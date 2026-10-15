"""Yandex v4 read-only response contracts. Crawling is not presence in search."""

import sys as _site_sys
from pathlib import Path as _SitePath
_site_dependency=_SitePath(__file__).resolve().parents[3]/'seo-crawlability/scripts'
if str(_site_dependency) not in _site_sys.path:_site_sys.path.insert(0,str(_site_dependency))
from crawlability.site import get_profile,site_host,site_origin,allowed_hosts,in_scope,require_url,brand_name,business_profile
import sys,re
from pathlib import Path
from urllib.parse import urlsplit
shared=Path(__file__).resolve().parents[3]/'seo-crawlability'/'scripts'
if not shared.is_dir():raise ImportError('Requires sibling seo-crawlability')
sys.path.insert(0,str(shared))
from crawlability.common import url_id,moment,fresh

def obj(v):
 if not isinstance(v,dict):raise ValueError('object_required')
 return v

def arr(v):
 if not isinstance(v,list):raise ValueError('array_required')
 return v

def string(v):
 if not isinstance(v,str) or not v:raise ValueError('nonempty_string_required')
 return v

def integer(v):
 if type(v) is not int or not 0<=v<=2**53-1:raise ValueError('nonnegative_safe_integer_required')
 return v

def host_url(v):
 m=re.fullmatch(r'(https?):([a-zA-Z0-9.-]+):(\d+)',string(v))
 if not m:raise ValueError('invalid_host_id')
 scheme,host,port=m.groups();host=host.lower()
 if host not in allowed_hosts() or int(port)!=(443 if scheme=='https' else 80):raise ValueError('foreign_host')
 return url_id(f'{scheme}://{host}:{port}/')

def page(host,v):
 u=url_id(v);p=urlsplit(u)
 if '#' in v or p.scheme+'://'+p.netloc+'/'!=host_url(host):raise ValueError('url_outside_host_or_fragment')
 return u

def stamp(v,at):
 dt=moment(v)
 if dt>moment(at):raise ValueError('future_timestamp')
 return dt.isoformat().replace('+00:00','Z')

def status(v):
 if type(v) is not int or not 100<=v<=599:raise ValueError('invalid_http_status')
 return v

REASONS={'NOTHING_FOUND','HOST_ERROR','REDIRECT_NOTSEARCHABLE','HTTP_ERROR','NOT_CANONICAL','NOT_MAIN_MIRROR','PARSER_ERROR','ROBOTS_HOST_ERROR','ROBOTS_URL_ERROR','DUPLICATE','LOW_QUALITY','CLEAN_PARAMS','NO_INDEX','OTHER'}
def api(endpoint,host,body,at):
 host_url(host);moment(at);obj(body)
 if 'error_code' in body:raise ValueError('api_error:'+str(body['error_code']))
 rows=[];gaps=[];out={'endpoint':endpoint,'host_id':host,'rows':rows,'gaps':gaps,'all_site_verified':False,'available_samples':None}
 def crawl(v):
  obj(v);group=string(v['status']);code=status(v['http_code']) if v.get('http_code') is not None else None
  if group.startswith('HTTP_') and group in {'HTTP_2XX','HTTP_3XX','HTTP_4XX','HTTP_5XX'} and code is not None and code//100!=int(group[5]):raise ValueError('http_class_conflict')
  if group not in {'HTTP_2XX','HTTP_3XX','HTTP_4XX','HTTP_5XX','OTHER'}:gaps.append('unknown_crawl_status')
  return {'http_status':code,'crawl_status':group,'crawl_at':stamp(v['access_date'],at)}
 def reason(row,v):
  r=v.get('excluded_url_status');row['reason']=r
  if r is not None and string(r) not in REASONS:gaps.append('unknown_exclusion_reason')
  if 'bad_http_status' in v:row['bad_http_status']=status(v['bad_http_status'])
  if 'target_url' in v:row.update(target_url=url_id(v['target_url']),target_relation='engine_related_url')
 if endpoint=='diagnostics':
  for key,v in obj(body['problems']).items():
   obj(v);state=v['state'];severity=string(v['severity'])
   if state not in {'PRESENT','ABSENT','UNDEFINED'}:raise ValueError('invalid_diagnostic_state')
   if severity not in {'FATAL','CRITICAL','POSSIBLE_PROBLEM','RECOMMENDATION'}:gaps.append('unknown_severity')
   rows.append({'reason':key,'state':state,'severity':severity,'state_updated_at':stamp(v['last_state_update'],at),'url':None})
 elif endpoint in {'indexing/samples','search-urls/events/samples'}:
  out['available_samples']=integer(body['count']);samples=arr(body['samples'])
  if len(samples)>out['available_samples']:raise ValueError('sample_count_conflict')
  gaps.append('samples_not_full_inventory')
  for v in samples:
   row={'url':page(host,v['url']),'device':'UNKNOWN','js':'UNKNOWN','searchable':None}
   if endpoint=='indexing/samples':row.update(crawl(v))
   else:
    if v['event'] not in {'APPEARED_IN_SEARCH','REMOVED_FROM_SEARCH'}:raise ValueError('unknown_search_event')
    row.update(event=v['event'],event_at=stamp(v['event_date'],at),search_at=stamp(v['last_access'],at));reason(row,v)
   rows.append(row)
 elif endpoint=='important-urls':
  gaps.append('selected_important_urls_not_full_inventory')
  for v in arr(body['urls']):
   row={'url':page(host,v['url']),'device':'UNKNOWN','js':'UNKNOWN','searchable':None}
   if 'update_date' in v:row['updated_at']=stamp(v['update_date'],at)
   if 'indexing_status' in v:row.update(crawl(v['indexing_status']))
   if 'search_status' in v:
    s=obj(v['search_status'])
    if type(s['searchable']) is not bool:raise ValueError('searchable_must_be_bool')
    row.update(searchable=s['searchable'],search_at=stamp(s['last_access'],at),title=s['title']);reason(row,s)
   rows.append(row)
 elif endpoint=='sitemaps':
  for v in arr(body['sitemaps']):
   row={'url':page(host,v['sitemap_url']),'sitemap_id':string(v['sitemap_id']),'indexed_count':None,'sitemap_type':string(v['sitemap_type']),'sources':arr(v['sources'])}
   for k in ['errors_count','urls_count','children_count']:row[k]=integer(v[k])
   if v.get('last_access_date'):row['last_access_at']=stamp(v['last_access_date'],at)
   rows.append(row)
 else:raise ValueError('unsupported_read_only_endpoint')
 return out
