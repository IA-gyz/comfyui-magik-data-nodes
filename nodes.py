"""Dependency-free consolidated ComfyUI data nodes. No expression evaluation.
Since 1.1.0 this pack also absorbs comfyui-magik-basic-nodes (see extra_nodes.py)."""
import math
import operator
import re
from numbers import Real


class AnyType(str):
    def __ne__(self, other):
        return False


ANY = AnyType('*')
RELATIONS = {'==': operator.eq, '!=': operator.ne, '<': operator.lt,
             '<=': operator.le, '>': operator.gt, '>=': operator.ge}
TEXT_RELATIONS = ('contains', 'starts with', 'ends with')


def numeric_compare(a, b, relation, tolerance):
    """Compare numbers with an absolute tolerance: values within tolerance
    count as equal, including for inclusive relations; strict relations
    exclude them (replaces Magik Basic Nodes' Magik Compare Number mode)."""
    a, b = number(a), number(b)
    tolerance = number(tolerance or 0.0)
    if tolerance < 0:
        raise ValueError('Tolerance must be nonnegative.')
    if tolerance == 0:
        return RELATIONS[relation](a, b)
    equal = abs(a - b) <= tolerance
    return {'==': equal, '!=': not equal, '<': a < b and not equal,
            '<=': a < b or equal, '>': a > b and not equal, '>=': a > b or equal}[relation]


def truth(value):
    try:
        return bool(value)
    except (ValueError, RuntimeError) as exc:
        raise ValueError('Expected a single truth value; reduce tensors/arrays explicitly first.') from exc


def number(value):
    if isinstance(value, bool) or not isinstance(value, (Real, str)):
        raise TypeError('Expected an INT, FLOAT or numeric string (not BOOLEAN).')
    if isinstance(value, str):
        value = value.strip()
        value = int(value) if re.fullmatch(r'[+-]?\d+', value) else float(value)
    if not isinstance(value, int) and not math.isfinite(value):
        raise ValueError('Numbers must be finite.')
    return value


def numeric_outputs(value):
    if isinstance(value, complex):
        raise ValueError('Complex results are not supported.')
    value = number(value)
    return value, float(value), int(value)


class DynamicInputs(dict):
    """Recognize only the numbered sockets supported by the frontend."""
    def __contains__(self, key):
        return super().__contains__(key) or re.fullmatch(r'(item|condition|branch)_\d+', key) is not None

    def __getitem__(self, key):
        if super().__contains__(key):
            return super().__getitem__(key)
        if key not in self:
            raise KeyError(key)
        return (ANY, {'lazy': True, 'forceInput': True})


class Base:
    CATEGORY = 'Magik/Data'
    FUNCTION = 'execute'


class MagikBoolean(Base):
    DESCRIPTION = 'Boolean logic. Strict mode requires booleans; generic mode uses Python truthiness. Extra item sockets participate in AND/OR/XOR and inverted variants.'
    RETURN_TYPES = ('BOOLEAN', 'BOOLEAN', 'INT', 'STRING')
    RETURN_NAMES = ('result', 'inverse', 'int', 'string')

    @classmethod
    def INPUT_TYPES(cls):
        return {'required': {'operation': (['AND', 'NAND', 'OR', 'NOR', 'NOT', 'XOR', 'XNOR', 'VALUE'],),
                             'generic': ('BOOLEAN', {'default': False}),
                             'a': ('BOOLEAN', {'default': False}), 'b': ('BOOLEAN', {'default': False})},
                'optional': DynamicInputs({'a_input': (ANY,), 'b_input': (ANY,)}),
                'hidden': {'unique_id': 'UNIQUE_ID', 'prompt': 'PROMPT'}}

    def execute(self, operation, generic=False, a=False, b=False, unique_id=None, prompt=None, **kwargs):
        def operand(name, fallback):
            return kwargs.get(name, fallback)
        vals = [operand('a_input', a)]
        if operation not in ('NOT', 'VALUE'):
            vals += [operand('b_input', b)]
            vals += [kwargs[k] for k in sorted(kwargs, key=lambda k: int(k[5:]) if k.startswith('item_') else -1) if k.startswith('item_')]
        if not generic and any(type(v) is not bool for v in vals):
            raise TypeError('Strict Boolean mode requires BOOLEAN inputs. Enable generic for truthiness.')
        vals = [truth(v) for v in vals]
        if operation in ('AND', 'NAND'): result = all(vals)
        elif operation in ('OR', 'NOR'): result = any(vals)
        elif operation in ('XOR', 'XNOR'): result = sum(vals) % 2 == 1
        elif operation in ('NOT', 'VALUE'): result = vals[0]
        else: raise ValueError(f'Unknown Boolean operation: {operation}')
        if operation in ('NOT', 'NAND', 'NOR', 'XNOR'): result = not result
        # int and string outputs replace Magik Basic Nodes' boolean emitter.
        return result, not result, int(result), 'true' if result else 'false'

    def check_lazy_status(self, operation, **kwargs):
        return [k for k, v in kwargs.items() if k.startswith('item_') and v is None] if operation not in ('NOT', 'VALUE') else []


class MagikCompare(Base):
    DESCRIPTION = 'Compare values, strings, container length or numeric range. Range boundaries are individually inclusive/exclusive. Length without len() returns False and -1. Values mode with a numeric pair and a tolerance counts numbers within tolerance as equal; String mode adds contains/starts with/ends with (from Magik Basic Nodes).'
    RETURN_TYPES = ('BOOLEAN', 'BOOLEAN', 'INT')
    RETURN_NAMES = ('result', 'inverse', 'actual_length')

    @classmethod
    def INPUT_TYPES(cls):
        return {'required': {'mode': (['Values', 'String', 'Length', 'Is null', 'In range'],),
                             'relation': (list(RELATIONS) + list(TEXT_RELATIONS),),
                             'text_a': ('STRING', {'default': ''}), 'text_b': ('STRING', {'default': ''}),
                             'case_sensitive': ('BOOLEAN', {'default': True}),
                             'length': ('INT', {'default': 0, 'min': 0}),
                             'minimum': ('FLOAT', {'default': 0.0}), 'maximum': ('FLOAT', {'default': 100.0}),
                             'include_min': ('BOOLEAN', {'default': True}), 'include_max': ('BOOLEAN', {'default': True}),
                             'tolerance': ('FLOAT', {'default': 0.0})},
                'optional': {'a': (ANY,), 'b': (ANY,)}}

    def execute(self, mode='Values', relation='==', text_a='', text_b='', case_sensitive=True,
                length=0, minimum=0.0, maximum=100.0, include_min=True, include_max=True,
                tolerance=0.0, a=None, b=None):
        actual = -1
        if relation not in RELATIONS and relation not in TEXT_RELATIONS: raise ValueError(f'Unknown relation: {relation}')
        if mode == 'Is null':
            if relation in TEXT_RELATIONS: raise ValueError(f'{relation} is only available in String mode.')
            result = a is None
        elif mode == 'In range':
            if relation in TEXT_RELATIONS: raise ValueError(f'{relation} is only available in String mode.')
            a, low, high = number(a), number(minimum), number(maximum)
            if low > high: raise ValueError('Minimum cannot exceed maximum.')
            result = (a >= low if include_min else a > low) and (a <= high if include_max else a < high)
        elif mode == 'Length':
            if relation in TEXT_RELATIONS: raise ValueError(f'{relation} is only available in String mode.')
            try: actual = len(a)
            except TypeError: return False, True, -1
            result = RELATIONS[relation](actual, length)
        elif mode == 'String':
            if relation not in RELATIONS and relation not in TEXT_RELATIONS: raise ValueError(f'Unknown relation: {relation}')
            left, right = text_a if a is None else a, text_b if b is None else b
            if not isinstance(left, str) or not isinstance(right, str): raise TypeError('String comparison requires strings.')
            if not case_sensitive: left, right = left.casefold(), right.casefold()
            if relation == 'contains': result = right in left
            elif relation == 'starts with': result = left.startswith(right)
            elif relation == 'ends with': result = left.endswith(right)
            else: result = RELATIONS[relation](left, right)
        elif mode == 'Values':
            if relation in TEXT_RELATIONS: raise ValueError(f'{relation} is only available in String mode.')
            numbers = a is not None and b is not None and all(
                isinstance(v, (Real, str)) and not isinstance(v, bool) for v in (a, b))
            result = numeric_compare(a, b, relation, tolerance) if numbers else RELATIONS[relation](a, b)
        else: raise ValueError(f'Unknown comparison mode: {mode}')
        result = truth(result)
        return result, not result, actual


class MagikMaths(Base):
    DESCRIPTION = 'Basic arithmetic plus clamp/map-range (ported from Magik Basic Nodes). Connected a/b override numeric widgets. result preserves INT where possible; FLOAT and INT outputs explicitly convert (INT truncates toward zero). Safe divide alone returns fallback on zero.'
    RETURN_TYPES = (ANY, 'FLOAT', 'INT')
    RETURN_NAMES = ('result', 'float', 'int')
    OPS = ['add', 'subtract', 'multiply', 'divide', 'divide (zero safe)', 'floor divide', 'modulus', 'power', 'round', 'average', 'clamp', 'map range', 'negate']

    @classmethod
    def INPUT_TYPES(cls):
        return {'required': {'operation': (cls.OPS,), 'a_value': ('FLOAT', {'default': 0.0}),
                             'b_value': ('FLOAT', {'default': 1.0}),
                             'digits': ('INT', {'default': 0, 'min': -308, 'max': 308}),
                             'zero_fallback': ('FLOAT', {'default': 0.0}),
                             'minimum': ('FLOAT', {'default': 0.0}), 'maximum': ('FLOAT', {'default': 1.0}),
                             'output_minimum': ('FLOAT', {'default': 0.0}), 'output_maximum': ('FLOAT', {'default': 100.0}),
                             'clamp_mapping': ('BOOLEAN', {'default': True})},
                'optional': {'a': (ANY,), 'b': (ANY,)}}

    def execute(self, operation, a_value=0.0, b_value=1.0, digits=0, zero_fallback=0.0,
                minimum=0.0, maximum=1.0, output_minimum=0.0, output_maximum=100.0,
                clamp_mapping=True, **kwargs):
        a = number(kwargs.get('a', a_value))
        if operation == 'round': return numeric_outputs(round(a, digits))
        if operation == 'negate': return numeric_outputs(-a)
        if operation not in ('average', 'clamp', 'map range'):
            b = number(kwargs.get('b', b_value))
        if operation == 'average':
            b = number(kwargs.get('b', b_value))
            result = a / 2 + b / 2
        elif operation == 'clamp':
            low, high = sorted((number(minimum), number(maximum)))
            result = max(low, min(high, a))
        elif operation == 'map range':
            low, high = number(minimum), number(maximum)
            if low == high: raise ValueError('Map range requires different input bounds.')
            ratio = (a - low) / (high - low)
            if clamp_mapping: ratio = max(0.0, min(1.0, ratio))
            result = number(output_minimum) + ratio * (number(output_maximum) - number(output_minimum))
        elif operation == 'divide (zero safe)': result = number(zero_fallback) if b == 0 else a / b
        else:
            ops = {'add': operator.add, 'subtract': operator.sub, 'multiply': operator.mul,
                   'divide': operator.truediv, 'floor divide': operator.floordiv, 'modulus': operator.mod, 'power': operator.pow}
            if operation not in ops: raise ValueError(f'Unknown math operation: {operation}')
            if operation == 'power' and abs(b) > 10000: raise ValueError('Power exponent exceeds 10000 limit.')
            result = ops[operation](a, b)
        return numeric_outputs(result)


class MagikMathConstFunctions(Base):
    DESCRIPTION = 'Constants and real-valued functions. Angles can use degrees/radians; atan2 uses a=y, b=x. log uses the base widget. Constants ignore all operands. INT output truncates toward zero.'
    RETURN_TYPES = (ANY, 'FLOAT', 'INT')
    RETURN_NAMES = ('result', 'float', 'int')
    OPS = ['abs', 'acos', 'asin', 'atan', 'atan2', 'ceil', 'cos', 'degrees', 'e', 'exp', 'floor', 'log', 'log10', 'max', 'min', 'pi', 'radians', 'sin', 'sqrt', 'tan']

    @classmethod
    def INPUT_TYPES(cls):
        return {'required': {'operation': (cls.OPS,), 'a_value': ('FLOAT', {'default': 0.0}),
                             'b_value': ('FLOAT', {'default': 1.0}), 'unit': (['degrees', 'radians'],),
                             'base': ('FLOAT', {'default': math.e})},
                'optional': {'a': (ANY, {'lazy': True}), 'b': (ANY, {'lazy': True})}}

    def check_lazy_status(self, operation, **kwargs):
        keys = [] if operation in ('e', 'pi') else ['a']
        if operation in ('atan2', 'max', 'min'): keys.append('b')
        return [k for k in keys if k in kwargs and kwargs[k] is None]

    def execute(self, operation, a_value=0.0, b_value=1.0, unit='degrees', base=math.e, **kwargs):
        if operation in ('e', 'pi'): return numeric_outputs(getattr(math, operation))
        a = number(kwargs.get('a', a_value))
        if operation in ('atan2', 'max', 'min'):
            b = number(kwargs.get('b', b_value))
            result = math.atan2(a, b) if operation == 'atan2' else (max(a, b) if operation == 'max' else min(a, b))
        elif operation in ('sin', 'cos', 'tan'):
            angle = math.radians(a) if unit == 'degrees' else a
            if operation == 'tan' and abs(math.cos(angle)) < 1e-10: raise ValueError('Tangent is undefined at this angle.')
            result = getattr(math, operation)(angle)
        elif operation == 'log': result = math.log(a, number(base))
        elif operation == 'abs': result = abs(a)
        elif operation in self.OPS: result = getattr(math, operation)(a)
        else: raise ValueError(f'Unknown function: {operation}')
        if operation in ('acos', 'asin', 'atan', 'atan2') and unit == 'degrees': result = math.degrees(result)
        return numeric_outputs(result)


class MagikControlFlow(Base):
    DESCRIPTION = 'Lazy if/else, ordered if/elif/else and zero-based switch; gates, routing, dependency ordering and connection checks. Numbered branch sockets are configured by input_count. Force calculation invalidates this node, not cached ancestors.'
    RETURN_TYPES = (ANY, ANY, 'BOOLEAN')
    RETURN_NAMES = ('result / true', 'false', 'is_connected')
    OUTPUT_NODE = True
    INPUT_IS_LIST = True
    OUTPUT_IS_LIST = (True, True, True)
    MODES = ['if/else', 'if/elif/else', 'switch/case', 'continue if not empty', 'continue flow', 'flow select', 'force calculation', 'force execution order', 'is connected']

    @classmethod
    def INPUT_TYPES(cls):
        return {'required': {'operation': (cls.MODES,), 'condition': ('BOOLEAN', {'default': True}),
                             'select': ('INT', {'default': 0}),
                             'input_count': ('INT', {'default': 2, 'min': 2, 'max': 128}),
                             'message': ('STRING', {'default': ''})},
                'optional': DynamicInputs({'value': (ANY, {'lazy': True}), 'if_true': (ANY, {'lazy': True}),
                                          'if_false': (ANY, {'lazy': True}), 'default': (ANY, {'lazy': True}),
                                          'dependency': (ANY, {'lazy': True})}),
                'hidden': {'prompt': 'PROMPT', 'unique_id': 'UNIQUE_ID'}}

    @classmethod
    def IS_CHANGED(cls, operation, **kwargs):
        operation = operation[0] if isinstance(operation, list) else operation
        return float('nan') if operation == 'force calculation' else operation

    @staticmethod
    def _links(prompt, unique_id):
        return (prompt or {}).get(str(unique_id), {}).get('inputs', {})

    def needed(self, operation, condition=True, select=0, input_count=2, links=None, **kwargs):
        links = links or {}
        if operation == 'is connected': return []
        if operation == 'if/else': return ['if_true' if condition else 'if_false']
        if operation == 'switch/case':
            key = f'branch_{select}'
            return [key if 0 <= select < input_count and key in links else 'default']
        if operation == 'if/elif/else':
            for i in range(input_count):
                key = f'condition_{i}'
                if key not in links: continue
                if kwargs.get(key) is None: return [key]
                if truth(kwargs[key]): return [f'branch_{i}']
            return ['default']
        if operation == 'continue flow' and not condition: return []
        if operation == 'force execution order' and 'dependency' in links and kwargs.get('dependency') is None:
            return ['dependency']
        return ['value']

    @staticmethod
    def _runtime_args(operation, prompt, unique_id, kwargs):
        if not isinstance(operation, list):
            return operation, prompt, unique_id, kwargs, False
        first = lambda v: v[0] if isinstance(v, list) and v else v
        kwargs = {k: first(v) if k in ('condition', 'select', 'input_count', 'message') or k.startswith('condition_') else v for k, v in kwargs.items()}
        return first(operation), first(prompt), first(unique_id), kwargs, True

    def check_lazy_status(self, operation, prompt=None, unique_id=None, **kwargs):
        operation, prompt, unique_id, kwargs, _ = self._runtime_args(operation, prompt, unique_id, kwargs)
        links = self._links(prompt, unique_id)
        return [k for k in self.needed(operation, links=links, **kwargs) if k in links and kwargs.get(k) is None]

    def execute(self, operation, condition=True, select=0, input_count=2, message='', prompt=None, unique_id=None, **kwargs):
        kwargs.update(condition=condition, select=select, input_count=input_count, message=message)
        operation, prompt, unique_id, kwargs, runtime = self._runtime_args(operation, prompt, unique_id, kwargs)
        result = self._execute(operation, prompt=prompt, unique_id=unique_id, **kwargs)
        if runtime:
            return tuple(v if isinstance(v, list) else [v] for v in result)
        return result

    def _execute(self, operation, condition=True, select=0, input_count=2, message='', prompt=None, unique_id=None, **kwargs):
        from comfy_execution.graph import ExecutionBlocker
        links = self._links(prompt, unique_id)
        connected = isinstance(links.get('value'), list) and len(links['value']) == 2
        block = lambda: ExecutionBlocker(message or None)
        if operation == 'is connected': return connected, block(), connected
        if operation not in self.MODES: raise ValueError(f'Unknown flow operation: {operation}')
        keys = self.needed(operation, condition, select, input_count, links, **kwargs)
        value = kwargs.get(keys[-1]) if keys else None
        if operation == 'continue flow' and not condition: return block(), block(), connected
        if operation == 'continue if not empty' and not truth(value): return block(), block(), connected
        if operation == 'flow select': return (value, block(), connected) if condition else (block(), value, connected)
        return value, block(), connected


NODE_CLASS_MAPPINGS = {c.__name__: c for c in (MagikBoolean, MagikCompare, MagikControlFlow, MagikMaths, MagikMathConstFunctions)}
NODE_DISPLAY_NAME_MAPPINGS = dict(zip(NODE_CLASS_MAPPINGS, ('Magik Boolean', 'Magik Compare', 'Magik Control Flow', 'Magik Maths', 'Magik Math Const&Functions')))
