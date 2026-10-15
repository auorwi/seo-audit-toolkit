"""Opt-in actual Chromium tests; local controlled pages, never mislabeled live BingX."""
import json,os,subprocess,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class BrowserTests(unittest.TestCase):
    def collect(self,html,identity='SOLV'):
        runtime=os.getenv('SEMANTICS_RUNTIME');chrome=os.getenv('SEMANTICS_CHROME')
        if not runtime or not chrome:self.skipTest('Browser runtime not configured')
        script=ROOT/'scripts/collect_metadata.mjs';self.assertTrue(script.exists(),'尚未实现007浏览器采集')
        js='''import {createRequire} from 'node:module';const require=createRequire(import.meta.url);
const {chromium}=require(process.env.SEMANTICS_RUNTIME+'/node_modules/playwright-core');
const {collectMetadata}=await import(process.env.TDK_MODULE);const browser=await chromium.launch({executablePath:process.env.SEMANTICS_CHROME,headless:true});
try{const page=await browser.newPage();await page.setContent(JSON.parse(process.env.TDK_HTML));
const r=await collectMetadata(page,{mainSelector:'main',identitySelector:'#entity',expectedIdentity:process.env.TDK_IDENTITY,placeholderSelector:'.loading',errorSelector:'.error',timeoutMs:2500,stableWindowMs:100,sampleIntervalMs:30});console.log(JSON.stringify(r));}finally{await browser.close();}'''
        with tempfile.TemporaryDirectory() as tmp:
            runner=Path(tmp)/'run.mjs';runner.write_text(js)
            p=subprocess.run(['node',str(runner)],env={**os.environ,'TDK_MODULE':script.as_uri(),'TDK_HTML':json.dumps(html),'TDK_IDENTITY':identity},capture_output=True,text=True,timeout=60)
        self.assertEqual(p.returncode,0,p.stderr);return json.loads(p.stdout)
    def test_actual_dom_metadata_and_hash_after_delayed_update(self):
        r=self.collect('<html><head><title>Loading</title></head><body><main><span id="entity"></span></main><script>setTimeout(()=>{document.title="SOLV | BingX";document.querySelector("#entity").textContent="SOLV"},70)</script></body></html>')
        self.assertEqual(r['capture']['readiness'],'ready');self.assertIn('<title>SOLV | BingX</title>',r['html']);self.assertTrue(r['capture']['document_sha256']);self.assertGreaterEqual(r['samples'],2)
    def test_error_page_is_not_ready(self):
        r=self.collect('<main><span id="entity">SOLV</span></main><div class="error">Load failed</div>');self.assertEqual(r['capture']['readiness'],'page_error')
    def test_wrong_entity_remains_unknown(self):
        r=self.collect('<main><span id="entity">ETH</span></main>');self.assertEqual(r['capture']['readiness'],'unknown_timeout')
    def test_visible_placeholder_not_success(self):
        r=self.collect('<main><span id="entity">SOLV</span><span class="loading">--</span></main>');self.assertEqual(r['capture']['readiness'],'unknown_timeout')
    def test_hidden_loading_element_does_not_block(self):
        r=self.collect('<main><span id="entity">SOLV</span><span class="loading" hidden>--</span></main>');self.assertEqual(r['capture']['readiness'],'ready')
if __name__=='__main__':unittest.main()
