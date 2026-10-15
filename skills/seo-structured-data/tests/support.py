import importlib,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
AT='2026-09-17T02:00:00Z';URL='https://bingx.com/en/price/bitcoin'
class StructuredTest(unittest.TestCase):
    def module(self,name):
        self.assertTrue((ROOT/'scripts/structured_audit'/(name+'.py')).is_file(),'尚未实现：'+name)
        return importlib.import_module('structured_audit.'+name)
