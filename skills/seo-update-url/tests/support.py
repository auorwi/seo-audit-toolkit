import importlib
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))


class InventoryTest(unittest.TestCase):
    def module(self, name):
        path = ROOT / "scripts" / "url_inventory" / (name + ".py")
        self.assertTrue(path.is_file(), "尚未实现受测能力：" + name)
        return importlib.import_module("url_inventory." + name)
