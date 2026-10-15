"""Bing-specific contracts: detect false index claims, guessed HTTP codes and mixed position metrics."""
import unittest,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
try:from bing_audit import contracts as c
except ImportError:c=None
SITE='https://bingx.com/';URL=SITE+'en/price/example';AT='2026-09-17T02:00:00Z'
def request(url=URL):return {'siteUrl':SITE,'url':url}
def info(**kw):return {'d':{'Url':URL,'IsPage':True,'HttpStatus':200,'LastCrawledDate':'/Date(0+0800)/',**kw}}
class Contracts(unittest.TestCase):
 def setUp(self):self.assertIsNotNone(c,'Bing contracts not implemented')
 def test_site_url_preserves_prefix(self):self.assertEqual(c.site_id('https://BINGX.com/en/'),'https://bingx.com/en/')
 def test_gsc_domain_property_not_bing_site(self):
  with self.assertRaises(ValueError):c.site_id('sc-domain:bingx.com')
 def test_deceptive_host_rejected(self):
  for s in ['https://bingx.com.evil.test/','https://notbingx.com/','https://user@bingx.com/']:
   with self.subTest(site=s),self.assertRaises(ValueError):c.site_id(s)
 def test_site_query_or_fragment_rejected(self):
  for s in [SITE+'?x=1',SITE+'#foo',SITE+'en']:
   with self.subTest(site=s),self.assertRaises(ValueError):c.site_id(s)
 def test_scope_not_sibling_host_or_scheme(self):
  for u in ['https://help.bingx.com/en','http://bingx.com/en','https://bingx.com/english']:
   self.assertFalse(c.belongs('https://bingx.com/en/',u))
 def test_exact_query_identity_survives(self):self.assertEqual(c.url_id(URL+'?pair=BTC&side=BUY#foo'),URL+'?pair=BTC&side=BUY')
 def test_ms_offset_not_double_applied(self):self.assertEqual(c.ms_time('/Date(0+0800)/'),'1970-01-01T00:00:00Z')
 def test_ms_negative_and_milliseconds_preserved(self):self.assertEqual(c.ms_time('/Date(-1-0700)/'),'1969-12-31T23:59:59.999000Z')
 def test_iso_explicit_timezone_accepted(self):self.assertEqual(c.ms_time('2026-09-16T10:00:00+08:00'),'2026-09-16T02:00:00Z')
 def test_date_only_or_naive_or_invalid_offset_not_guessed(self):
  for v in ['2026-09-16','2026-09-16T10:00:00','/Date(0+2500)/','/Date(NaN)/',True]:
   with self.subTest(value=v),self.assertRaises(ValueError):c.ms_time(v)
 def test_ispage_true_never_means_indexed(self):self.assertIsNone(c.api('GetUrlInfo',request(),info(),captured_at=AT)['indexed'])
 def test_http_zero_is_unknown_not_failed(self):self.assertIsNone(c.api('GetUrlInfo',request(),info(HttpStatus=0),captured_at=AT)['historical_http_status'])
 def test_http_success_is_historical_not_live(self):
  r=c.api('GetUrlInfo',request(),info(),captured_at=AT);self.assertEqual(r['historical_http_status'],200);self.assertFalse(r['live_observation']);self.assertEqual(r['device'],'UNKNOWN')
 def test_missing_lastcrawl_stays_unknown(self):self.assertIsNone(c.api('GetUrlInfo',request(),info(LastCrawledDate=None),captured_at=AT)['last_crawled'])
 def test_future_crawl_rejected(self):
  with self.assertRaises(ValueError):c.api('GetUrlInfo',request(),info(LastCrawledDate='2027-01-01T00:00:00Z'),captured_at=AT)
 def test_returned_url_mismatch_rejected(self):
  with self.assertRaises(ValueError):c.api('GetUrlInfo',request(),info(Url=URL+'?pair=ETH'),captured_at=AT)
 def test_domain_summary_not_treated_as_page(self):
  with self.assertRaises(ValueError):c.api('GetUrlInfo',request('domain:bingx.com'),info(),captured_at=AT)
 def test_http_and_boolean_types_strict(self):
  for kw in [{'HttpStatus':True},{'HttpStatus':999},{'IsPage':'true'}]:
   with self.subTest(kw=kw),self.assertRaises(ValueError):c.api('GetUrlInfo',request(),info(**kw),captured_at=AT)
 def test_api_fault_body_never_empty_healthy(self):
  with self.assertRaises(ValueError):c.api('GetUrlInfo',request(),{'ErrorCode':3,'Message':'InvalidApiKey'},captured_at=AT)
 def test_unwrapped_or_null_response_rejected(self):
  for b in [{}, {'d':None}]:
   with self.subTest(body=b),self.assertRaises(ValueError):c.api('GetUrlInfo',request(),b,captured_at=AT)
 def test_mutating_and_retired_methods_rejected(self):
  for m in ['SubmitUrl','SubmitFeed','RemoveSite','soap/GetUrlInfo','pox/GetUrlInfo']:
   with self.subTest(method=m),self.assertRaises(ValueError):c.api(m,request(),info(),captured_at=AT)
 def test_crawl_flags_decode_combined_dns_and_server(self):
  r=c.api('GetCrawlIssues',{'siteUrl':SITE},{'d':[{'Url':URL,'HttpCode':503,'Issues':136,'InLinks':2}]},captured_at=AT)
  self.assertEqual(set(r['entries'][0]['reasons']),{'server_error','dns_error'});self.assertFalse(r['exhaustive'])
 def test_unknown_crawl_bits_preserved_not_silenced(self):
  r=c.api('GetCrawlIssues',{'siteUrl':SITE},{'d':[{'Url':URL,'HttpCode':0,'Issues':512}]},captured_at=AT)
  self.assertEqual(r['entries'][0]['raw_flags'],512);self.assertTrue(r['gaps']);self.assertEqual(r['entries'][0]['reasons'],[])
 def test_robots_and_malware_not_conflated_with_5xx(self):
  r=c.api('GetCrawlIssues',{'siteUrl':SITE},{'d':[{'Url':URL,'HttpCode':200,'Issues':48}]},captured_at=AT)
  self.assertEqual(set(r['entries'][0]['reasons']),{'robots_blocked','malware_reported'})
 def test_foreign_crawl_url_rejected(self):
  with self.assertRaises(ValueError):c.api('GetCrawlIssues',{'siteUrl':SITE},{'d':[{'Url':'https://other.test/','HttpCode':200,'Issues':32}]},captured_at=AT)
 def test_negative_or_boolean_flag_rejected(self):
  for v in [-1,True]:
   with self.subTest(value=v),self.assertRaises(ValueError):c.api('GetCrawlIssues',{'siteUrl':SITE},{'d':[{'Url':URL,'HttpCode':200,'Issues':v}]},captured_at=AT)
 def test_feed_success_not_indexing_or_inventory(self):
  r=c.api('GetFeeds',{'siteUrl':SITE},{'d':[{'Url':SITE+'sitemap.xml','Status':'Success','UrlCount':50}]},captured_at=AT)
  self.assertIsNone(r['indexed_count']);self.assertFalse(r['url_inventory_complete']);self.assertEqual(r['entries'][0]['url_count'],50)
 def test_unknown_feed_status_is_gap(self):self.assertTrue(c.api('GetFeeds',{'siteUrl':SITE},{'d':[{'Url':SITE+'sitemap.xml','Status':'FutureStatus','UrlCount':0}]},captured_at=AT)['gaps'])
 def test_query_position_fields_remain_separate(self):
  r=c.api('GetQueryStats',{'siteUrl':SITE},{'d':[{'Query':'bingx','Clicks':2,'Impressions':10,'AvgClickPosition':3,'AvgImpressionPosition':9,'Date':'/Date(0)/'}]},captured_at=AT)
  self.assertEqual(r['entries'][0]['avg_click_position'],3);self.assertEqual(r['entries'][0]['avg_impression_position'],9);self.assertEqual(r['entries'][0]['dimension'],'query');self.assertFalse(r['exhaustive'])
 def test_page_stats_query_field_must_be_url(self):
  with self.assertRaises(ValueError):c.api('GetPageStats',{'siteUrl':SITE},{'d':[{'Query':'bingx','Clicks':2,'Impressions':10,'Date':'/Date(0)/'}]},captured_at=AT)
 def test_invalid_metrics_rejected(self):
  for kw in [{'Clicks':-1},{'Impressions':True},{'AvgClickPosition':float('nan')},{'AvgImpressionPosition':-1}]:
   with self.subTest(kw=kw),self.assertRaises(ValueError):c.api('GetQueryStats',{'siteUrl':SITE},{'d':[{'Query':'bingx','Clicks':2,'Impressions':10,'Date':'/Date(0)/',**kw}]},captured_at=AT)
 def test_empty_top_rows_do_not_prove_no_traffic(self):
  r=c.api('GetQueryStats',{'siteUrl':SITE},{'d':[]},captured_at=AT);self.assertFalse(r['exhaustive']);self.assertEqual(r['entries'],[])
if __name__=='__main__':unittest.main()
