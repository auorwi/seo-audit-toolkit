from support import IntegrityTest
from content_integrity.numbers import parse_quantity
from test_comparison import observation,AT
def point(year,value,**kw):return {'year':year,**observation(value,concept='forecast_price',basis='declared_projection',period=str(year),scenario='growth_1pct',temporal_kind='static',data_at=None,**kw)}
class ForecastTests(IntegrityTest):
    def check(self,table=None,summary=None):return self.module('forecast').check_summary(table or [point(2030,'105.00'),point(2031,'106.05')],summary or point(2031,'106.05'),at=AT)
    def test_year_and_value_match(self):self.assertEqual(self.check()['status'],'consistent')
    def test_summary_uses_wrong_year_value(self):
        r=self.check(summary=point(2031,'105.00'));self.assertEqual(r['status'],'year_value_conflict');self.assertEqual(r['matching_other_years'],[2030])
    def test_missing_year_is_candidate_shift_not_proven(self):
        r=self.check(table=[point(2030,'105.00')],summary=point(2031,'105.00'));self.assertEqual(r['status'],'possible_year_shift');self.assertFalse(r['confirmed'])
    def test_same_value_many_years_does_not_choose_one(self):
        r=self.check(table=[point(2029,'105.00'),point(2030,'105.00')],summary=point(2031,'105.00'));self.assertEqual(r['status'],'summary_year_not_covered');self.assertEqual(r['matching_other_years'],[2029,2030])
    def test_different_growth_scenario_not_conflict(self):
        p=point(2031,'105.00');p['scenario']='growth_5pct';self.assertEqual(self.check(summary=p)['status'],'incomparable')
    def test_duplicate_year_conflict_ambiguous_table(self):
        r=self.check(table=[point(2031,'100.00'),point(2031,'110.00')]);self.assertEqual(r['status'],'ambiguous_table')
    def test_missing_summary_year_not_invented(self):
        p=point(2031,'105.00');p['year']=None;self.assertEqual(self.check(summary=p)['status'],'insufficient_data')
    def test_missing_price_not_zero(self):self.assertEqual(self.check(summary=point(2031,'--'))['status'],'insufficient_data')
    def test_unrelated_asset_matching_number_not_shift_evidence(self):
        p=point(2030,'105.00');p['asset_id']='ethereum';r=self.check(table=[p],summary=point(2031,'105.00'));self.assertEqual(r['matching_other_years'],[])
    def test_forecast_year_not_treated_as_future_capture_time(self):self.assertEqual(self.check()['comparison']['left']['observed_at'],AT)
    def test_no_claim_prediction_will_happen(self):self.assertEqual(self.check()['scope'],'internal forecast table-summary consistency; not forecast accuracy')
