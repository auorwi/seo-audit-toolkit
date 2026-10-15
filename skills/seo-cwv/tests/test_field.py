from support import CWVTest,AT,URL
def crux():return {'record':{'key':{'url':URL,'formFactor':'PHONE'},'collectionPeriod':{'firstDate':{'year':2026,'month':8,'day':19},'lastDate':{'year':2026,'month':9,'day':15}},'metrics':{'largest_contentful_paint':{'percentiles':{'p75':2400}},'cumulative_layout_shift':{'percentiles':{'p75':'0.08'}},'interaction_to_next_paint':{'percentiles':{'p75':170}}}}}
def psi():return {'loadingExperience':{'id':URL,'metrics':{'LARGEST_CONTENTFUL_PAINT_MS':{'percentile':2400},'CUMULATIVE_LAYOUT_SHIFT_SCORE':{'percentile':8,'distributions':[{'min':0,'max':10},{'min':10,'max':25},{'min':25}]},'INTERACTION_TO_NEXT_PAINT':{'percentile':170}}},'originLoadingExperience':{'id':'https://bingx.com','metrics':{'LARGEST_CONTENTFUL_PAINT_MS':{'percentile':3100}}}}
class FieldTests(CWVTest):
    def crux(self,d=None,request=None):return self.module('field').parse_crux(d or crux(),request or {'url':URL,'formFactor':'PHONE'},observed_at=AT)
    def psi(self,d=None):return self.module('field').parse_psi(d or psi(),{'url':URL,'strategy':'mobile'},observed_at=AT)
    def test_crux_cls_decimal_string(self):self.assertEqual(self.crux()['metrics']['CLS'],0.08)
    def test_crux_keeps_p75(self):self.assertEqual(self.crux()['metrics']['LCP'],2400)
    def test_crux_phone(self):self.assertEqual(self.crux()['device'],'PHONE')
    def test_crux_window_preserved(self):self.assertEqual(self.crux()['collection_period']['last_date'],'2026-09-15')
    def test_origin_never_url_scope(self):
        d=crux();d['record']['key']={'origin':'https://bingx.com','formFactor':'PHONE'};r=self.crux(d,{'origin':'https://bingx.com','formFactor':'PHONE'});self.assertEqual(r['scope'],'origin')
    def test_wrong_device_not_current(self):
        d=crux();d['record']['key']['formFactor']='DESKTOP';self.assertEqual(self.crux(d)['status'],'unverified')
    def test_wrong_url_not_current(self):
        d=crux();d['record']['key']['url']='https://bingx.com/en/other';self.assertEqual(self.crux(d)['status'],'unverified')
    def test_normalized_url_with_evidence_allowed(self):
        d=crux();d['record']['key']['url']=URL+'/';d['urlNormalizationDetails']={'originalUrl':URL,'normalizedUrl':URL+'/'};self.assertEqual(self.crux(d)['status'],'observed')
    def test_absent_window_marked(self):
        d=crux();del d['record']['collectionPeriod'];self.assertIn('collection_period_missing',self.crux(d)['gaps'])
    def test_missing_inp_not_tbt(self):
        d=crux();del d['record']['metrics']['interaction_to_next_paint'];self.assertIsNone(self.crux(d)['metrics']['INP'])
    def test_bad_numeric_becomes_unknown(self):
        d=crux();d['record']['metrics']['largest_contentful_paint']['percentiles']['p75']='NaN';self.assertIsNone(self.crux(d)['metrics']['LCP'])
    def test_429_explicit_failure(self):self.assertEqual(self.crux({'error':{'code':429,'status':'RESOURCE_EXHAUSTED'}})['status'],'api_error')
    def test_404_no_data_not_site_404(self):self.assertEqual(self.crux({'error':{'code':404,'status':'NOT_FOUND'}})['status'],'no_data')
    def test_psi_origin_separate(self):self.assertEqual([r['scope'] for r in self.psi()['records']],['url','origin'])
    def test_psi_cls_scale_evidenced_by_bins(self):self.assertEqual(self.psi()['records'][0]['metrics']['CLS'],0.08)
    def test_psi_scale_unknown_not_assumed(self):
        d=psi();del d['loadingExperience']['metrics']['CUMULATIVE_LAYOUT_SHIFT_SCORE']['distributions'];self.assertIsNone(self.psi(d)['records'][0]['metrics']['CLS'])
    def test_psi_origin_fallback_not_url_good(self):
        d=psi();d['loadingExperience']={};r=self.psi(d);self.assertEqual([x['scope'] for x in r['records']],['origin']);self.assertIn('url_field_data_unavailable',r['gaps'])
    def test_psi_old_fid_not_inp(self):
        d=psi();del d['loadingExperience']['metrics']['INTERACTION_TO_NEXT_PAINT'];d['loadingExperience']['metrics']['FIRST_INPUT_DELAY_MS']={'percentile':10};self.assertIsNone(self.psi(d)['records'][0]['metrics']['INP'])
    def test_psi_window_not_invented(self):self.assertIsNone(self.psi()['records'][0]['collection_period']);self.assertIn('collection_period_missing',self.psi()['records'][0]['gaps'])
    def test_psi_error_not_good_score(self):self.assertEqual(self.psi({'error':{'code':429}})['status'],'api_error')
    def test_error_keeps_requested_scope_and_device(self):
        r=self.crux({'error':{'code':429}});self.assertIn('key',r);self.assertEqual(r['key'],URL);self.assertEqual(r['device'],'PHONE');self.assertEqual(r['scope'],'url')
