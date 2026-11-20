import importlib
import math
from pathlib import Path
import sys
import types
import unittest

pack_dir = Path(__file__).parents[1]
pkg = types.ModuleType('magik_data_pack')
pkg.__path__ = [str(pack_dir)]
sys.modules['magik_data_pack'] = pkg
m = importlib.import_module('magik_data_pack.nodes')
e = importlib.import_module('magik_data_pack.extra_nodes')

class Blocker:
    def __init__(self, message): self.message = message

sys.modules.setdefault('comfy_execution', types.ModuleType('comfy_execution'))
graph = types.ModuleType('comfy_execution.graph')
graph.ExecutionBlocker = Blocker
sys.modules.setdefault('comfy_execution.graph', graph)

class Tests(unittest.TestCase):
    def test_boolean_truth_tables(self):
        for a in (False, True):
            for b in (False, True):
                for op, expected in [('AND', a and b), ('NAND', not (a and b)), ('OR', a or b), ('NOR', not (a or b)), ('XOR', a != b), ('XNOR', a == b)]:
                    self.assertEqual(m.MagikBoolean().execute(op, a=a, b=b), (expected, not expected, int(expected), 'true' if expected else 'false'))
        self.assertEqual(m.MagikBoolean().execute('AND', generic=True, a_input=[1], b_input='yes', item_0=0), (False, True, 0, 'false'))
        with self.assertRaises(TypeError): m.MagikBoolean().execute('AND', a_input=1)
        self.assertEqual(m.MagikBoolean().execute('NOT', a=True, b_input=object()), (False, True, 0, 'false'))

    def test_compare(self):
        n = m.MagikCompare()
        for low in (False, True):
            for high in (False, True):
                self.assertEqual(n.execute('In range', a=0, minimum=0, maximum=1, include_min=low, include_max=high)[0], low)
                self.assertEqual(n.execute('In range', a=1, minimum=0, maximum=1, include_min=low, include_max=high)[0], high)
        self.assertTrue(n.execute('String', text_a='Straße', text_b='STRASSE', case_sensitive=False)[0])
        self.assertEqual(n.execute('Length', a=4), (False, True, -1))
        self.assertEqual(n.execute('Length', a=[0,1], length=2), (True, False, 2))
        self.assertTrue(n.execute('Values', a={'a': [1]}, b={'a': [1]})[0])

    def test_compare_ported_from_basic(self):
        n = m.MagikCompare()
        # Tolerance within Values mode.
        self.assertTrue(n.execute('Values', a=1.0, b=1.05, relation='==', tolerance=0.1)[0])
        self.assertFalse(n.execute('Values', a=1.0, b=1.05, relation='==', tolerance=0.01)[0])
        self.assertTrue(n.execute('Values', a=1.0, b=2.0, relation='<', tolerance=0.1)[0])
        self.assertFalse(n.execute('Values', a=1.0, b=0.9, relation='<', tolerance=0.1)[0])
        self.assertTrue(n.execute('Values', a=1.0, b=1.05, relation='<=', tolerance=0.1)[0])
        # Tolerance only applies to numeric pairs; structural comparison is unchanged.
        self.assertTrue(n.execute('Values', a={'a': [1]}, b={'a': [1]}, relation='==', tolerance=0.1)[0])
        # Text relations under String mode.
        self.assertTrue(n.execute('String', text_a='Magik', text_b='gi', relation='contains')[0])
        self.assertTrue(n.execute('String', text_a='Magik', text_b='MAG', relation='starts with', case_sensitive=False)[0])
        self.assertFalse(n.execute('String', text_a='Magik', text_b='xik', relation='ends with', case_sensitive=True)[0])
        for op in ('contains', 'starts with', 'ends with'):
            with self.assertRaises(ValueError): n.execute('Values', a=1, b=1, relation=op)
            with self.assertRaises(ValueError): n.execute('Length', a=[1], relation=op)
            with self.assertRaises(ValueError): n.execute('Is null', a=None, relation=op)

    def test_maths(self):
        n = m.MagikMaths()
        for op, expected in [('add', 9), ('subtract', 5), ('multiply', 14), ('divide', 3.5), ('floor divide', 3), ('modulus', 1), ('power', 49)]:
            self.assertEqual(n.execute(op, a=7, b=2)[0], expected)
        self.assertEqual(n.execute('add', a=2**53+1, b=1)[0], 2**53+2)
        self.assertEqual(n.execute('divide (zero safe)', a=1,b=0,zero_fallback=9)[0], 9)
        with self.assertRaises(ZeroDivisionError): n.execute('divide', a=1,b=0)
        with self.assertRaises(ValueError): n.execute('power', a=-1,b=0.5)
        self.assertEqual(n.execute('round', a=1.125, digits=2)[0], 1.12)
        self.assertEqual(n.execute('add', a='123', b='2')[0],125)

    def test_maths_ported_from_basic(self):
        n = m.MagikMaths()
        self.assertEqual(n.execute('negate', a=7)[0], -7)
        self.assertEqual(n.execute('average', a=7, b=2)[0], 4.5)
        self.assertEqual(n.execute('clamp', a=15, minimum=0, maximum=10)[0], 10)
        self.assertEqual(n.execute('clamp', a=-5, minimum=0, maximum=10)[0], 0)
        self.assertEqual(n.execute('clamp', a=5, minimum=10, maximum=0)[0], 5)
        self.assertEqual(n.execute('map range', a=5, minimum=0, maximum=10)[2], 50)
        self.assertEqual(n.execute('map range', a=20, minimum=0, maximum=10, clamp_mapping=True)[0], 100)
        self.assertEqual(n.execute('map range', a=20, minimum=0, maximum=10, clamp_mapping=False)[0], 200)
        self.assertEqual(n.execute('map range', a=0, minimum=0, maximum=10, output_minimum=0, output_maximum=10)[0], 0)
        with self.assertRaises(ValueError): n.execute('map range', a=1, minimum=3, maximum=3)

    def test_functions(self):
        n = m.MagikMathConstFunctions()
        values = {'abs': ( -2, 2), 'acos': (1,0), 'asin': (0,0), 'atan': (0,0), 'atan2': (0,0), 'ceil': (1.2,2), 'cos': (0,1), 'degrees': (math.pi,180), 'e': (0,math.e), 'exp': (0,1), 'floor': (1.2,1), 'log': (1,0), 'log10': (100,2), 'max': (2,2), 'min': (2,1), 'pi': (0,math.pi), 'radians': (180,math.pi), 'sin': (90,1), 'sqrt': (4,2), 'tan': (0,0)}
        self.assertEqual(set(values), set(n.OPS))
        for op,(a, expected) in values.items(): self.assertAlmostEqual(n.execute(op,a_value=a)[0],expected)
        for op,a in [('sqrt',-1), ('acos',2), ('log',0), ('tan',90)]:
            with self.assertRaises(ValueError): n.execute(op,a_value=a)
        self.assertEqual(n.check_lazy_status('pi', a=None, b=None), [])
        self.assertEqual(n.check_lazy_status('sqrt', a=None, b=None), ['a'])
        self.assertEqual(n.execute('pi', a=object())[0], math.pi)

    def flow(self, mode, **kwargs):
        return m.MagikControlFlow().execute(mode, **kwargs)

    def test_flow(self):
        n = m.MagikControlFlow()
        prompt = {'8': {'inputs': {'if_true': ['1',0], 'if_false': ['2',0], 'value': ['3',0], 'condition_0': ['4',0], 'branch_0': ['5',0], 'branch_1': ['6',0], 'default': ['7',0]}}}
        self.assertEqual(n.check_lazy_status('if/else',condition=True,prompt=prompt,unique_id='8',if_true=None,if_false=None), ['if_true'])
        self.assertEqual(self.flow('if/else', condition=False, if_true='wrong',if_false=0)[0],0)
        self.assertEqual(n.check_lazy_status('if/elif/else',prompt=prompt,unique_id='8',condition_0=None), ['condition_0'])
        self.assertEqual(n.check_lazy_status('if/elif/else',prompt=prompt,unique_id='8',condition_0=True,branch_0=None), ['branch_0'])
        self.assertEqual(self.flow('switch/case', prompt=prompt,unique_id='8',select=1,branch_1=None,default=8)[0],None)
        self.assertEqual(self.flow('switch/case', prompt=prompt,unique_id='8',select=99,default=8)[0],8)
        self.assertTrue(self.flow('is connected',prompt=prompt,unique_id='8',value=None)[0])
        self.assertFalse(self.flow('is connected')[0])
        self.assertIsInstance(self.flow('continue flow',condition=False)[0],Blocker)
        for v in ([],{},'',0,False,None): self.assertIsInstance(self.flow('continue if not empty',value=v)[0],Blocker)
        self.assertEqual(self.flow('continue if not empty',value=[0])[0],[0])
        a,b,_ = self.flow('flow select',condition=False,value='data')
        self.assertIsInstance(a,Blocker)
        self.assertEqual(b,'data')
        self.assertTrue(math.isnan(n.IS_CHANGED('force calculation')))
        self.assertEqual(n.IS_CHANGED('if/else'),'if/else')

    def test_comfy_list_execution_and_order(self):
        n = m.MagikControlFlow()
        prompt = {'8': {'inputs': {'value': ['1',0], 'dependency': ['2',0]}}}
        self.assertEqual(n.check_lazy_status(['force execution order'], prompt=[prompt], unique_id=['8'], value=None, dependency=None), ['dependency'])
        self.assertEqual(n.check_lazy_status(['force execution order'], prompt=[prompt], unique_id=['8'], value=None, dependency=[None]), ['value'])
        result = n.execute(['continue if not empty'], value=[], prompt=[prompt], unique_id=['8'])
        self.assertIsInstance(result[0][0], Blocker)
        self.assertEqual(n.execute(['if/else'],condition=[False],if_true=['wrong'],if_false=[1,2])[0], [1,2])
        self.assertEqual(n.execute(['force execution order'], value=[1,2], dependency=[None])[0], [1,2])
        self.assertTrue(math.isnan(n.IS_CHANGED(['force calculation'])))

    def test_extra_nodes(self):
        c = e.MagikTypeConvert()
        self.assertEqual(c.execute(5, 'String', padding=3), ('005',))
        self.assertEqual(c.execute(True, 'String'), ('true',))
        self.assertEqual(c.execute(-7, 'String', padding=3), ('-07',))
        self.assertEqual(c.execute('42', 'Integer'), (42,))
        self.assertEqual(c.execute(1.9, 'Integer', integer_rounding='Floor'), (1,))
        self.assertEqual(c.execute(1.2, 'Integer', integer_rounding='Round'), (1,))
        self.assertEqual(c.execute(True, 'Float'), (1.0,))
        self.assertEqual(c.execute('yes', 'Boolean'), (True,))
        self.assertEqual(c.execute(0.0, 'Boolean'), (False,))
        self.assertEqual(e.MagikFloat().execute(1.23456, 2), (1.23, '1.23'))
        with self.assertRaises(ValueError): e.MagikFloat().execute(float('inf'), 2)
        l = e.MagikLength()
        self.assertEqual(l.execute(['a\nb'], ['Auto'], [True], ['utf-8']), (2,))
        self.assertEqual(l.execute(['abc'], ['Text characters'], [True], ['utf-8']), (3,))
        self.assertEqual(l.execute([[1,2,3]], ['List elements'], [True], ['utf-8']), (3,))
        self.assertEqual(l.execute([{'a':1}], ['Dictionary entries'], [True], ['utf-8']), (1,))
        image = types.SimpleNamespace(shape=(2, 4, 6, 3), dtype='float32', device='cpu')
        result = e.MagikImageInfo().execute(image)
        self.assertEqual(result[1:5], (6, 4, 2, 3))
        self.assertAlmostEqual(result[5], 1.5)

    def test_registration_and_dynamic_schema(self):
        self.assertEqual(set(m.NODE_CLASS_MAPPINGS), {'MagikBoolean', 'MagikCompare', 'MagikControlFlow', 'MagikMaths', 'MagikMathConstFunctions'})
        self.assertEqual(set(e.NODE_CLASS_MAPPINGS), {'MagikTypeConvert', 'MagikFloat', 'MagikLength', 'MagikImageInfo'})
        for cls in list(m.NODE_CLASS_MAPPINGS.values()) + list(e.NODE_CLASS_MAPPINGS.values()):
            self.assertEqual(len(cls.RETURN_TYPES), len(cls.RETURN_NAMES))
            cls.INPUT_TYPES()
        schema = m.MagikControlFlow.INPUT_TYPES()['optional']
        self.assertIn('branch_127', schema)
        self.assertTrue(schema['branch_127'][1]['lazy'])
        self.assertNotIn('arbitrary', schema)
        self.assertIn('contains', m.MagikCompare.INPUT_TYPES()['required']['relation'][0])

if __name__ == '__main__': unittest.main()
