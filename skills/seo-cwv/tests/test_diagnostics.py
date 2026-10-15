from support import CWVTest,URL
class DiagnosticTests(CWVTest):
    def parse(self,audits,**kw):return self.module('diagnostics').diagnose_lhr({'requestedUrl':URL,'audits':audits,**kw})
    def test_resource_specific_savings(self):
        r=self.parse({'unused-javascript':{'title':'Reduce unused JavaScript','details':{'overallSavingsMs':500,'overallSavingsBytes':10000,'items':[{'url':'https://bingx.com/a.js','wastedBytes':10000}]}}});self.assertEqual(r['opportunities'][0]['resources'][0]['url'],'https://bingx.com/a.js')
    def test_zero_estimate_not_action(self):self.assertEqual(self.parse({'render-blocking-resources':{'details':{'overallSavingsMs':0,'overallSavingsBytes':0}}})['opportunities'],[])
    def test_tbt_numeric_value_not_savings(self):self.assertEqual(self.parse({'total-blocking-time':{'numericValue':900}})['opportunities'],[])
    def test_error_audit_not_opportunity(self):self.assertEqual(self.parse({'unused-javascript':{'scoreDisplayMode':'error','details':{'overallSavingsMs':500}}})['opportunities'],[])
    def test_positive_bytes_without_ms_kept(self):self.assertEqual(len(self.parse({'uses-optimized-images':{'details':{'overallSavingsBytes':9000}}})['opportunities']),1)
    def test_metric_savings_new_schema(self):self.assertEqual(self.parse({'render-blocking-insight':{'metricSavings':{'LCP':400,'FCP':200},'details':{'items':[]}}})['opportunities'][0]['metric_savings']['LCP'],400)
    def test_overlapping_savings_not_summed(self):
        r=self.parse({'a':{'details':{'overallSavingsMs':400}},'b':{'details':{'overallSavingsMs':500}}});self.assertIsNone(r['total_savings_ms'])
    def test_lcp_node_preserved_without_estimated_savings(self):
        r=self.parse({'largest-contentful-paint-element':{'details':{'items':[{'items':[{'node':{'type':'node','selector':'main h1','snippet':'<h1>Bitcoin</h1>'}}]}]}}});self.assertEqual(r['elements'][0]['selector'],'main h1');self.assertEqual(r['opportunities'],[])
    def test_layout_shift_node_has_audit_source(self):
        r=self.parse({'layout-shifts':{'details':{'items':[{'node':{'type':'node','selector':'#banner'},'score':0.2}]}}});self.assertEqual(r['elements'][0]['audit_id'],'layout-shifts')
    def test_long_task_details_not_inp(self):
        r=self.parse({'long-tasks':{'details':{'items':[{'url':'https://bingx.com/a.js','duration':800,'startTime':1500}]}}});self.assertEqual(r['long_tasks'][0]['duration'],800);self.assertNotIn('INP',r)
    def test_runtime_error_keeps_gap(self):
        r=self.parse({},runtimeError={'code':'NO_FCP'});self.assertEqual(r['opportunities'],[]);self.assertTrue(r['gaps'])
    def test_missing_details_not_silently_root_caused(self):self.assertTrue(self.parse({})['gaps'])
