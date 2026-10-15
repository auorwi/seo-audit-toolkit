import tempfile,copy,json
from support import IntegrityTest
from test_adapters import ManifestFixture
from test_comparison import AT
from test_forecast import point
from test_calculator import trial
from content_integrity.numbers import parse_quantity as n

class EdgeCaseTests(IntegrityTest):
    def test_rounding_intervals_only_touch_not_definite_match(self):
        from test_comparison import observation
        r=self.module('comparison').check_pair(observation('100'),observation('101'),at=AT);self.assertEqual(r['status'],'display_rounding_boundary')
    def test_exact_flag_requires_boolean(self):
        with self.assertRaises(ValueError):self.module('numbers').parse_quantity('1.23',exact='false')
    def test_forecast_year_period_must_agree(self):
        s=point(2031,'105');s['period']='2030';r=self.module('forecast').check_summary([point(2031,'105')],s,at=AT);self.assertEqual(r['status'],'insufficient_data')
    def test_forecast_invalid_row_year_period_not_used(self):
        row=point(2030,'105');row['period']='2031';r=self.module('forecast').check_summary([row],point(2031,'105'),at=AT);self.assertEqual(r['matching_other_years'],[])
    def test_forecast_configured_freshness_used(self):
        r=self.module('forecast').check_summary([point(2031,'105')],point(2031,'105'),at='2026-09-19T05:00:00Z',max_age_hours=72);self.assertEqual(r['status'],'consistent')
    def test_calculator_asset_identity_distinct_from_display_unit(self):
        row=trial();row['asset_unit']='BTC';row['input_unit']='BTC';self.assertEqual(self.module('calculator').check_trial(row,at=AT)['status'],'consistent')
    def test_conflicting_duplicate_snapshot_poisoned(self):
        with tempfile.TemporaryDirectory() as tmp:
            f=ManifestFixture(tmp);path=f.write();other=copy.deepcopy(f.capture);other['fields']['card']['text']='999'
            m=json.loads(path.read_text());m['captures'].append(f.save('other.json',other));path.write_text(json.dumps(m))
            self.assertEqual(self.module('adapters').load_manifest(path,at=AT)['checks'],[])
    def test_observation_time_cannot_be_invented(self):
        with tempfile.TemporaryDirectory() as tmp:
            f=ManifestFixture(tmp);f.check['payload']['left']['observed_at']='2026-09-17T04:59:59Z'
            self.assertEqual(self.module('adapters').load_manifest(f.write(),at=AT)['checks'],[])
    def test_claim_reviewed_flag_requires_actual_review(self):
        with tempfile.TemporaryDirectory() as tmp:
            f=ManifestFixture(tmp);f.check.update(kind='claim',payload={'kind':'direction','observed_at':AT,'reviewed':False,'direction':'increase','change':n('100.00'),'change_kind':'signed_percent'})
            self.assertEqual(self.module('adapters').load_manifest(f.write(),at=AT)['checks'],[])
    def test_api_reference_without_actual_http_evidence_not_accepted(self):
        with tempfile.TemporaryDirectory() as tmp:
            f=ManifestFixture(tmp);f.check.update(kind='claim',payload={'kind':'lifecycle','observed_at':AT,'reviewed':True,'reference_scope':'official_api','reference_state':'inactive','page_state':'active'})
            self.assertEqual(self.module('adapters').load_manifest(f.write(),at=AT)['checks'],[])
