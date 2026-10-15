import importlib
import sys
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
AT='2026-09-17T00:00:00Z'

class RenderingTest(unittest.TestCase):
    def module(self,name):
        self.assertTrue((ROOT/'scripts/rendering_audit'/(name+'.py')).is_file(),'尚未实现：'+name)
        return importlib.import_module('rendering_audit.'+name)
