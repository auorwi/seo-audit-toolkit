"""Opt-in actual Chromium integration on local controlled fixtures."""
import hashlib,json,os,subprocess,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class StructuredBrowserTests(unittest.TestCase):
    def collect(self,html,timeout=1500,extra=None):
        if not os.getenv('SEMANTICS_RUNTIME') or not os.getenv('SEMANTICS_CHROME'):self.skipTest('Browser runtime not configured')
        module=ROOT/'scripts/collect_structured.mjs';self.assertTrue(module.exists(),'尚未实现008实际浏览器采集')
        js='''import {createRequire} from 'node:module';const require=createRequire(import.meta.url);const {chromium}=require(process.env.SEMANTICS_RUNTIME+'/node_modules/playwright-core');
const {collectStructured}=await import(process.env.STRUCTURED_MODULE);const browser=await chromium.launch({executablePath:process.env.SEMANTICS_CHROME,headless:true});
try{const page=await browser.newPage();await page.setContent(JSON.parse(process.env.TEST_HTML));const r=await collectStructured(page,{mainSelector:'main',identitySelector:'#entity',expectedIdentity:'BTC',placeholderSelector:'.loading',errorSelector:'.error',timeoutMs:Number(process.env.TEST_TIMEOUT),stableWindowMs:100,sampleIntervalMs:30,...JSON.parse(process.env.TEST_EXTRA)});console.log(JSON.stringify(r));}finally{await browser.close();}'''
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'run.mjs';p.write_text(js);r=subprocess.run(['node',str(p)],env={**os.environ,'STRUCTURED_MODULE':module.as_uri(),'TEST_HTML':json.dumps(html),'TEST_TIMEOUT':str(timeout),'TEST_EXTRA':json.dumps(extra or {})},capture_output=True,text=True,timeout=60)
        self.assertEqual(r.returncode,0,r.stderr);return json.loads(r.stdout)
    def test_delayed_schema_settles_and_visible_text_binds_same_document(self):
        r=self.collect('<html><head><script id="ld" type="application/ld+json">{"@type":"WebPage","name":"Old"}</script></head><body><main><h1 id="entity">BTC</h1><p>Price $12.00</p></main><script>setTimeout(()=>document.querySelector("#ld").textContent=JSON.stringify({"@context":"https://schema.org","@type":"WebPage","name":"New"}),150)</script></body></html>')
        self.assertEqual(r['capture']['readiness'],'ready');self.assertIn('"name":"New"',r['html']);self.assertIn('Price $12.00',r['visible']['visible_text']);self.assertEqual(r['visible']['document_sha256'],hashlib.sha256(r['html'].encode()).hexdigest());self.assertGreaterEqual(r['schema_samples'],2)
    def test_continuously_changing_schema_is_unknown_not_ready(self):
        r=self.collect('<main><h1 id="entity">BTC</h1></main><script id="ld" type="application/ld+json">{}</script><script>let x=0;setInterval(()=>document.querySelector("#ld").textContent=JSON.stringify({"@type":"Offer","price":++x}),25)</script>',timeout=500)
        self.assertEqual(r['capture']['readiness'],'unknown_timeout');self.assertIn('structured_data_not_stable',r['unmet'])
    def test_no_schema_is_valid_inventory_not_error(self):
        r=self.collect('<main><h1 id="entity">BTC</h1></main>');self.assertEqual(r['capture']['readiness'],'ready');self.assertEqual(r['structured_counts']['jsonld'],0)
    def test_wrong_page_entity_cannot_be_promoted_by_stable_schema(self):
        r=self.collect('<main><h1 id="entity">ETH</h1></main>',timeout=250);self.assertNotEqual(r['capture']['readiness'],'ready')
    def test_business_placeholder_prevents_false_ready(self):
        r=self.collect('<main><h1 id="entity">BTC</h1><p id="reward">Claim -- USDT</p></main>',timeout=400,extra={'contentChecks':[{'selector':'#reward','forbiddenText':'--'}]})
        self.assertEqual(r['capture']['readiness'],'unknown_timeout')
        self.assertIn('content_check_not_ready:#reward',r['unmet'])
    def test_business_value_must_settle_before_ready(self):
        r=self.collect('<main><h1 id="entity">BTC</h1><p id="reward">Claim -- USDT</p></main><script>setTimeout(()=>document.querySelector("#reward").textContent="Claim 7,000 USDT",450)</script>',extra={'contentChecks':[{'selector':'#reward','forbiddenText':'--','requiredText':'USDT'}]})
        self.assertEqual(r['capture']['readiness'],'ready');self.assertIn('Claim 7,000 USDT',r['visible']['visible_text'])
if __name__=='__main__':unittest.main()
