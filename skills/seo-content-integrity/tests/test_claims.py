from support import IntegrityTest
from content_integrity.numbers import parse_quantity as n
from test_comparison import AT

def claim(kind='direction', **kw):
    return {'kind':kind,'observed_at':AT,'asset_id':'bitcoin','market':'spot',
            'reviewed':True,'direction':'increase','change':n('-2.50'), 'change_kind':'signed_percent',**kw}

class ClaimTests(IntegrityTest):
    def check(self,row=None):return self.module('claims').check_claim(row or claim(),at=AT)
    def test_increased_negative(self):self.assertEqual(self.check()['status'],'direction_conflict')
    def test_decreased_positive_signed(self):self.assertEqual(self.check(claim(direction='decrease',change=n('2')))['status'],'direction_conflict')
    def test_decreased_positive_magnitude_is_valid(self):self.assertEqual(self.check(claim(direction='decrease',change=n('2'),change_kind='magnitude'))['status'],'consistent')
    def test_zero_change_no_direction_conflict(self):self.assertEqual(self.check(claim(change=n('0')))['status'],'consistent')
    def test_unknown_signed_semantics(self):self.assertEqual(self.check(claim(change_kind='unknown'))['status'],'insufficient_data')
    def test_unreviewed_direction_word(self):self.assertEqual(self.check(claim(reviewed=False))['status'],'insufficient_data')
    def test_missing_number(self):self.assertEqual(self.check(claim(change=n('--')))['status'],'insufficient_data')
    def test_outdated_capture(self):self.assertEqual(self.check(claim(observed_at='2025-01-01T00:00:00Z'))['status'],'insufficient_data')
    def test_placeholder_empty_expected_country(self):self.assertEqual(self.check(claim('template_field',field='country',value='',required=True))['status'],'empty_template_field')
    def test_optional_empty_field(self):self.assertEqual(self.check(claim('template_field',field='country',value='',required=False))['status'],'not_applicable')
    def test_missing_field_capture_not_empty(self):self.assertEqual(self.check(claim('template_field',field='country',value=None,required=True))['status'],'insufficient_data')
    def test_unexpanded_placeholder(self):self.assertEqual(self.check(claim('template_field',field='asset',value='{{coinName}}',required=True,unexpanded=True))['status'],'unexpanded_placeholder')
    def test_known_country_valid(self):self.assertEqual(self.check(claim('template_field',field='country',value='Japan',required=True))['status'],'consistent')
    def test_live_label_with_old_date(self):self.assertEqual(self.check(claim('freshness',live_claim=True,data_at='2025-10-13T00:00:00Z'))['status'],'stale_data_live_claim')
    def test_live_label_without_data_time_is_unknown(self):self.assertEqual(self.check(claim('freshness',live_claim=True,data_at=None))['status'],'insufficient_data')
    def test_old_historical_table_not_live_bug(self):self.assertEqual(self.check(claim('freshness',live_claim=False,data_at='2025-10-13T00:00:00Z'))['status'],'not_applicable')
    def test_cta_not_verified_listing(self):self.assertEqual(self.check(claim('lifecycle',page_state='buy_cta',reference_state='unlisted',reference_scope='same_page'))['status'],'potential_copy_conflict')
    def test_ended_still_claims_active_same_product(self):self.assertEqual(self.check(claim('lifecycle',page_state='active',reference_state='ended',reference_scope='same_page'))['status'],'lifecycle_conflict')
    def test_api_error_not_unlisted(self):self.assertEqual(self.check(claim('lifecycle',page_state='active',reference_state='unknown',reference_scope='official_api',reference_status='error'))['status'],'insufficient_data')
    def test_wrong_market_not_same_state(self):self.assertEqual(self.check(claim('lifecycle',page_state='active',reference_state='unlisted',reference_scope='official_api',reference_status='ok',reference_market='futures',reference_asset_id='bitcoin',reference_at=AT))['status'],'incomparable')
    def test_official_same_market_state(self):self.assertEqual(self.check(claim('lifecycle',page_state='active',reference_state='inactive',reference_scope='official_api',reference_status='ok',reference_market='spot',reference_asset_id='bitcoin',reference_at=AT))['status'],'lifecycle_conflict')
    def test_absent_symbol_is_not_explicit_offline(self):self.assertEqual(self.check(claim('lifecycle',page_state='active',reference_state='absent',reference_scope='official_api',reference_status='ok',reference_market='spot',reference_asset_id='bitcoin',reference_at=AT))['status'],'insufficient_data')
    def test_same_page_different_products_not_false_conflict(self):self.assertEqual(self.check(claim('lifecycle',page_state='active',reference_state='unlisted',reference_scope='same_page',market='chainspot',reference_market='spot'))['status'],'incomparable')
