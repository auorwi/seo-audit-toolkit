import tempfile,copy
from support import IntegrityTest
from test_adapters import ManifestFixture
from test_comparison import AT,observation

class AuditTests(IntegrityTest):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.f=ManifestFixture(self.tmp.name)
    def run_audit(self,inputs=None):
        mod=self.module('audit');inputs=inputs if inputs is not None else self.module('adapters').load_manifest(self.f.write(),at=AT)
        return mod.audit(inputs,at=AT)
    def test_confirmed_difference_has_evidence(self):
        r=self.run_audit();self.assertEqual(len(r['findings']),1);self.assertEqual(r['findings'][0]['classification'],'evidence_supported_conflict');self.assertTrue(r['findings'][0]['evidence'])
    def test_stable_identity_not_value_hash(self):
        a=self.run_audit()['findings'][0]['issue_id'];self.f.capture['fields']['body']['text']='120.00';self.f.check['citations'][1]['quote']='120.00';self.f.check['payload']['right']=observation('120.00')
        self.assertEqual(a,self.run_audit()['findings'][0]['issue_id'])
    def test_insufficient_data_is_gap(self):
        self.f.check['payload']['right']['data_at']=None;r=self.run_audit();self.assertEqual(r['findings'],[]);self.assertTrue(r['gaps'])
    def test_matching_result_not_finding(self):
        self.f.check['payload']['right']=observation('100.00');r=self.run_audit();self.assertEqual(r['findings'],[])
    def test_fullsite_never_claimed(self):self.assertFalse(self.run_audit()['coverage']['full_site_proven'])
    def test_scoped_check_complete(self):self.assertTrue(self.run_audit()['coverage']['declared_checks_complete'])
    def test_missing_kind_visible(self):
        self.f.manifest['scope'][0]['kinds'].append('forecast');r=self.run_audit();self.assertFalse(r['coverage']['declared_checks_complete']);self.assertTrue(any(g['reason']=='scoped_check_not_performed' for g in r['gaps']))
    def test_no_reviews_not_healthy(self):
        inputs=self.module('adapters').load_manifest(self.f.write(),at=AT);inputs['checks']=[];r=self.run_audit(inputs);self.assertFalse(r['coverage']['declared_checks_complete'])
    def test_extra_url_scope_preserved(self):
        self.f.manifest['scope'].append({'url':'https://bingx.com/en/price/ripple','kinds':['pair']});self.assertFalse(self.run_audit()['coverage']['declared_checks_complete'])
    def test_recommendation_and_retest(self):
        f=self.run_audit()['findings'][0];self.assertTrue(f['recommendation']);self.assertTrue(f['retest']);self.assertEqual(f['owner_skill'],'012')
    def test_ledger_replay_idempotent(self):
        self.module('audit');from crawlability.ledger import record,history
        from pathlib import Path
        db=Path(self.tmp.name)/'state.sqlite';r=self.run_audit();record(db,r);record(db,r);self.assertEqual(history(db)[0]['sightings'],1)
    def test_absence_does_not_close(self):
        self.module('audit');from crawlability.ledger import record,history
        from pathlib import Path
        db=Path(self.tmp.name)/'state.sqlite';r=self.run_audit();record(db,r);record(db,{**r,'findings':[]});self.assertEqual(history(db)[0]['status'],'open')
    def test_tampered_proof_keeps_scope_gap(self):self.f.capture['html']='changed';self.assertFalse(self.run_audit()['coverage']['declared_checks_complete'])
    def test_empty_scope_not_complete(self):
        inputs={'scope':[],'captures':{},'checks':[],'actions':{},'gaps':[]};self.assertFalse(self.run_audit(inputs)['coverage']['declared_checks_complete'])
    def test_candidate_becoming_confirmed_keeps_issue_identity(self):
        from test_forecast import point
        inputs=self.module('adapters').load_manifest(self.f.write(),at=AT);c=inputs['checks'][0];c['kind']='forecast';c['payload']={'table':[point(2030,'105')],'summary':point(2031,'105')}
        before=self.run_audit(inputs)['findings'];self.assertEqual(len(before),1);first=before[0]
        c['payload']['table'].append(point(2031,'106.05'));after=self.run_audit(inputs)['findings'];self.assertEqual(len(after),1);second=after[0]
        self.assertEqual(first['issue_id'],second['issue_id']);self.assertNotEqual(first['classification'],second['classification'])
    def test_same_forecast_year_issue_across_scenarios_one_issue(self):
        from test_forecast import point
        inputs=self.module('adapters').load_manifest(self.f.write(),at=AT);c=inputs['checks'][0];c['kind']='forecast';c['payload']={'table':[point(2031,'110')],'summary':point(2031,'100')}
        other=copy.deepcopy(c);other['check_id']='second-growth-scenario';other['payload']['table'][0]['scenario']='growth_2pct';other['payload']['summary']['scenario']='growth_2pct';inputs['checks'].append(other)
        r=self.run_audit(inputs);self.assertEqual(len(r['findings']),1);self.assertEqual(len(r['findings'][0]['evidence']),2)
    def test_confirmed_scenario_upgrades_grouped_candidate(self):
        from test_forecast import point
        inputs=self.module('adapters').load_manifest(self.f.write(),at=AT);c=inputs['checks'][0];c['kind']='forecast';c['payload']={'table':[point(2030,'105')],'summary':point(2031,'105')}
        other=copy.deepcopy(c);other['check_id']='other-scenario';other['payload']['table'].append(point(2031,'106.05'));inputs['checks'].append(other)
        r=self.run_audit(inputs);self.assertEqual(len(r['findings']),1);self.assertEqual(r['findings'][0]['classification'],'evidence_supported_conflict');self.assertEqual(r['findings'][0]['rule'],'year_value_conflict')
