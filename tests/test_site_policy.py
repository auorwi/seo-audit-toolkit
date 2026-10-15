import unittest,os,json,tempfile,sys,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'skills/seo-crawlability/scripts'))

class SitePolicy(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.old=os.environ.get('SEO_SITE_PROFILE');self.addCleanup(self.restore)
  self.profile={'site':'example.com','allowed_hosts':['example.com'],'seeds':['https://example.com/']};self.write()
 def restore(self):
  if self.old is None:os.environ.pop('SEO_SITE_PROFILE',None)
  else:os.environ['SEO_SITE_PROFILE']=self.old
 def write(self):
  p=Path(self.tmp.name)/'site.json';p.write_text(json.dumps(self.profile));os.environ['SEO_SITE_PROFILE']=str(p)
 def test_missing_profile_fails_closed(self):
  from crawlability.site import get_profile,in_scope
  os.environ.pop('SEO_SITE_PROFILE');self.assertFalse(in_scope('https://bingx.com/'))
  with self.assertRaises(ValueError):get_profile()
 def test_exact_host_and_public_url_policy(self):
  from crawlability.site import in_scope,require_url
  for u in ['https://example.com/','http://example.com/','https://EXAMPLE.com:443/a','http://example.com:80/']:
   self.assertTrue(in_scope(u),u)
  for u in ['https://www.example.com/','https://example.com.attacker.org/','https://u:p@example.com/','ftp://example.com/','https://example.com:8443/','https://example.com/?api_key=secret','https://example.com/?access_token=secret','https://example.com/?%65mail=private','https://example.com\\@attacker.org/','https://example.com./']:
   self.assertFalse(in_scope(u),u)
   with self.assertRaises(ValueError,msg=u):require_url(u)
 def test_private_and_subdomain_isolation(self):
  from crawlability.site import in_scope
  self.profile.update(site='localhost',allowed_hosts=['localhost'],seeds=[]);self.write();self.assertFalse(in_scope('http://localhost/'))
  self.profile.update(site='127.0.0.1',allowed_hosts=['127.0.0.1']);self.write();self.assertFalse(in_scope('http://127.0.0.1/'))
 def test_profile_change_and_explicit_punycode(self):
  from crawlability.site import site_host,site_origin,brand_name,business_profile,in_scope
  self.assertEqual(site_host(),'example.com');self.assertEqual(site_origin(),'https://example.com');self.assertEqual(brand_name(),'example.com');self.assertEqual(business_profile(),'generic')
  self.profile.update(site='xn--bcher-kva.de',allowed_hosts=['xn--bcher-kva.de'],seeds=['https://xn--bcher-kva.de/'],brand='Bücher');self.write()
  self.assertEqual(site_host(),'xn--bcher-kva.de');self.assertTrue(in_scope('https://xn--bcher-kva.de/'));self.assertFalse(in_scope('https://bücher.de/'));self.assertTrue(in_scope('https://xn--bcher-kva.de/über'));self.assertEqual(brand_name(),'Bücher')
 def test_fixture_loopback_requires_exact_port(self):
  from crawlability.site import in_scope
  self.profile.update(site='127.0.0.1',allowed_hosts=['127.0.0.1'],seeds=[],test_only_allow_loopback=True,fixture_port=8765);self.write()
  self.assertTrue(in_scope('http://127.0.0.1:8765/'));self.assertFalse(in_scope('http://127.0.0.1:8766/'));self.assertFalse(in_scope('http://127.0.0.2:8765/'))
 def test_js_python_policy_parity(self):
  import shutil
  if not shutil.which('node'):self.skipTest('Node unavailable')
  from crawlability.site import in_scope
  urls=['https://example.com/','http://example.com:80/','https://example.com:8443/','https://x.example.com/','https://example.com/?token=x','https://u@example.com/','https://example.com./','https://example.com/%20']
  module=(ROOT/'skills/seo-crawlability/scripts/site.mjs').as_uri()
  result=subprocess.run(['node','--input-type=module','-e',f"import {{allowed}} from {json.dumps(module)}; console.log(JSON.stringify({json.dumps(urls)}.map(allowed)));"],capture_output=True,text=True,check=True)
  self.assertEqual(json.loads(result.stdout),[in_scope(u) for u in urls])
 def test_noncanonical_numeric_host_and_profile_credentials_rejected(self):
  from crawlability.site import in_scope,get_profile
  self.profile.update(site='127.1',allowed_hosts=['127.1'],seeds=[]);self.write();self.assertFalse(in_scope('http://127.1/'))
  self.profile.update(site='example.com',allowed_hosts=['example.com'],password='private');self.write()
  with self.assertRaises(ValueError):get_profile()
 def test_browser_scope_guard_and_generic_readiness_contract(self):
  import shutil
  if not shutil.which('node'):self.skipTest('Node unavailable')
  module=(ROOT/'skills/seo-crawlability/scripts/site.mjs').as_uri()
  code=f"import {{protectPage,readinessConfig}} from {json.dumps(module)}; let handler;let result;const session={{on:(name,fn)=>handler=fn,send:async method=>{{if(method==='Fetch.failRequest')result='blocked';if(method==='Fetch.continueRequest')result='followed';}}}};await protectPage({{context:()=>({{newCDPSession:async()=>session}})}});await handler({{requestId:'fixture',resourceType:'Document',request:{{url:'https://foreign.example.org/'}}}});const generic=readinessConfig();const strong=readinessConfig({{identitySelector:'h1',expectedIdentity:'Product'}});console.log(JSON.stringify({{result,generic,strong}}));"
  result=subprocess.run(['node','--input-type=module','-e',code],capture_output=True,text=True,check=True);value=json.loads(result.stdout)
  self.assertEqual(value['result'],'blocked');self.assertFalse(value['generic']['identityRequired']);self.assertFalse(value['generic']['identityVerified']);self.assertIn('unverified',value['generic']['readinessBasis']);self.assertTrue(value['strong']['identityRequired']);self.assertEqual(value['strong']['expectedIdentity'],'Product')
 def test_unicode_host_profiles_rejected_with_punycode_guidance_in_both_runtimes(self):
  from crawlability.site import get_profile
  module=(ROOT/'skills/seo-crawlability/scripts/site.mjs').as_uri()
  for host in ['faß.de','ς.gr','a\u200cb.de','a\u200db.de','K.com','bücher.de','ｅxample.com']:
   with self.subTest(host=host):
    self.profile.update(site=host,allowed_hosts=[host],seeds=[]);self.write()
    with self.assertRaisesRegex(ValueError,'punycode'):get_profile()
    result=subprocess.run(['node','--input-type=module','-e',f"import {{getProfile}} from {json.dumps(module)};try{{getProfile();process.exitCode=1;}}catch(e){{console.log(e.message);}}"],capture_output=True,text=True,check=True)
    self.assertIn('punycode',result.stdout)
 def test_unicode_url_gate_parity_with_ascii_profiles(self):
  from crawlability.site import in_scope
  module=(ROOT/'skills/seo-crawlability/scripts/site.mjs').as_uri()
  for host in ['xn--fa-hia.de','fass.de','k.com']:
   self.profile.update(site=host,allowed_hosts=[host],seeds=[]);self.write()
   urls=['https://faß.de/','https://fass.de/','https://xn--fa-hia.de/','https://K.com/','https://k.com/','https://a\u200cb.de/']
   expected=[u=='https://'+host+'/' for u in urls]
   self.assertEqual([in_scope(u) for u in urls],expected)
   result=subprocess.run(['node','--input-type=module','-e',f"import {{allowed}} from {json.dumps(module)};console.log(JSON.stringify({json.dumps(urls)}.map(allowed)));"],capture_output=True,text=True,check=True)
   self.assertEqual(json.loads(result.stdout),expected)
if __name__=='__main__':unittest.main()
