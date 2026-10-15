import importlib,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
class MediaTest(unittest.TestCase):
    def module(self,name):
        self.assertTrue((ROOT/'scripts/media_audit'/(name+'.py')).is_file(),'尚未实现013模块：'+name)
        return importlib.import_module('media_audit.'+name)
