"""Explicit actual Chromium tests on controlled local HTML, never live-site claims."""
import hashlib,json,os,subprocess,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class LinkBrowserTests(unittest.TestCase):
    def collect(self,html,extra=None,timeout=1500):
        if not os.getenv('SEMANTICS_RUNTIME') or not os.getenv('SEMANTICS_CHROME'):self.skipTest('Actual browser runtime not configured')
        module=ROOT/'scripts/collect_links.mjs';self.assertTrue(module.exists(),'尚未实现009实际浏览器采集')
        js='''import {createRequire} from 'node:module';const require=createRequire(import.meta.url);const {chromium}=require(process.env.SEMANTICS_RUNTIME+'/node_modules/playwright-core');const {collectLinks}=await import(process.env.LINK_MODULE);const browser=await chromium.launch({executablePath:process.env.SEMANTICS_CHROME,headless:true});try{const page=await browser.newPage();await page.setContent(JSON.parse(process.env.TEST_HTML));const r=await collectLinks(page,{mainSelector:'main',identitySelector:'h1',expectedIdentity:'Prices',placeholderSelector:'.loading',errorSelector:'.error',stableWindowMs:100,sampleIntervalMs:25,timeoutMs:Number(process.env.TEST_TIMEOUT),...JSON.parse(process.env.TEST_EXTRA)});console.log(JSON.stringify(r));}finally{await browser.close();}'''
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'run.mjs';p.write_text(js);r=subprocess.run(['node',str(p)],env={**os.environ,'LINK_MODULE':module.as_uri(),'TEST_HTML':json.dumps(html),'TEST_EXTRA':json.dumps(extra or {}),'TEST_TIMEOUT':str(timeout)},capture_output=True,text=True,timeout=60)
        self.assertEqual(r.returncode,0,r.stderr);return json.loads(r.stdout)
    def test_delayed_actual_href_and_bound_visible_snapshot(self):
        r=self.collect('<main><h1>Prices</h1><div id="list"></div></main><script>setTimeout(()=>document.querySelector("#list").innerHTML=\'<a href="/en/price/bitcoin">BTC</a>\',150)</script>',{'itemSelector':'#list a','itemAttribute':'href'})
        self.assertEqual(r['capture']['readiness'],'ready');self.assertEqual(r['browser']['item_keys'],['/en/price/bitcoin']);self.assertEqual(r['browser']['document_sha256'],hashlib.sha256(r['html'].encode()).hexdigest())
    def test_hidden_links_are_preserved_with_visibility_not_removed_from_inventory(self):
        r=self.collect('<main><h1>Prices</h1><a href="/visible">Visible</a><div style="display:none"><a href="/hidden">Hidden</a></div></main>');self.assertEqual([x['visible'] for x in r['browser']['links']],[True,False])
    def test_click_transition_cannot_settle_on_previous_item_set(self):
        r=self.collect('<main><h1>Prices</h1><a class="item" href="/old">Old</a></main>',{'itemSelector':'.item','itemAttribute':'href','previousItemKeys':['/old']},timeout=400)
        self.assertEqual(r['capture']['readiness'],'unknown_timeout');self.assertIn('items_not_changed',r['unmet'])
    def test_real_business_items_must_exist_if_selector_configured(self):
        r=self.collect('<main><h1>Prices</h1></main>',{'itemSelector':'.item','itemAttribute':'href'},timeout=400);self.assertEqual(r['capture']['readiness'],'unknown_timeout')
    def test_wrong_entity_cannot_be_promoted_by_existing_links(self):
        r=self.collect('<main><h1>Wrong</h1><a href="/a">A</a></main>',timeout=250);self.assertNotEqual(r['capture']['readiness'],'ready')
    def test_locator_indices_account_for_controls_between_anchors(self):
        r=self.collect('<main><h1>Prices</h1><button>Next</button><a href="/a">A</a><span role="link">More</span><a href="/b">B</a></main>');self.assertEqual([x['locator'] for x in r['browser']['links']],['a[observed-index=1]','a[observed-index=3]'])
    def test_actual_browser_redirect_chain_retains_original_href_response(self):
        if not os.getenv('SEMANTICS_RUNTIME') or not os.getenv('SEMANTICS_CHROME'):self.skipTest('Actual browser runtime not configured')
        module=ROOT/'scripts/collect_responses.mjs';self.assertTrue(module.exists(),'尚未实现实际HTTP跳转链采集')
        js='''import {createRequire} from 'node:module';const require=createRequire(import.meta.url);const {chromium}=require(process.env.SEMANTICS_RUNTIME+'/node_modules/playwright-core');const {observeRedirectChain}=await import(process.env.LINK_MODULE);const {createServer}=await import('node:http');const server=createServer((req,res)=>{if(req.url==='/old'){res.writeHead(302,{location:'/new','set-cookie':'private=value'});res.end();}else{res.writeHead(200,{'content-type':'text/html'});res.end('<h1>New</h1>');}});await new Promise(r=>server.listen(0,'127.0.0.1',r));const b=await chromium.launch({executablePath:process.env.SEMANTICS_CHROME,headless:true});try{const p=await b.newPage();const response=await p.goto('http://127.0.0.1:'+server.address().port+'/old');console.log(JSON.stringify(await observeRedirectChain(response)));}finally{await b.close();server.close();}'''
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'run.mjs';p.write_text(js);r=subprocess.run(['node',str(p)],env={**os.environ,'LINK_MODULE':module.as_uri()},capture_output=True,text=True,timeout=60)
        self.assertEqual(r.returncode,0,r.stderr);rows=json.loads(r.stdout);self.assertEqual([x['url'].rsplit('/',1)[-1] for x in rows],['old','new']);self.assertTrue(all(x['url'].startswith('http://127.0.0.1:') for x in rows));self.assertEqual([x['status'] for x in rows],[302,200]);self.assertNotIn('private=value',r.stdout);self.assertEqual(rows[0]['method'],'GET')
if __name__=='__main__':unittest.main()
