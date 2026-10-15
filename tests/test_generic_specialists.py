import unittest, sys, tempfile, json, os, hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for skill in ROOT.glob('skills/seo-*'):
 sys.path.insert(0,str(skill/'scripts'))

class GenericSpecialists(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
  self.old=os.environ.get('SEO_SITE_PROFILE');self.addCleanup(self.restore)
  p=Path(self.tmp.name)/'site.json';p.write_text(json.dumps({'site':'example.com','allowed_hosts':['example.com'],'seeds':['https://example.com/'],'business_profile':'generic'}));os.environ['SEO_SITE_PROFILE']=str(p)
 def restore(self):
  if self.old is None:os.environ.pop('SEO_SITE_PROFILE',None)
  else:os.environ['SEO_SITE_PROFILE']=self.old
 def test_generic_metadata_audit(self):
  from tdk_audit.audit import audit
  result=audit([],['https://example.com/'],at='2026-10-15T00:00:00Z')
  self.assertEqual(result['skill'],'007')
 def test_generic_platform_properties(self):
  from gsc_audit.contracts import property_id
  from bing_audit.contracts import site_id
  from yandex_audit.contracts import host_url
  self.assertEqual(property_id('sc-domain:example.com'),'sc-domain:example.com')
  self.assertEqual(site_id('https://example.com/'),'https://example.com/')
  self.assertEqual(host_url('https:example.com:443'),'https://example.com/')
 def test_generic_report_manifest(self):
  from seo_report.core import load_manifest
  p=Path(self.tmp.name); b=json.dumps({'skill':'003','at':'2026-10-15T00:00:00Z','findings':[],'coverage':{}}).encode();(p/'source.json').write_bytes(b)
  m={'site':'example.com','run_id':'generic','at':'2026-10-15T00:00:00Z','requested_skills':['003'],'sources':[{'skill':'003','path':'source.json','sha256':hashlib.sha256(b).hexdigest()}]};(p/'manifest.json').write_text(json.dumps(m))
  self.assertEqual(load_manifest(p/'manifest.json')['site'],'example.com')
 def test_declared_foreign_scope_rejected(self):
  from crawlability.audit import audit as crawl
  from canonical_routing.audit import audit as canonical
  from rendering_audit.audit import audit as rendering
  from semantics_audit.audit import audit as semantics
  with self.assertRaises(ValueError):semantics([],[],['https://foreign.example.org/'],at='2026-10-15T00:00:00Z')
  for fn in (crawl,canonical,rendering):
   with self.subTest(fn=fn.__module__),self.assertRaises(ValueError):fn([],['https://foreign.example.org/'],at='2026-10-15T00:00:00Z')
 def test_generic_route_has_no_crypto_assumptions(self):
  from url_inventory.identity import classify
  r=classify('https://example.com/en/price/bitcoin')
  self.assertFalse(r['classified']);self.assertEqual(r['entities'],{});self.assertEqual(r['template'],'/en/price/bitcoin')
 def test_generic_market_fetch_refused_before_network(self):
  from content_integrity.reference_fetch import fetch
  with self.assertRaisesRegex(ValueError,'business_profile'):fetch('BTC-USDT')
 def test_live_http_cannot_enable_benchmark_dns_bypass(self):
  from url_inventory.network import HttpClient
  with self.assertRaisesRegex(ValueError,'benchmark_alias'):HttpClient(['example.com'],allow_benchmark_alias=True)
 def test_semantics_direct_cli_foreign_target_fails_without_output(self):
  import subprocess
  root=Path(self.tmp.name);manifest=root/'manifest.json';manifest.write_text(json.dumps({'schema_version':1,'captures':[],'tool_reports':[]}))
  script=ROOT/'skills/seo-semantics/scripts/audit_semantics.py'
  for kind in ('--url','--urls'):
   target='https://foreign.example.org/'
   if kind=='--urls':
    path=root/'urls.json';path.write_text(json.dumps([target]));target=str(path)
   output=root/('output'+kind);state=root/('state'+kind)
   result=subprocess.run([sys.executable,str(script),'--manifest',str(manifest),kind,target,'--state',str(state),'--output',str(output),'--at','2026-10-15T00:00:00Z'],capture_output=True,text=True)
   self.assertEqual(result.returncode,1,result.stdout);self.assertIn('outside_configured_site',result.stderr);self.assertFalse(output.exists());self.assertFalse((state/'issues.sqlite').exists())
 def test_evidence_normalizers_reject_unicode_authority_before_mapping(self):
  from crawlability.common import url_id
  from crawlability.robots import _origin
  from url_inventory.identity import normalize_url
  from sitemap_audit.xmlrules import identity
  for fn in (url_id,_origin,normalize_url,identity):
   for host in ['faß.de','bücher.de','K.com','a\u200cb.de']:
    with self.subTest(normalizer=fn.__module__,host=host),self.assertRaises(ValueError):fn('https://'+host+'/')
   self.assertIn('xn--fa-hia.de',str(fn('https://xn--fa-hia.de/')))
 def test_js_cli_rejects_raw_unicode_before_url_constructor_mapping(self):
  import subprocess
  p=Path(self.tmp.name)/'site.json';p.write_text(json.dumps({'site':'xn--fa-hia.de','allowed_hosts':['xn--fa-hia.de'],'seeds':[]}))
  for skill in ('seo-tdk','seo-semantics'):
   result=subprocess.run(['node',str(ROOT/'skills'/skill/'scripts/collect_page.mjs'),'--url','https://faß.de/'],capture_output=True,text=True)
   self.assertIn('unsupported_target',result.stderr)
 def test_extruct_cli_rejects_unicode_base_host_before_extracting(self):
  import subprocess
  root=Path(self.tmp.name);html=root/'page.html';html.write_text('<html><body>Evidence fixture</body></html>');output=root/'extruct.json'
  script=ROOT/'skills/seo-structured-data/scripts/extract_embedded.py'
  result=subprocess.run([sys.executable,str(script),'--html',str(html),'--url','https://faß.de/','--output',str(output)],capture_output=True,text=True)
  self.assertEqual(result.returncode,1,result.stdout);self.assertIn('punycode',result.stderr);self.assertFalse(output.exists())
 def test_cwv_bundled_sample_is_explicit_historical_fixture(self):
  seed=json.loads((ROOT/'skills/seo-cwv/references/approved-sample-seed.json').read_text())
  self.assertIsInstance(seed,dict);self.assertEqual(seed['run_kind'],'historical_fixture');self.assertEqual(seed['selection'],'explicit_opt_in_only');self.assertFalse(seed['live_evidence'])
  self.assertEqual(len(seed['targets']),8)
  workflow=(ROOT/'skills/seo-cwv/SKILL.md').read_text().split('## 执行顺序',1)[1].split('## 工具调用',1)[0]
  self.assertNotIn('全面基线使用[既有8页清单]',workflow)
 def test_optional_controlled_chromium_collectors(self):
  import subprocess
  runtime=os.getenv('SEO_BROWSER_RUNTIME');chrome=os.getenv('SEO_BROWSER_EXECUTABLE')
  if not runtime or not chrome:self.skipTest('Explicit optional browser runtime/executable not configured')
  runner=Path(self.tmp.name)/'browser.mjs'
  runner.write_text(BROWSER_FIXTURE)
  env=dict(os.environ,SEMANTICS_RUNTIME=runtime,SEMANTICS_CHROME=chrome,SITE_MODULE=(ROOT/'skills/seo-crawlability/scripts/site.mjs').as_uri(),TDK_MODULE=(ROOT/'skills/seo-tdk/scripts/collect_metadata.mjs').as_uri(),SEO_SITE_PROFILE=str(Path(self.tmp.name)/'browser-profile.json'))
  result=subprocess.run(['node',str(runner)],env=env,capture_output=True,text=True,timeout=60)
  self.assertEqual(result.returncode,0,result.stderr)
  observed=json.loads(result.stdout);self.assertTrue(observed['outside_redirect_blocked']);self.assertEqual(len(observed['collectorResults']),7);self.assertFalse(observed['identity_verified'])

BROWSER_FIXTURE=r"""
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import http from 'node:http';
import fs from 'node:fs';
const require=createRequire(import.meta.url);
const {chromium}=require(process.env.SEMANTICS_RUNTIME+'/node_modules/playwright-core');
const {protectPage}=await import(process.env.SITE_MODULE);
const {collectMetadata}=await import(process.env.TDK_MODULE);
const server=http.createServer((req,res)=>{
 if(req.url==='/redirect'){res.writeHead(302,{Location:'https://example.com/outside'});res.end();return;}
 res.writeHead(200,{'Content-Type':'text/html'});res.end('<!doctype html><html><head><title>Generic products</title></head><body><main><h1>Generic product catalogue</h1><p>Current public product documentation.</p></main></body></html>');
});
await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
const port=server.address().port;
fs.writeFileSync(process.env.SEO_SITE_PROFILE,JSON.stringify({site:'127.0.0.1',allowed_hosts:['127.0.0.1'],seeds:[],business_profile:'generic',test_only_allow_loopback:true,fixture_port:port}));
let browser;
try{
 browser=await chromium.launch({executablePath:process.env.SEMANTICS_CHROME,headless:true});
 const page=await browser.newPage();await protectPage(page);await page.goto('http://127.0.0.1:'+port+'/');
 const generic=await collectMetadata(page,{stableWindowMs:20,sampleIntervalMs:10,timeoutMs:1000});
 assert.equal(generic.capture.readiness,'ready');assert.equal(generic.capture.identity_verified,false);assert.match(generic.capture.readiness_basis,/unverified/);
 const collectorResults={tdk:generic.capture.readiness};
 const root=process.env.SITE_MODULE;
 const options={stableWindowMs:20,sampleIntervalMs:10,timeoutMs:1000};
 for(const [skill,file,name] of [['seo-internal-links','collect_links.mjs','collectLinks'],['seo-international','collect_international.mjs','collectInternational'],['seo-structured-data','collect_structured.mjs','collectStructured'],['seo-content-integrity','collect_content.mjs','collectContent'],['seo-media','collect_media.mjs','collectMedia'],['seo-semantics','collect_semantics.mjs','collectSemantics']]){
  const module=new URL('../../'+skill+'/scripts/'+file,root);
  const fn=(await import(module))[name];const config={...options};
  if(skill==='seo-semantics')config.axeSource=require(process.env.SEMANTICS_RUNTIME+'/node_modules/axe-core').source;
  const result=await fn(page,config);const capture=result.capture??result;
  assert.equal(capture.readiness,'ready',skill+': '+JSON.stringify(result.unmet??result.readiness_gaps));assert.equal(capture.identity_verified,false,skill);assert.match(capture.readiness_basis,/unverified/,skill);
  collectorResults[skill]=capture.readiness;
 }
 const strong=await collectMetadata(page,{mainSelector:'main',identitySelector:'h1',expectedIdentity:'Wrong product',stableWindowMs:20,sampleIntervalMs:10,timeoutMs:100});
 assert.equal(strong.capture.readiness,'unknown_timeout');assert.ok(strong.unmet.includes('entity_not_observed'));
 let rejected=false;try{await page.goto('http://127.0.0.1:'+port+'/redirect');}catch{rejected=true;}
 assert.equal(rejected,true);
 console.log(JSON.stringify({controlled_fixture:true,generic_readiness:generic.capture.readiness,identity_verified:generic.capture.identity_verified,strong_identity_mismatch:strong.capture.readiness,outside_redirect_blocked:rejected,collectorResults,browser:browser.version()}));
}finally{if(browser)await browser.close();server.close();}
"""
if __name__=='__main__':unittest.main()
