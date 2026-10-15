from support import CWVTest,URL,AT
def lhr():return {'lighthouseVersion':'12.6.1','requestedUrl':URL,'finalDisplayedUrl':URL,'fetchTime':AT,'environment':{'hostUserAgent':'Chrome/153.0.8010.36','networkUserAgent':'Mobile Chrome/153','benchmarkIndex':900},'configSettings':{'formFactor':'mobile','throttlingMethod':'simulate','throttling':{'cpuSlowdownMultiplier':4,'rttMs':150},'screenEmulation':{'width':412,'height':823,'mobile':True},'locale':'en-US','disableStorageReset':False},'categories':{'performance':{'score':0.52}},'audits':{'largest-contentful-paint':{'numericValue':3200,'numericUnit':'millisecond','scoreDisplayMode':'numeric'},'cumulative-layout-shift':{'numericValue':0.13,'numericUnit':'unitless','scoreDisplayMode':'numeric'},'total-blocking-time':{'numericValue':700,'numericUnit':'millisecond'},'first-contentful-paint':{'numericValue':1100,'numericUnit':'millisecond'}}}
CTX={'runner':'lhci','host_id':'test-machine','network_location':'test','entry_mode':'direct','login':'unauthenticated','source':'actual LHR'}
class LabTests(CWVTest):
    def parse(self,d=None,ctx=None):return self.module('lab').parse_lhr(d or lhr(),ctx or CTX)
    def test_ms_not_score(self):self.assertEqual(self.parse()['metrics']['LCP'],3200)
    def test_cls_unitless(self):self.assertEqual(self.parse()['metrics']['CLS'],0.13)
    def test_tbt_kept_separate(self):self.assertEqual(self.parse()['metrics']['TBT'],700);self.assertIsNone(self.parse()['metrics']['INP'])
    def test_score_not_field_pass(self):self.assertEqual(self.parse()['field_assessment'],'not_available_from_lighthouse')
    def test_runtime_error_invalid(self):
        d=lhr();d['runtimeError']={'code':'NO_FCP','message':'No paint'};self.assertFalse(self.parse(d)['valid_measurement'])
    def test_missing_lcp_not_zero(self):
        d=lhr();del d['audits']['largest-contentful-paint'];self.assertIsNone(self.parse(d)['metrics']['LCP']);self.assertFalse(self.parse(d)['valid_measurement'])
    def test_wrong_metric_unit_invalid(self):
        d=lhr();d['audits']['largest-contentful-paint']['numericUnit']='second';self.assertIsNone(self.parse(d)['metrics']['LCP'])
    def test_metric_error_mode_invalid(self):
        d=lhr();d['audits']['largest-contentful-paint']['scoreDisplayMode']='error';self.assertFalse(self.parse(d)['valid_measurement'])
    def test_wrong_final_url_not_silent(self):
        d=lhr();d['finalDisplayedUrl']='https://bingx.com/en/';r=self.parse(d);self.assertFalse(r['valid_measurement']);self.assertEqual(r['final_url'],'https://bingx.com/en/')
    def test_approved_final_equivalence_explicit(self):
        d=lhr();d['finalDisplayedUrl']=URL+'/';r=self.parse(d,{**CTX,'expected_final_url':URL+'/','final_url_basis':'verified slash redirect'});self.assertTrue(r['valid_measurement'])
    def test_document_404_invalid(self):
        d=lhr();d['audits']['network-requests']={'details':{'items':[{'url':URL,'resourceType':'Document','statusCode':404}]}};self.assertFalse(self.parse(d)['valid_measurement'])
    def test_environment_changes_separate_fingerprint(self):
        d=lhr();d['configSettings']['throttling']['cpuSlowdownMultiplier']=1;self.assertNotEqual(self.parse()['environment_key'],self.parse(d)['environment_key'])
    def test_tool_version_changes_separate_fingerprint(self):
        d=lhr();d['lighthouseVersion']='13.4.1';self.assertNotEqual(self.parse()['environment_key'],self.parse(d)['environment_key'])
    def test_psi_runner_not_lhci_baseline(self):self.assertNotEqual(self.parse()['environment_key'],self.parse(ctx={**CTX,'runner':'psi'})['environment_key'])
    def test_benchmark_variation_does_not_split_group(self):
        d=lhr();d['environment']['benchmarkIndex']=901;self.assertEqual(self.parse()['environment_key'],self.parse(d)['environment_key'])
    def test_unverified_host_not_comparable(self):
        c={**CTX};del c['host_id'];self.assertFalse(self.parse(ctx=c)['comparable'])
    def test_warnings_preserved(self):
        d=lhr();d['runWarnings']=['timeout while waiting'];self.assertEqual(self.parse(d)['warnings'],['timeout while waiting'])
    def test_old_final_url_schema_supported(self):
        d=lhr();d['finalUrl']=d.pop('finalDisplayedUrl');self.assertEqual(self.parse(d)['final_url'],URL)
