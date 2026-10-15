"""Explicit real extruct dependency integration; controlled HTML, not a live site."""
import hashlib,json,os,subprocess,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
URL='https://bingx.com/en/price/bitcoin'
class ExtructTests(unittest.TestCase):
    def run_extract(self,html,extra=None):
        python=os.getenv('EXTRUCT_PYTHON')
        if not python:self.skipTest('EXTRUCT_PYTHON not configured')
        script=ROOT/'scripts/extract_embedded.py';self.assertTrue(script.exists(),'尚未实现真实extruct CLI')
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp);p=base/'page.html';p.write_text(html)
            proc=subprocess.run([python,str(script),'--html',str(p),'--url',URL,'--output',str(base/'result.json')]+(extra or []),capture_output=True,text=True,timeout=30)
            self.assertEqual(proc.returncode,0,proc.stderr)
            result=json.loads((base/'result.json').read_text());self.assertEqual(result['document_sha256'],hashlib.sha256(p.read_bytes()).hexdigest());return result
    def test_real_microdata_nested_offer(self):
        r=self.run_extract('<div itemscope itemtype="https://schema.org/Product"><span itemprop="name">Bitcoin</span><div itemprop="offers" itemscope itemtype="https://schema.org/Offer"><meta itemprop="price" content="65000"><meta itemprop="priceCurrency" content="USD"></div></div>')
        self.assertEqual(r['state'],'completed');self.assertTrue(r['checker_version']);self.assertEqual(r['payload']['microdata'][0]['properties']['name'],'Bitcoin');self.assertIn('offers',r['payload']['microdata'][0]['properties'])
    def test_real_rdfa_expanded_property(self):
        r=self.run_extract('<html><body><div vocab="https://schema.org/" typeof="Product" resource="#btc"><span property="name">Bitcoin</span></div></body></html>')
        p=next(x for x in r['payload']['rdfa'] if 'https://schema.org/Product' in x.get('@type',[]));self.assertEqual(p['https://schema.org/name'][0]['@value'],'Bitcoin')
    def test_empty_markup_is_successful_extraction_not_all_seo_pass(self):
        r=self.run_extract('<html><body>No structured data</body></html>');self.assertEqual(r['payload'],{'microdata':[],'rdfa':[]});self.assertFalse(r['coverage']['engine_validation'])
    def test_microdata_itemref_resolves_actual_external_property(self):
        r=self.run_extract('<div itemscope itemtype="https://schema.org/Product" itemref="extra"><span itemprop="name">BTC</span></div><div id="extra"><span itemprop="brand">BingX</span></div>')
        self.assertEqual(r['payload']['microdata'][0]['properties']['brand'],'BingX')
    def test_microdata_relative_url_resolved_against_page(self):
        r=self.run_extract('<div itemscope itemtype="https://schema.org/WebPage"><a itemprop="url" href="/en/price">Price</a></div>');self.assertEqual(r['payload']['microdata'][0]['properties']['url'],'https://bingx.com/en/price')
if __name__=='__main__':unittest.main()
