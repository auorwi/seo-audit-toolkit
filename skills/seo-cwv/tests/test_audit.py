from support import CWVTest,AT,URL
from test_series import run
def inputs(**kw):return {'lab_runs':[],'field_records':[],'expected_cells':[],'gaps':[],**kw}
def field(**kw):return {'source':'crux_api','status':'observed','scope':'url','key':URL,'device':'PHONE','observed_at':AT,'collection_period':{'first_date':'2026-08-19','last_date':'2026-09-15','days':28},'metrics':{'LCP':2000,'CLS':0.05,'INP':100},'gaps':[],**kw}
class AuditTests(CWVTest):
    def audit(self,data,**kw):return self.module('audit').audit(data,at=AT,**kw)
    def test_full_grid_missing_cells_listed(self):
        r=self.audit(inputs(expected_cells=[{'url':URL,'device':'mobile'}]));self.assertFalse(r['coverage']['laboratory_scope_complete']);self.assertEqual(r['coverage']['missing_cells'][0]['url'],URL)
    def test_three_consistent_runs_complete_cell(self):
        r=self.audit(inputs(lab_runs=[run(i) for i in range(3)],expected_cells=[{'url':URL,'device':'mobile'}]));self.assertTrue(r['coverage']['laboratory_scope_complete'])
    def test_mixed_environment_not_three_valid(self):
        r=self.audit(inputs(lab_runs=[run(1),run(2),run(3,environment_key='different')],expected_cells=[{'url':URL,'device':'mobile'}]));self.assertFalse(r['coverage']['laboratory_scope_complete'])
    def test_lab_not_field_pass(self):
        r=self.audit(inputs(lab_runs=[run(i,1000) for i in range(3)]));self.assertEqual(r['field_assessments'],[]);self.assertFalse(r['coverage']['field_scope_complete'])
    def test_field_url_pass_with_window(self):self.assertEqual(self.audit(inputs(field_records=[field()]))['field_assessments'][0]['current_assessment'],'pass')
    def test_origin_cannot_cover_requested_url(self):
        r=self.audit(inputs(field_records=[field(scope='origin',key='https://bingx.com')],expected_cells=[{'url':URL,'device':'mobile'}]));self.assertFalse(r['coverage']['field_scope_complete'])
    def test_missing_window_not_current_pass(self):self.assertEqual(self.audit(inputs(field_records=[field(collection_period=None)]))['field_assessments'][0]['current_assessment'],'unknown')
    def test_stale_lab_not_current(self):
        r=self.audit(inputs(lab_runs=[run(i,fetched_at='2020-01-01T00:00:00Z') for i in range(3)]));self.assertEqual(r['laboratory']['groups'],[])
    def test_new_field_error_does_not_resurrect_old_good(self):
        old=field(observed_at='2026-09-17T04:00:00Z');new=field(status='api_error',metrics={});r=self.audit(inputs(field_records=[old,new]));self.assertEqual(r['field_assessments'][0]['current_assessment'],'unknown')
    def test_stable_metric_issue_id(self):
        a=self.audit(inputs(lab_runs=[run(i,5000) for i in range(3)]));b=self.audit(inputs(lab_runs=[run(i+3,6000) for i in range(3)]));self.assertEqual([f['issue_id'] for f in a['findings']],[f['issue_id'] for f in b['findings']])
    def test_invalid_freshness_rejected(self):
        with self.assertRaises(ValueError):self.audit(inputs(),max_age_hours=0)
    def test_empty_scope_not_global_success(self):self.assertFalse(self.audit(inputs())['coverage']['laboratory_scope_complete'])
    def test_future_field_window_not_current_pass(self):
        r=self.audit(inputs(field_records=[field(collection_period={'first_date':'2026-09-19','last_date':'2026-10-16','days':28})]));self.assertEqual(r['field_assessments'][0]['current_assessment'],'unknown')
    def test_nonstandard_crux_window_not_same_baseline(self):
        r=self.audit(inputs(field_records=[field(collection_period={'first_date':'2026-09-13','last_date':'2026-09-15','days':3})]));self.assertEqual(r['field_assessments'][0]['current_assessment'],'unknown')
    def test_unreviewed_metrics_not_complete_business_scope(self):
        r=self.audit(inputs(lab_runs=[run(i) for i in range(3)],expected_cells=[{'url':URL,'device':'mobile'}]));self.assertIn('business_page_scope_complete',r['coverage']);self.assertFalse(r['coverage']['business_page_scope_complete'])
    def test_all_run_screenshots_reviewed_complete_business_scope(self):
        rows=[run(i,page_content_validity='reviewed_valid',page_review={'reviewed_at':AT}) for i in range(3)]
        r=self.audit(inputs(lab_runs=rows,expected_cells=[{'url':URL,'device':'mobile'}]));self.assertTrue(r['coverage'].get('business_page_scope_complete'))
    def test_future_business_review_not_current_confirmation(self):
        rows=[run(i,page_content_validity='reviewed_valid',page_review={'reviewed_at':'2026-10-01T00:00:00Z'}) for i in range(3)]
        r=self.audit(inputs(lab_runs=rows,expected_cells=[{'url':URL,'device':'mobile'}]));self.assertIn('business_page_scope_complete',r['coverage']);self.assertFalse(r['coverage']['business_page_scope_complete'])
    def test_wrong_page_has_stable_actionable_finding(self):
        row=run(1,valid_measurement=False,page_content_validity='reviewed_invalid',page_review={'reviewed_at':AT,'visible_evidence':'Log In; no market list','reason':'Wrong measured business state'},exclusion='business_page_invalid')
        r=self.audit(inputs(lab_runs=[row]));self.assertIn('business_page_mismatch',[f['rule'] for f in r['findings']])
    def test_future_invalid_review_cannot_exclude_historical_measurement(self):
        from test_page_reviews import measured,raw,review
        row=self.module('reviews').apply_review(measured(),raw(),review(status='invalid',reviewed_at='2026-10-01T00:00:00Z'))
        r=self.audit(inputs(lab_runs=[row]));self.assertEqual(r['coverage']['valid_lab_runs'],1);self.assertNotIn('business_page_mismatch',[f['rule'] for f in r['findings']])
    def test_old_wrong_page_not_new_current_finding(self):
        row=run(1,valid_measurement=False,fetched_at='2020-01-01T00:00:00Z',page_content_validity='reviewed_invalid',page_review={'reviewed_at':AT})
        r=self.audit(inputs(lab_runs=[row]));self.assertNotIn('business_page_mismatch',[f['rule'] for f in r['findings']])
    def test_high_host_load_is_not_reliable_lab_coverage(self):
        rows=[run(i,5000,environment_quality={'status':'high_host_load','suitable_for_regression':False}) for i in range(3)]
        r=self.audit(inputs(lab_runs=rows,expected_cells=[{'url':URL,'device':'mobile'}]));self.assertIn('reliable_lab_scope_complete',r['coverage']);self.assertFalse(r['coverage']['reliable_lab_scope_complete']);self.assertIn('host_environment_not_suitable_for_regression',[g['reason'] for g in r['gaps']])
