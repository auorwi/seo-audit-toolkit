import sys,unittest,copy
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
try:from yandex_audit import contracts as c
except ImportError:c=None
AT='2026-09-17T03:00:00Z';HOST='https:bingx.com:443';URL='https://bingx.com/en?a=1&b=2'
class Contracts(unittest.TestCase):
 def setUp(self):self.assertIsNotNone(c,'Yandex contracts not implemented')
 def test_host_exact_scheme_port(self):self.assertEqual(c.host_url(HOST),'https://bingx.com/')
 def test_http_distinct(self):self.assertEqual(c.host_url('http:bingx.com:80'),'http://bingx.com/')
 def test_reject_foreign_hosts(self):
  for x in ['https:bingx.com.evil.test:443','https:evil.test:443','https://bingx.com/','https:user@bingx.com:443']:
   with self.subTest(x=x),self.assertRaises(ValueError):c.host_url(x)
 def test_subdomain_allowed_explicit(self):self.assertEqual(c.host_url('https:www.bingx.com:443'),'https://www.bingx.com/')
 def test_no_silent_subdomain_merge(self):
  with self.assertRaises(ValueError):c.page(HOST,'https://www.bingx.com/en')
 def test_query_order_preserved(self):self.assertEqual(c.page(HOST,URL),URL)
 def test_no_fragment(self):
  with self.assertRaises(ValueError):c.page(HOST,URL+'#a')
 def test_comma_datetime_offset(self):self.assertEqual(c.stamp('2026-09-16T12:00:00,000+0300',AT),'2026-09-16T09:00:00Z')
 def test_naive_rejected(self):
  with self.assertRaises(ValueError):c.stamp('2026-09-16T12:00:00',AT)
 def test_future_rejected(self):
  with self.assertRaises(ValueError):c.stamp('2026-09-18T00:00:00Z',AT)
 def api(self,ep,body):return c.api(ep,HOST,body,AT)
 def test_diagnostics_three_states(self):
  r=self.api('diagnostics',{'problems':{s:{'severity':'RECOMMENDATION','state':s,'last_state_update':'2026-09-16T00:00:00Z'} for s in ['PRESENT','ABSENT','UNDEFINED']}})
  self.assertEqual([x['state'] for x in r['rows']],['PRESENT','ABSENT','UNDEFINED']);self.assertFalse(r['all_site_verified'])
 def test_unknown_diag_state_rejected(self):
  with self.assertRaises(ValueError):self.api('diagnostics',{'problems':{'x':{'severity':'FATAL','state':'yes','last_state_update':AT}}})
 def test_unknown_severity_preserved(self):
  r=self.api('diagnostics',{'problems':{'x':{'severity':'NEW_LEVEL','state':'PRESENT','last_state_update':AT}}});self.assertIn('unknown_severity',r['gaps'])
 def test_crawl_200_not_searchable(self):
  r=self.api('indexing/samples',{'count':50000,'samples':[{'url':URL,'http_code':200,'status':'HTTP_2XX','access_date':AT}]});self.assertIsNone(r['rows'][0]['searchable']);self.assertEqual(r['available_samples'],50000);self.assertFalse(r['all_site_verified'])
 def test_crawl_other_not_500(self):
  r=self.api('indexing/samples',{'count':1,'samples':[{'url':URL,'status':'OTHER','access_date':AT}]});self.assertIsNone(r['rows'][0]['http_status'])
 def test_http_class_conflict_rejected(self):
  with self.assertRaises(ValueError):self.api('indexing/samples',{'count':1,'samples':[{'url':URL,'status':'HTTP_5XX','http_code':200,'access_date':AT}]})
 def test_invalid_count_rejected(self):
  for count in [True,-1,1.5,'1']:
   with self.subTest(count=count),self.assertRaises(ValueError):self.api('indexing/samples',{'count':count,'samples':[]})
 def test_sample_count_less_than_rows(self):
  with self.assertRaises(ValueError):self.api('indexing/samples',{'count':0,'samples':[{'url':URL,'status':'OTHER','access_date':AT}]})
 def important(self):return {'urls':[{'url':URL,'update_date':AT,'indexing_status':{'status':'HTTP_2XX','http_code':200,'access_date':'2026-09-16T01:00:00Z'},'search_status':{'title':'t','last_access':'2026-09-15T02:00:00Z','searchable':False,'excluded_url_status':'NOT_CANONICAL','target_url':'https://bingx.com/en'}}]}
 def test_independent_crawl_and_search_dates(self):
  r=self.api('important-urls',self.important())['rows'][0];self.assertEqual(r['crawl_at'],'2026-09-16T01:00:00Z');self.assertEqual(r['search_at'],'2026-09-15T02:00:00Z');self.assertFalse(r['searchable'])
 def test_target_not_always_canonical(self):
  r=self.important();r['urls'][0]['search_status']['excluded_url_status']='DUPLICATE';row=self.api('important-urls',r)['rows'][0];self.assertEqual(row['target_relation'],'engine_related_url');self.assertNotIn('canonical',row)
 def test_important_without_search_unknown(self):
  r=self.important();del r['urls'][0]['search_status'];self.assertIsNone(self.api('important-urls',r)['rows'][0]['searchable'])
 def test_search_bool_str_rejected(self):
  r=self.important();r['urls'][0]['search_status']['searchable']='false'
  with self.assertRaises(ValueError):self.api('important-urls',r)
 def test_search_event_is_historical_not_current(self):
  r=self.api('search-urls/events/samples',{'count':1,'samples':[{'url':URL,'title':'x','event':'REMOVED_FROM_SEARCH','event_date':AT,'last_access':'2026-09-15T00:00:00Z','excluded_url_status':'LOW_QUALITY'}]})['rows'][0];self.assertIsNone(r['searchable']);self.assertEqual(r['event'],'REMOVED_FROM_SEARCH')
 def test_unknown_reason_preserved(self):
  r=self.important();r['urls'][0]['search_status']['excluded_url_status']='FUTURE_REASON';o=self.api('important-urls',r);self.assertEqual(o['rows'][0]['reason'],'FUTURE_REASON');self.assertIn('unknown_exclusion_reason',o['gaps'])
 def test_sitemap_count_not_index_count(self):
  r=self.api('sitemaps',{'sitemaps':[{'sitemap_id':'x','sitemap_url':'https://bingx.com/sitemap.xml','errors_count':0,'urls_count':20,'children_count':3,'sources':['ROBOTS_TXT'],'sitemap_type':'SITEMAP_INDEX'}]});self.assertEqual(r['rows'][0]['urls_count'],20);self.assertIsNone(r['rows'][0]['indexed_count']);self.assertFalse(r['all_site_verified'])
 def test_api_error_not_website_failure(self):
  with self.assertRaisesRegex(ValueError,'api_error'):self.api('diagnostics',{'error_code':'HOST_NOT_VERIFIED'})
 def test_mutation_endpoint_rejected(self):
  with self.assertRaises(ValueError):self.api('recrawl/queue',{})
 def test_bool_http_rejected(self):
  with self.assertRaises(ValueError):self.api('indexing/samples',{'count':1,'samples':[{'url':URL,'status':'OTHER','http_code':True,'access_date':AT}]})
 def test_duplicate_url_rows_retained(self):
  row={'url':URL,'status':'OTHER','access_date':AT};self.assertEqual(len(self.api('indexing/samples',{'count':2,'samples':[row,row]})['rows']),2)
