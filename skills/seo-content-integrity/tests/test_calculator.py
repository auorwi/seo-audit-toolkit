from copy import deepcopy
from support import IntegrityTest
from content_integrity.numbers import parse_quantity as n
from test_comparison import AT

def trial(quantity='10', direction='asset_to_quote', output='20.00'):
    return {'trial_id': quantity+'-'+direction, 'asset_id':'bitcoin', 'quote_unit':'EUR',
            'observed_at':AT, 'direction':direction, 'requested_input':n(quantity,exact=True),
            'actual_input':n(quantity,exact=True), 'output':n(output), 'rate':n('2.00'),
            'rate_basis':'quote_per_asset', 'input_unit':'bitcoin' if direction=='asset_to_quote' else 'EUR',
            'output_unit':'EUR' if direction=='asset_to_quote' else 'bitcoin',
            'interaction_status':'completed', 'readiness':'ready', 'rate_changed':False,
            'before_evidence_id':'before', 'after_evidence_id':'after', 'rate_evidence_id':'after'}

class CalculatorTests(IntegrityTest):
    def check(self, row=None):return self.module('calculator').check_trial(row or trial(),at=AT)
    def test_forward(self):self.assertEqual(self.check()['status'],'consistent')
    def test_reverse(self):self.assertEqual(self.check(trial('10','quote_to_asset','5.00'))['status'],'consistent')
    def test_arithmetic_error(self):self.assertEqual(self.check(trial(output='10.00'))['status'],'calculation_conflict')
    def test_actual_input_not_applied(self):
        r=trial();r['actual_input']=n('1',exact=True);self.assertEqual(self.check(r)['status'],'interaction_not_applied')
    def test_failed_interaction_not_website_bug(self):
        r=trial();r['interaction_status']='timeout';self.assertEqual(self.check(r)['status'],'insufficient_data')
    def test_loading_not_zero_error(self):
        r=trial(output='0');r['readiness']='loading';self.assertEqual(self.check(r)['status'],'insufficient_data')
    def test_missing_rate(self):
        r=trial();r['rate']=n('--');self.assertEqual(self.check(r)['status'],'insufficient_data')
    def test_rate_changes_inconclusive(self):
        r=trial();r['rate_changed']=True;self.assertEqual(self.check(r)['status'],'insufficient_data')
    def test_missing_rate_stability(self):
        r=trial();del r['rate_changed'];self.assertEqual(self.check(r)['status'],'insufficient_data')
    def test_wrong_output_unit(self):
        r=trial();r['output_unit']='USD';self.assertEqual(self.check(r)['status'],'unit_conflict')
    def test_missing_unit_not_guess(self):
        r=trial();r['output_unit']=None;self.assertEqual(self.check(r)['status'],'insufficient_data')
    def test_zero_rate_not_division(self):
        r=trial('10','quote_to_asset','0');r['rate']=n('0');self.assertEqual(self.check(r)['status'],'insufficient_data')
    def test_stale_capture(self):
        r=trial();r['observed_at']='2025-01-01T00:00:00Z';self.assertEqual(self.check(r)['status'],'insufficient_data')
    def test_missing_before_evidence(self):
        r=trial();r.pop('before_evidence_id');self.assertEqual(self.check(r)['status'],'insufficient_data')
    def test_same_before_after_evidence(self):
        r=trial();r['after_evidence_id']='before';self.assertEqual(self.check(r)['status'],'insufficient_data')
    def test_small_value_shown_zero(self):
        r=trial('10',output='0.00');r['rate']=n('0.0000000123',exact=True);self.assertEqual(self.check(r)['status'],'precision_loss')
    def test_rounding_allowed(self):
        r=trial('3',output='3.70');r['rate']=n('1.234',exact=True);self.assertEqual(self.check(r)['status'],'consistent_with_display_precision')
    def test_no_claim_market_accuracy(self):self.assertFalse(self.check()['market_rate_accuracy_verified'])
    def test_negative_quantity_not_supported(self):self.assertEqual(self.check(trial('-1',output='-2'))['status'],'insufficient_data')
    def test_invalid_direction(self):
        r=trial();r['direction']='trade';self.assertEqual(self.check(r)['status'],'insufficient_data')
    def test_coverage_requires_six_distinct_trials(self):
        mod=self.module('calculator');r=mod.check_suite([trial()],at=AT)
        self.assertFalse(r['coverage_complete']);self.assertEqual(len(r['missing_cases']),5)
    def test_all_six_cases(self):
        rows=[trial(q,d,str(int(q)*2 if d=='asset_to_quote' else int(q)/2)) for q in ['1','10','1000'] for d in ['asset_to_quote','quote_to_asset']]
        r=self.module('calculator').check_suite(rows,at=AT);self.assertTrue(r['coverage_complete']);self.assertEqual(r['missing_cases'],[])
    def test_duplicate_trials_not_coverage(self):
        r=self.module('calculator').check_suite([trial()]*6,at=AT);self.assertFalse(r['coverage_complete'])
    def test_foreign_asset_cannot_fill_suite(self):
        r=trial();other=deepcopy(r);other['asset_id']='ethereum'
        self.assertEqual(self.module('calculator').check_suite([r,other],at=AT)['status'],'mixed_context')
    def test_interactions_completed_but_invalid_rate_keeps_math_gap(self):
        rows=[trial(q,d,'0') for q in ['1','10','1000'] for d in ['asset_to_quote','quote_to_asset']]
        for row in rows:row['rate']=n('0')
        r=self.module('calculator').check_suite(rows,at=AT);self.assertTrue(r['interaction_coverage_complete']);self.assertFalse(r['coverage_complete']);self.assertEqual(r['completed_interactions'],6)
    def test_failed_trial_not_completed_interaction(self):
        row=trial();row['interaction_status']='failed';r=self.module('calculator').check_suite([row],at=AT);self.assertEqual(r['completed_interactions'],0)
