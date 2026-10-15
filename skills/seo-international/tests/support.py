import importlib, sys, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
AT='2026-09-17T04:00:00Z'
class InternationalTest(unittest.TestCase):
    def module(self,name):
        self.assertTrue((ROOT/'scripts/international_audit'/(name+'.py')).is_file(),'尚未实现：'+name)
        return importlib.import_module('international_audit.'+name)
