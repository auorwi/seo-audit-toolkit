import copy
from support import IntegrityTest
from content_integrity.numbers import parse_quantity
AT='2026-09-17T05:00:00Z'
def observation(value='100.00',**kw):return {'asset_id':'bitcoin','concept':'price','unit':'USD','basis':'spot_last_trade','period':'current','scenario':'default','temporal_kind':'live','observed_at':AT,'data_at':AT,'number':parse_quantity(value),**kw}

class ComparisonTests(IntegrityTest):
    def check(self,a=None,b=None,**kw):return self.module('comparison').check_pair(a or observation(),b or observation(),at=AT,**kw)
    def test_equal_values_consistent(self):self.assertEqual(self.check()['status'],'consistent')
    def test_same_concept_clear_conflict(self):self.assertEqual(self.check(b=observation('150.00'))['status'],'conflict')
    def test_rounded_supply_can_match_precise_text(self):
        a=observation('62.8B',concept='circulating_supply',unit='XRP',asset_id='ripple');b=observation('62,845,000,000',concept='circulating_supply',unit='XRP',asset_id='ripple');self.assertEqual(self.check(a,b)['status'],'consistent_with_display_precision')
    def test_circulating_and_total_are_different_concepts(self):self.assertEqual(self.check(observation('62.8B',concept='circulating_supply'),observation('99.9B',concept='total_supply'))['status'],'incomparable')
    def test_currency_not_implicitly_converted(self):self.assertEqual(self.check(b=observation(unit='USDT'))['status'],'incomparable')
    def test_different_asset_not_comparable(self):self.assertEqual(self.check(b=observation(asset_id='ethereum'))['status'],'incomparable')
    def test_spot_not_mark_price(self):self.assertEqual(self.check(b=observation(basis='perpetual_mark_price'))['status'],'incomparable')
    def test_missing_semantic_basis_unknown(self):self.assertEqual(self.check(b=observation(basis=None))['status'],'incomparable')
    def test_different_period_not_compared(self):self.assertEqual(self.check(b=observation(period='24h_high'))['status'],'incomparable')
    def test_different_forecast_scenario_not_compared(self):self.assertEqual(self.check(b=observation(scenario='growth_5pct'))['status'],'incomparable')
    def test_missing_value_not_zero(self):self.assertEqual(self.check(b=observation('--'))['status'],'insufficient_data')
    def test_unsynchronized_live_quotes_not_declared_conflict(self):self.assertEqual(self.check(b=observation('120',data_at='2026-09-17T04:55:00Z'))['status'],'incomparable')
    def test_missing_data_time_not_capture_time(self):self.assertEqual(self.check(b=observation(data_at=None))['status'],'incomparable')
    def test_stale_capture_not_current(self):self.assertEqual(self.check(b=observation(observed_at='2020-01-01T00:00:00Z'))['status'],'insufficient_data')
    def test_future_capture_not_current(self):self.assertEqual(self.check(b=observation(observed_at='2027-01-01T00:00:00Z'))['status'],'insufficient_data')
    def test_static_content_uses_capture_and_same_scenario(self):self.assertEqual(self.check(observation(temporal_kind='static',data_at=None),observation(temporal_kind='static',data_at=None))['status'],'consistent')
    def test_explicit_tolerance_is_recorded(self):
        r=self.check(b=observation('100.10'),relative_tolerance='0.002');self.assertEqual(r['status'],'within_configured_tolerance');self.assertEqual(r['relative_tolerance'],'0.002')
    def test_negative_tolerance_rejected(self):
        with self.assertRaises(ValueError):self.check(relative_tolerance='-1')
    def test_tiny_positive_hidden_by_display_zero_is_precision_issue(self):
        a=observation('0.00');b=observation(number=parse_quantity('0.000000000123',exact=True));r=self.check(a,b);self.assertEqual(r['status'],'precision_loss');self.assertNotEqual(r['difference'],'0')
    def test_true_zero_not_underflow_by_guess(self):self.assertEqual(self.check(observation('0.00'),observation('0.00'))['status'],'consistent')
    def test_compact_supply_may_be_truncated_not_rounded(self):
        self.assertEqual(self.check(observation('965.7M'),observation('965,765,530.99'))['status'],'possible_truncation')
