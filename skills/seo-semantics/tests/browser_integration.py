"""Real Chromium + axe contract tests; run explicitly with an isolated runtime."""
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from support import ROOT

RUNNER=r'''
const {pathToFileURL}=require('node:url');
const path=require('node:path');
(async()=>{
 const [runtime,executable,collector,scenario]=process.argv.slice(2);
 const {chromium}=require(path.join(runtime,'node_modules/playwright-core'));
 const axe=require(path.join(runtime,'node_modules/axe-core'));
 const {collectSemantics}=await import(pathToFileURL(collector).href);
 let browser;
 try{
  browser=await chromium.launch({executablePath:executable,headless:true});
  const page=await browser.newPage();
  let body='<main><h1>Fixture</h1><button id="unnamed"></button><input id="q" aria-label="Search"><div style="display:none"><h1>Hidden copy</h1></div><h2 aria-hidden="true">Visible text</h2></main>';
  if(scenario==='placeholder')body='<main><h1>Fixture</h1><div class="loading">Loading</div></main>';
  if(scenario==='identity')body='<main><h1>Wrong</h1></main>';
  if(scenario==='empty')body='<main></main><h1>Fixture</h1>';
  if(scenario==='error')body='<main><h1>Fixture</h1><p>Load failed, please try again</p></main>';
  if(scenario==='delayed')body='<main><h1></h1></main><script>setTimeout(()=>document.querySelector("h1").textContent="Fixture",80)</script>';
  await page.setContent('<!doctype html><html lang="en"><head><title>Fixture</title></head><body>'+body+'</body></html>');
  const result=await collectSemantics(page,{axeSource:axe.source,mainSelector:'main',identitySelector:'h1',expectedIdentity:'Fixture',placeholderSelector:'.loading',errorSelector:['error','ready_error_scan'].includes(scenario)?'main':'.page-error',errorText:['error','ready_error_scan'].includes(scenario)?'Load failed, please try again':undefined,timeoutMs:['placeholder','identity','empty'].includes(scenario)?120:3000,stableWindowMs:30,sampleIntervalMs:25});
  console.log(JSON.stringify(result));
 }finally{if(browser)await browser.close();}
})().catch(e=>{console.error(e.stack);process.exitCode=1});
'''

class BrowserCollectorTests(unittest.TestCase):
    def test_public_cli_emits_verifiable_manifest(self):
        if not os.environ.get('SEMANTICS_LIVE_ACCEPTANCE'):self.skipTest('Live public-site acceptance is opt-in')
        script=ROOT/'scripts/collect_page.mjs';self.assertTrue(script.is_file(),'尚未实现公开页CLI证据输出')
        runtime=os.environ['SEMANTICS_RUNTIME'];chrome=os.environ['SEMANTICS_CHROME']
        from semantics_audit.adapters import load_manifest
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);config=root/'config.json'
            config.write_text(json.dumps({'mainSelector':'.detail-wrapper','identitySelector':'.meta-name','expectedIdentity':'SOLV','placeholderSelector':'.loading-ct,.loading-svg','errorSelector':'.detail-wrapper','errorText':'Load failed, please try again'}))
            run=subprocess.run(['node',str(script),'--url','https://bingx.com/en/launchpad/detail?currency=78','--config',str(config),'--runtime',runtime,'--browser-executable',chrome,'--output',str(root/'out')],capture_output=True,text=True,timeout=100)
            self.assertEqual(run.returncode,0,run.stderr+'\n'+run.stdout)
            loaded=load_manifest(root/'out/manifest.json')
            self.assertEqual(loaded['gaps'],[]);self.assertEqual(loaded['captures'][0]['readiness'],'ready')
            self.assertEqual(loaded['tool_reports'][0]['tool'],'axe')
            self.assertTrue(loaded['tool_reports'][0]['payload']['testEngine']['version'])

    def test_error_phrase_scan_does_not_treat_healthy_main_as_failure(self):
        result=self.run_case('ready_error_scan')
        self.assertEqual(result['capture']['readiness'],'ready')

    def test_visible_error_phrase_remains_page_error(self):
        result=self.run_case('error')
        self.assertEqual(result['capture']['readiness'],'page_error')
        self.assertIsNone(result['axe'])

    def run_case(self,scenario):
        collector=ROOT/'scripts/collect_semantics.mjs'
        self.assertTrue(collector.is_file(),'尚未实现真实浏览器采集器')
        runtime=os.environ.get('SEMANTICS_RUNTIME');chrome=os.environ.get('SEMANTICS_CHROME')
        if not runtime or not chrome:self.skipTest('Set SEMANTICS_RUNTIME and SEMANTICS_CHROME for real browser tests')
        with tempfile.TemporaryDirectory() as temp:
            runner=Path(temp)/'run.cjs';runner.write_text(RUNNER)
            # Local Chrome may spend 30s in graceful teardown; page readiness keeps its own short deadline.
            process=subprocess.run(['node',str(runner),runtime,chrome,str(collector),scenario],capture_output=True,text=True,timeout=60)
            self.assertEqual(process.returncode,0,process.stderr)
            return json.loads(process.stdout)

    def test_real_axe_finds_unnamed_button_with_document_binding(self):
        result=self.run_case('ready')
        self.assertEqual(result['capture']['readiness'],'ready')
        self.assertEqual(result['axe']['testEngine']['name'],'axe-core')
        rule=next(v for v in result['axe']['violations'] if v['id']=='button-name')
        self.assertTrue(any('#unnamed' in n['target'] for n in rule['nodes']))
        self.assertEqual(result['document_sha256'],result['axe_input_sha256'])
        self.assertIn('<button id="unnamed"></button>',result['html'])

    def test_actual_hidden_and_aria_hidden_are_distinct(self):
        nodes=self.run_case('ready')['capture']['nodes']
        hidden=next(n for n in nodes if n['tag']=='h1' and n['text']=='Hidden copy')
        aria=next(n for n in nodes if n['tag']=='h2')
        self.assertEqual(hidden['visibility'],'hidden');self.assertEqual(aria['visibility'],'visible')
        self.assertEqual(aria['attributes']['aria-hidden'],'true')
        self.assertIsNone(aria['accessible_name'])

    def test_real_elements_preserve_parent_locator_and_unknown_names(self):
        nodes=self.run_case('ready')['capture']['nodes']
        button=next(n for n in nodes if n['attributes'].get('id')=='unnamed')
        main=next(n for n in nodes if n['tag']=='main')
        self.assertEqual(button['parent_id'],main['node_id'])
        self.assertTrue(button['selector']);self.assertIsNone(button['accessible_name'])
        self.assertEqual(button['attributes']['id'],'unnamed')

    def test_placeholder_is_timeout_not_success(self):
        result=self.run_case('placeholder');self.assertEqual(result['capture']['readiness'],'unknown_timeout')
        self.assertIsNone(result['axe']);self.assertIn('placeholders_present',result['unmet'])

    def test_wrong_entity_does_not_start_accessibility_certification(self):
        result=self.run_case('identity');self.assertEqual(result['capture']['readiness'],'unknown_timeout')
        self.assertIsNone(result['axe']);self.assertIn('expected_identity_not_observed',result['unmet'])

    def test_complete_document_with_empty_main_is_not_ready(self):
        result=self.run_case('empty');self.assertEqual(result['capture']['readiness'],'unknown_timeout')
        self.assertIn('main_content_missing',result['unmet'])

    def test_delayed_heading_completion_waits_for_real_dom(self):
        result=self.run_case('delayed');self.assertEqual(result['capture']['readiness'],'ready')
        self.assertTrue(any(n['tag']=='h1' and n['text']=='Fixture' for n in result['capture']['nodes']))
        self.assertGreaterEqual(result['readiness_samples'],2)

if __name__=='__main__':unittest.main()
