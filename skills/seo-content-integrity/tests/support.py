import importlib,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
class IntegrityTest(unittest.TestCase):
    def module(self,name):
        self.assertTrue((ROOT/'scripts/content_integrity'/(name+'.py')).is_file(),'尚未实现：'+name)
        return importlib.import_module('content_integrity.'+name)
