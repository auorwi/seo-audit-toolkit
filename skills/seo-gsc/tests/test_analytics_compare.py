"""Catch apples-to-oranges windows, missing rows as zero, and naive position averages."""
import unittest,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from gsc_audit.contracts import analytics
try:from gsc_audit.performance import compare
except ImportError:compare=None

def period(start,end,rows,**request):
    return analytics({'startDate':start,'endDate':end,'dimensions':['page'],**request},{'rows':rows,'responseAggregationType':'byPage'})
def row(url,clicks,imp,pos):return {'keys':[url],'clicks':clicks,'impressions':imp,'ctr':clicks/imp if imp else 0,'position':pos}
class Compare(unittest.TestCase):
    def setUp(self):self.assertIsNotNone(compare,'Comparison implementation missing')
    def periods(self):return period('2026-09-01','2026-09-07',[row('https://bingx.com/en/a',10,100,2),row('https://bingx.com/en/b',0,10,10)]),period('2026-09-08','2026-09-14',[row('https://bingx.com/en/a',5,50,4)])
    def test_matching_row_delta_only(self):
        a,b=self.periods();r=compare(a,b);self.assertEqual(len(r['matched_rows']),1);self.assertEqual(r['matched_rows'][0]['clicks_delta'],-5);self.assertEqual(r['matched_rows'][0]['clicks_change_ratio'],-.5)
    def test_missing_row_not_zero(self):
        a,b=self.periods();r=compare(a,b);self.assertEqual(r['unmatched_before'],[{'page':'https://bingx.com/en/b'}]);self.assertFalse(r['sitewide_change_proven'])
    def test_weighted_position_on_observed_rows(self):
        a,b=self.periods();r=compare(a,b);self.assertAlmostEqual(r['observed_before']['position'],30/11);self.assertAlmostEqual(r['observed_before']['ctr'],1/11)
    def test_empty_window_unknown_ratio(self):
        a=period('2026-09-01','2026-09-07',[]);b=period('2026-09-08','2026-09-14',[]);r=compare(a,b);self.assertIsNone(r['observed_before']['position']);self.assertEqual(r['matched_rows'],[])
    def test_zero_prior_clicks_no_infinite_growth(self):
        a=period('2026-09-01','2026-09-07',[row('x',0,10,2)]);b=period('2026-09-08','2026-09-14',[row('x',2,10,2)]);self.assertIsNone(compare(a,b)['matched_rows'][0]['clicks_change_ratio'])
    def test_different_window_length_rejected(self):
        a,b=self.periods();b['query']['endDate']='2026-09-13'
        with self.assertRaises(ValueError):compare(a,b)
    def test_overlapping_window_rejected(self):
        a,b=self.periods();b['query']['startDate']='2026-09-07';b['query']['endDate']='2026-09-13'
        with self.assertRaises(ValueError):compare(a,b)
    def test_different_filters_rejected(self):
        a,b=self.periods();b['query']['dimensionFilterGroups']=[{'filters':[{'dimension':'country','expression':'USA'}]}]
        with self.assertRaises(ValueError):compare(a,b)
    def test_incomplete_data_not_final_comparison(self):
        a,b=self.periods();b['may_include_incomplete_data']=True
        with self.assertRaises(ValueError):compare(a,b)
    def test_duplicate_keys_require_pagination_reconciliation(self):
        a,b=self.periods();a['rows'].append(dict(a['rows'][0]))
        with self.assertRaises(ValueError):compare(a,b)
    def test_different_response_aggregation_rejected(self):
        a,b=self.periods();b['response_aggregation']='byProperty'
        with self.assertRaises(ValueError):compare(a,b)
    def test_startrow_not_zero_cannot_compare_whole_window(self):
        a,b=self.periods();b['start_row']=25000
        with self.assertRaises(ValueError):compare(a,b)
if __name__=='__main__':unittest.main()
