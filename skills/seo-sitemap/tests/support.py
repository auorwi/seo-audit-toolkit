import importlib
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
NS = "http://www.sitemaps.org/schemas/sitemap/0.9"
AT = "2026-09-16T10:00:00Z"

def xml(urls, kind="urlset"):
    from xml.sax.saxutils import escape
    tag = "url" if kind == "urlset" else "sitemap"
    return (f'<{kind} xmlns="{NS}">' + ''.join(f'<{tag}><loc>{escape(u)}</loc></{tag}>' for u in urls) + f'</{kind}>').encode()

class AuditTest(unittest.TestCase):
    def module(self, name):
        self.assertTrue((ROOT / "scripts" / "sitemap_audit" / (name + ".py")).is_file(), "尚未实现：" + name)
        return importlib.import_module("sitemap_audit." + name)

    def parse(self, body, **kwargs):
        return self.module("xmlrules").inspect_xml(body, "https://bingx.com/sitemap.xml", AT, **kwargs)

    def codes(self, result):
        return {r["rule"] for r in result["findings"]}
