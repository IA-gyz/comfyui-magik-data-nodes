import importlib.util
import math
from pathlib import Path
import sys
import types
import unittest

spec = importlib.util.spec_from_file_location('magik_nodes_test', Path(__file__).parents[1] / 'nodes.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

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
                    self.assertEqual(m.MagikBoolean().execute(op, a=a, b=b), (expected, not expected))
        self.assertEqual(m.MagikBoolean().execute('AND', generic=True, a_input=[1], b_input='yes', item_0=0), (False, True))
        with self.assertRaises(TypeError): m.MagikBoolean().execute('AND', a_input=1)
        self.assertEqual(m.MagikBoolean().execute('NOT', a=True, b_input=object()), (False, True))

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

    def test_registration_and_dynamic_schema(self):
        self.assertEqual(len(m.NODE_CLASS_MAPPINGS),5)
        for cls in m.NODE_CLASS_MAPPINGS.values():
            self.assertEqual(len(cls.RETURN_TYPES),len(cls.RETURN_NAMES))
            cls.INPUT_TYPES()
        schema = m.MagikControlFlow.INPUT_TYPES()['optional']
        self.assertIn('branch_127',schema)
        self.assertTrue(schema['branch_127'][1]['lazy'])
        self.assertNotIn('arbitrary',schema)

if __name__ == '__main__': unittest.main()
