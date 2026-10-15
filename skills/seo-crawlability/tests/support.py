import importlib
import sys
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
AT='2026-09-16T12:00:00Z'

class CrawlTest(unittest.TestCase):
    def module(self,name):
        self.assertTrue((ROOT/'scripts/crawlability'/(name+'.py')).is_file(),'尚未实现：'+name)
        return importlib.import_module('crawlability.'+name)

    def rules(self,text,url='https://bingx.com/en',agent='Googlebot',robots_url='https://bingx.com/robots.txt'):
        body=text.encode('utf-8') if isinstance(text,str) else text
        return self.module('robots').evaluate_rules(body,url,agent,robots_url)
