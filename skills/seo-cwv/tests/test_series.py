from support import CWVTest,URL,AT
def run(i,lcp=3000,**kw):return {'run_id':str(i),'source':'lighthouse','requested_url':URL,'final_url':URL,'device':'mobile','environment_key':'env1','environment_quality':{'status':'no_high_load_detected','suitable_for_regression':True,'basis':'synthetic controlled unit fixture'},'valid_measurement':True,'comparable':True,'fetched_at':AT,'metrics':{'LCP':lcp,'CLS':0.12,'TBT':500,'FCP':1000,'INP':None},**kw}
class SeriesTests(CWVTest):
    def summarize(self,rs):return self.module('series').summarize_lab(rs)
    def compare(self,a,b):return self.module('series').compare_lab(a,b,relative_budget=0.1,absolute_budgets={'LCP':300,'CLS':0.02,'TBT':100})
    def test_three_valid_median(self):
        r=self.summarize([run(1,1000),run(2,3000),run(3,9000)])['groups'][0];self.assertEqual(r['metrics']['LCP']['median'],3000);self.assertTrue(r['sufficient'])
    def test_two_samples_insufficient(self):self.assertFalse(self.summarize([run(1),run(2)])['groups'][0]['sufficient'])
    def test_all_successes_not_best_three(self):self.assertEqual(self.summarize([run(1,1000),run(2,2000),run(3,8000),run(4,9000)])['groups'][0]['metrics']['LCP']['median'],5000)
    def test_failed_preserved_excluded(self):
        r=self.summarize([run(1,valid_measurement=False),run(2),run(3)]);self.assertFalse(r['groups'][0]['sufficient']);self.assertEqual(len(r['excluded']),1)
    def test_duplicate_run_not_new_sample(self):self.assertEqual(self.summarize([run(1),run(1),run(2)])['groups'][0]['n'],2)
    def test_same_evidence_not_counted_twice(self):self.assertEqual(self.summarize([run(1,evidence={'sha256':'a'*64}),run(2,evidence={'sha256':'a'*64})])['groups'][0]['n'],1)
    def test_devices_never_merged(self):self.assertEqual(len(self.summarize([run(1),run(2,device='desktop')])['groups']),2)
    def test_environments_never_merged(self):self.assertEqual(len(self.summarize([run(1),run(2,environment_key='env2')])['groups']),2)
    def test_uncomparable_not_baseline(self):self.assertEqual(self.summarize([run(1,comparable=False)])['groups'],[])
    def test_no_inp_invented(self):self.assertIsNone(self.summarize([run(1),run(2),run(3)])['groups'][0]['metrics']['INP']['median'])
    def test_regression_matching_environment(self):
        a=self.summarize([run(i,2000) for i in range(3)]);b=self.summarize([run(i+3,3000) for i in range(3)]);r=self.compare(a,b);self.assertEqual(r['comparisons'][0]['metrics']['LCP']['status'],'regressed')
    def test_changed_environment_not_regression(self):
        a=self.summarize([run(i,2000) for i in range(3)]);b=self.summarize([run(i+3,6000,environment_key='env2') for i in range(3)]);self.assertEqual(self.compare(a,b)['comparisons'],[])
    def test_small_noise_below_absolute_budget(self):
        a=self.summarize([run(i,1000) for i in range(3)]);b=self.summarize([run(i+3,1150) for i in range(3)]);self.assertEqual(self.compare(a,b)['comparisons'][0]['metrics']['LCP']['status'],'within_budget')
    def test_insufficient_baseline_not_comparison(self):self.assertEqual(self.compare(self.summarize([run(1)]),self.summarize([run(2),run(3),run(4)]))['comparisons'],[])
    def test_zero_baseline_no_division_failure(self):
        a=self.summarize([run(i,0) for i in range(3)]);b=self.summarize([run(i+3,600) for i in range(3)]);self.assertEqual(self.compare(a,b)['comparisons'][0]['metrics']['LCP']['status'],'regressed')
    def test_scope_url_not_merged(self):self.assertEqual(len(self.summarize([run(1),run(2,requested_url='https://bingx.com/en/')])['groups']),2)
