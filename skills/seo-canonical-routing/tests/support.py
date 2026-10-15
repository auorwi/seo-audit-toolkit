import importlib
import sys
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
AT='2026-09-16T16:00:00Z'

class RoutingTest(unittest.TestCase):
    def module(self,name):
        self.assertTrue((ROOT/'scripts/canonical_routing'/(name+'.py')).is_file(),'尚未实现：'+name)
        return importlib.import_module('canonical_routing.'+name)
