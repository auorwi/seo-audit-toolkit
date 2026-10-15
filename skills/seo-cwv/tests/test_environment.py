from support import CWVTest
from test_series import run

class EnvironmentTests(CWVTest):
    def assess(self,before=(1,1,1),after=(1,1,1),cpus=10,**kw):return self.module('environment').assess_load(before,after,cpus,**kw)
    def test_normal_load_not_quiet_machine_certificate(self):
        r=self.assess();self.assertEqual(r['status'],'no_high_load_detected');self.assertFalse(r['quiet_machine_proven'])
    def test_actual_observed_extreme_load_flagged(self):
        r=self.assess((292,295,308),(224,258,288));self.assertEqual(r['status'],'high_host_load');self.assertFalse(r['suitable_for_regression']);self.assertAlmostEqual(r['max_load_per_cpu'],29.2)
    def test_high_after_is_not_ignored(self):self.assertEqual(self.assess(after=(30,1,1))['status'],'high_host_load')
    def test_missing_cpu_unknown(self):self.assertEqual(self.assess(cpus=None)['status'],'environment_data_missing')
    def test_missing_load_unknown(self):self.assertEqual(self.assess(before=None)['status'],'environment_data_missing')
    def test_nonfinite_or_negative_unknown(self):
        for value in [float('nan'),float('inf'),-1,True]:self.assertEqual(self.assess(before=(value,1,1))['status'],'environment_data_missing')
    def test_engineering_threshold_must_be_positive(self):
        with self.assertRaises(ValueError):self.assess(max_load_per_cpu=0)
    def test_baseline_comparison_blocked_by_busy_host(self):
        m=self.module('series');old=m.summarize_lab([run(i) for i in range(3)]);new=m.summarize_lab([run(i+3,8000,environment_quality={'status':'high_host_load','suitable_for_regression':False}) for i in range(3)])
        r=m.compare_lab(old,new);self.assertEqual(r['comparisons'],[]);self.assertIn('host_environment_not_suitable_for_regression',[g['reason'] for g in r['gaps']])
    def test_missing_quality_cannot_be_clean_baseline(self):
        m=self.module('series');rows=[run(i) for i in range(3)]
        for r in rows:r.pop('environment_quality',None)
        g=m.summarize_lab(rows)['groups'][0];self.assertFalse(g.get('suitable_for_regression',True))
