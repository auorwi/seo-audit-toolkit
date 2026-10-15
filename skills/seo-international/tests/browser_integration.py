"""Real Chromium on controlled documents; these are not BingX live findings."""
import os,json,hashlib,subprocess,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class InternationalBrowserTests(unittest.TestCase):
    def collect(self,html,extra=None,mode='collect'):
        self.assertTrue((ROOT/'scripts/collect_international.mjs').exists(),'尚未实现010浏览器采集')
        js='''import {createRequire} from 'node:module';const require=createRequire(import.meta.url);const {chromium}=require(process.env.SEMANTICS_RUNTIME+'/node_modules/playwright-core');const {collectInternational,performLanguageSwitch}=await import(process.env.MODULE);const b=await chromium.launch({executablePath:process.env.SEMANTICS_CHROME,headless:true});try{const p=await b.newPage();await p.setContent(JSON.parse(process.env.HTML));const config={mainSelector:'main',identitySelector:'h1',expectedIdentity:'Bitcoin',placeholderSelector:'.loading',errorSelector:'.error',timeoutMs:1200,stableWindowMs:100,sampleIntervalMs:25,...JSON.parse(process.env.EXTRA)};const before=await collectInternational(p,config);if(process.env.MODE==='switch'){console.log(JSON.stringify(await performLanguageSwitch(p,before,'#fr',{...config,requiredText:'Prix du Bitcoin'},{expectedText:'Français',expectedLocale:'fr'})));}else if(process.env.MODE==='wrong'){try{await performLanguageSwitch(p,before,'#fr',config,{expectedText:'Wrong',expectedLocale:'fr'});console.log(JSON.stringify({error:null}));}catch(e){console.log(JSON.stringify({error:e.message,main:await p.locator('main').innerText()}));}}else console.log(JSON.stringify(before));}finally{await b.close();}'''
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'run.mjs';p.write_text(js);r=subprocess.run(['node',str(p)],env={**os.environ,'MODULE':(ROOT/'scripts/collect_international.mjs').as_uri(),'HTML':json.dumps(html),'EXTRA':json.dumps(extra or {}),'MODE':mode},capture_output=True,text=True,timeout=60)
        self.assertEqual(r.returncode,0,r.stderr);return json.loads(r.stdout)
    def test_actual_visible_main_and_snapshot_bound(self):
        r=self.collect('<html lang="fr"><main><h1>Bitcoin</h1><p>Prix du Bitcoin</p><p hidden>Hidden text</p></main></html>');self.assertEqual(r['capture']['readiness'],'ready');self.assertIn('Prix du Bitcoin',r['browser']['visible_main']);self.assertNotIn('Hidden text',r['browser']['visible_main']);self.assertEqual(r['browser']['document_sha256'],hashlib.sha256(r['html'].encode()).hexdigest())
    def test_waits_for_actual_translated_business_text(self):
        r=self.collect('<main><h1>Bitcoin</h1><p id="body">Loading</p></main><script>setTimeout(()=>{document.documentElement.lang="fr";document.querySelector("#body").innerText="Prix du Bitcoin"},250)</script>',{'expectedHtmlLang':'fr','requiredText':'Prix du Bitcoin'});self.assertEqual(r['capture']['readiness'],'ready');self.assertIn('Prix du Bitcoin',r['browser']['visible_main'])
    def test_unready_language_not_promoted(self):
        r=self.collect('<html lang="en"><main><h1>Bitcoin</h1><p>Bitcoin price</p></main></html>',{'expectedHtmlLang':'fr','timeoutMs':350});self.assertEqual(r['capture']['readiness'],'unknown_timeout')
    def test_missing_business_field_is_observation(self):
        r=self.collect('<main><h1>Bitcoin</h1><select id="currency"></select></main>',{'fieldSelectors':{'country':'#country','currency':'#currency'}});self.assertEqual(r['browser']['visible_fields'],{'country':False,'currency':True})
    def test_real_click_retains_same_url_and_entity_text(self):
        r=self.collect('<main><h1>Bitcoin</h1><p id="body">Bitcoin price</p><button id="fr" onclick="document.documentElement.lang=\'fr\';document.querySelector(\'#body\').innerText=\'Prix du Bitcoin\'">Français</button></main>',mode='switch');self.assertEqual(r['after']['capture']['readiness'],'ready');self.assertEqual(r['action']['before_url'],r['action']['after_url']);self.assertEqual(r['action']['expected_locale'],'fr');self.assertIn('Prix du Bitcoin',r['after']['browser']['visible_main'])
    def test_wrong_switch_label_stops_before_click(self):
        r=self.collect('<main><h1>Bitcoin</h1><p id="body">Bitcoin price</p><button id="fr" onclick="document.querySelector(\'#body\').innerText=\'changed\'">Français</button></main>',mode='wrong');self.assertEqual(r['error'],'switch_label_mismatch');self.assertIn('Bitcoin price',r['main'])
if __name__=='__main__':unittest.main()
