"""Opt-in real Chromium fixtures; never presented as live BingX evidence."""
import os,json,subprocess,tempfile,unittest,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class ContentBrowserTests(unittest.TestCase):
    def run_browser(self,html,mode='capture',extra=None,quantity='10'):
        self.assertTrue((ROOT/'scripts/collect_content.mjs').is_file(),'012 collector not implemented')
        js='''import {createRequire} from 'node:module';const require=createRequire(import.meta.url);const {chromium}=require(process.env.SEMANTICS_RUNTIME+'/node_modules/playwright-core');const {collectContent,performTrial,performScenario}=await import(process.env.MODULE);const b=await chromium.launch({executablePath:process.env.SEMANTICS_CHROME,headless:true});try{const p=await b.newPage();await p.setContent(JSON.parse(process.env.HTML));const c={mainSelector:'main',identitySelector:'h1',expectedIdentity:'Bitcoin',placeholderSelector:'.loading',errorSelector:'.error',timeoutMs:1800,stableWindowMs:150,sampleIntervalMs:40,fieldSelectors:{price:'#price',input:'#quantity',output:'#output',rate:'#rate',input_unit:'#input-unit',output_unit:'#output-unit'},...JSON.parse(process.env.EXTRA)};console.log(JSON.stringify(process.env.MODE==='scenario'?await performScenario(p,c,{inputSelector:'#quantity',growthPercent:process.env.QUANTITY}):process.env.MODE==='trial'?await performTrial(p,c,{inputSelector:'#quantity',quantity:process.env.QUANTITY,direction:'asset_to_quote'}):await collectContent(p,c)));}finally{await b.close();}'''
        with tempfile.TemporaryDirectory() as tmp:
            script=Path(tmp)/'run.mjs';script.write_text(js)
            r=subprocess.run(['node',str(script)],env={**os.environ,'MODULE':(ROOT/'scripts/collect_content.mjs').as_uri(),'HTML':json.dumps(html),'MODE':mode,'EXTRA':json.dumps(extra or {}),'QUANTITY':quantity},capture_output=True,text=True,timeout=90)
        self.assertEqual(r.returncode,0,r.stderr);return json.loads(r.stdout)
    def html(self,script="document.querySelector('#output').innerText=Number(this.value)*2"):
        return '<main><h1>Bitcoin</h1><input id="quantity" type="text" value="1" oninput="'+script+'"><span id="output">2</span><span id="rate">2</span><span id="input-unit">BTC</span><span id="output-unit">EUR</span></main>'
    def test_capture_hash_visible_fields(self):
        r=self.run_browser('<main><h1>Bitcoin</h1><b id="price">100</b><p hidden>secret</p></main>');self.assertEqual(r['readiness'],'ready');self.assertEqual(r['document_sha256'],hashlib.sha256(r['html'].encode()).hexdigest());self.assertEqual(r['fields']['price']['text'],'100');self.assertNotIn('secret',r['visible_main'])
    def test_actual_input_changes_output(self):
        r=self.run_browser(self.html(),'trial');self.assertEqual(r['action']['status'],'completed');self.assertEqual(r['before']['fields']['input']['value'],'1');self.assertEqual(r['after']['fields']['input']['value'],'10');self.assertEqual(r['after']['fields']['output']['text'],'20')
    def test_stuck_output_preserved(self):
        r=self.run_browser(self.html('void 0'),'trial');self.assertEqual(r['after']['fields']['output']['text'],'2');self.assertEqual(r['after']['fields']['input']['value'],'10')
    def test_readonly_control_never_marked_completed(self):
        r=self.run_browser(self.html().replace('type="text"','type="text" readonly'),'trial');self.assertEqual(r['action']['status'],'failed');self.assertIn('control_not_editable',r['action']['reason'])
    def test_password_control_rejected(self):
        r=self.run_browser(self.html().replace('type="text"','type="password"'),'trial');self.assertEqual(r['action']['status'],'failed');self.assertEqual(r['after']['fields']['input']['value'],None)
    def test_wrong_entity_stops_action(self):
        r=self.run_browser(self.html().replace('<h1>Bitcoin','<h1>Ethereum'),'trial',{'timeoutMs':500});self.assertEqual(r['action']['status'],'failed');self.assertEqual(r['after']['fields']['input']['value'],'1')
    def test_loading_waits_until_actual_data(self):
        r=self.run_browser('<main><h1>Bitcoin</h1><b class="loading">loading</b><b id="price">--</b></main><script>setTimeout(()=>{document.querySelector(".loading").remove();document.querySelector("#price").innerText="120"},300)</script>');self.assertEqual(r['fields']['price']['text'],'120');self.assertEqual(r['readiness'],'ready')
    def test_missing_field_distinct_from_empty(self):
        r=self.run_browser('<main><h1>Bitcoin</h1><b id="price"></b></main>');self.assertTrue(r['fields']['price']['present']);self.assertEqual(r['fields']['price']['text'],'');self.assertFalse(r['fields']['output']['present'])
    def test_delayed_calculator_output_observed(self):
        script="setTimeout(()=>document.querySelector('#output').innerText=Number(this.value)*2,400)"
        r=self.run_browser(self.html(script),'trial');self.assertEqual(r['after']['fields']['output']['text'],'20')
    def test_business_field_waits_beyond_metadata(self):
        r=self.run_browser('<main><h1>Bitcoin</h1><b id="price"></b></main><script>setTimeout(()=>document.querySelector("#price").innerText="150",700)</script>',extra={'requiredFields':{'price':{'pattern':'^[0-9]+$'}}});self.assertEqual(r['readiness'],'ready');self.assertEqual(r['fields']['price']['text'],'150')
    def test_empty_required_value_does_not_pass(self):
        r=self.run_browser('<main><h1>Bitcoin</h1><b id="price"></b></main>',extra={'timeoutMs':500,'requiredFields':{'price':{'nonEmpty':True}}});self.assertEqual(r['readiness'],'unknown_timeout')
    def test_actual_forecast_growth_changes_table(self):
        r=self.run_browser(self.html("document.querySelector('#output').innerText='2031: '+(100*(1+Number(this.value)/100))"),'scenario',quantity='2');self.assertEqual(r['action']['status'],'completed');self.assertEqual(r['after']['fields']['output']['text'],'2031: 102');self.assertEqual(r['action']['growth_percent'],'2')
    def test_forecast_unsupported_growth_not_applied(self):
        r=self.run_browser(self.html(),'scenario',quantity='2000');self.assertEqual(r['action']['status'],'failed');self.assertEqual(r['after']['fields']['input']['value'],'1')
    def test_forecast_percent_mask_preserved(self):
        html=self.html("this.value=this.value.slice(0,-1)+'%';document.querySelector('#output').innerText=100*(1+Number(this.value.slice(0,-1))/100)").replace('value="1"','value="5%"')
        r=self.run_browser(html,'scenario',quantity='2');self.assertEqual(r['action']['applied_input'],'2%');self.assertEqual(r['after']['fields']['output']['text'],'102')
    def test_forecast_erased_input_not_completed(self):
        html=self.html("this.value='%' ")
        r=self.run_browser(html,'scenario',quantity='2');self.assertEqual(r['action']['status'],'failed');self.assertEqual(r['action']['reason'],'growth_input_not_applied')
if __name__=='__main__':unittest.main()
