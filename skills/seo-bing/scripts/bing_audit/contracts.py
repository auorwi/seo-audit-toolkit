"""Bing REST JSON observations; index status is never inferred from IsPage or HTTP 200."""

import sys as _site_sys
from pathlib import Path as _SitePath
_site_dependency=_SitePath(__file__).resolve().parents[3]/'seo-crawlability/scripts'
if str(_site_dependency) not in _site_sys.path:_site_sys.path.insert(0,str(_site_dependency))
from crawlability.site import get_profile,site_host,site_origin,allowed_hosts,in_scope,require_url,brand_name,business_profile
import sys,re,math
from pathlib import Path
from datetime import datetime,timezone,timedelta
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

def text(v):
 if not isinstance(v,str):raise ValueError('string_required')
 return v

def integer(v):
 if type(v) is not int or not 0<=v<=2**53-1:raise ValueError('nonnegative_safe_integer_required')
 return v

def site_id(v):
 p=urlsplit(text(v));u=url_id(v)
 if p.username or p.password or p.query or p.fragment or '?' in v or '#' in v or not p.path.endswith('/') or not in_scope(u):raise ValueError('invalid_site_prefix')
 return u

def belongs(site,url):return url_id(url).startswith(site_id(site))

def ms_time(v):
 text(v);m=re.fullmatch(r'/Date\((-?\d+)([+-]\d{4})?\)/',v)
 if m:
  if m[2] and (int(m[2][1:3])>23 or int(m[2][3:])>59):raise ValueError('invalid_date_offset')
  try:d=datetime(1970,1,1,tzinfo=timezone.utc)+timedelta(milliseconds=int(m[1]))
  except OverflowError:raise ValueError('date_out_of_range') from None
 else:d=moment(v).astimezone(timezone.utc)
 return d.isoformat().replace('+00:00','Z')

def past(v,at):
 if v is None:return None
 t=ms_time(v)
 if moment(t)>moment(at):raise ValueError('future_platform_date')
 return t

def http(v):
 integer(v)
 if v==0:return None
 if not 100<=v<=599:raise ValueError('invalid_http_status')
 return v

FLAGS={1:'redirect_301',2:'redirect_302',4:'http_4xx',8:'server_error',16:'robots_blocked',32:'malware_reported',64:'important_url_robots_blocked',128:'dns_error',256:'timeout'}
METHODS={'GetUrlInfo','GetCrawlIssues','GetFeeds','GetQueryStats','GetPageStats'}

def api(method,request,body,*,captured_at):
 moment(captured_at);obj(request);obj(body)
 if method not in METHODS:raise ValueError('unsupported_readonly_method')
 site=site_id(request['siteUrl'])
 if 'ErrorCode' in body or 'error' in body:raise ValueError('api_fault')
 if 'd' not in body or body['d'] is None:raise ValueError('missing_response_payload')
 payload=body['d'];gaps=[]
 def scoped(u):
  u=url_id(u)
  if not belongs(site,u):raise ValueError('response_url_outside_site')
  return u
 if method=='GetUrlInfo':
  d=obj(payload);u=scoped(request['url'])
  if scoped(d['Url'])!=u:raise ValueError('response_url_mismatch')
  ispage=d.get('IsPage')
  if ispage is not None and type(ispage) is not bool:raise ValueError('invalid_ispage')
  code=http(d['HttpStatus']) if 'HttpStatus' in d else None
  return {'kind':'url_info','url':u,'device':'UNKNOWN','indexed':None,'is_page':ispage,'historical_http_status':code,'last_crawled':past(d.get('LastCrawledDate'),captured_at),'discovered_at':past(d.get('DiscoveryDate'),captured_at),'live_observation':False,'gaps':['explicit_index_status_unavailable']}
 entries=[]
 for raw in arr(payload):
  d=obj(raw)
  if method=='GetCrawlIssues':
   u=scoped(d['Url']);flags=integer(d['Issues']);unknown=flags & ~511
   if unknown:gaps.append({'url':u,'reason':'unknown_crawl_flags','bits':unknown})
   if 'InLinks' in d:integer(d['InLinks'])
   entries.append({'url':u,'historical_http_status':http(d['HttpCode']),'raw_flags':flags,'reasons':[reason for bit,reason in FLAGS.items() if flags & bit],'inlinks':d.get('InLinks')})
  elif method=='GetFeeds':
   u=scoped(d['Url']);status=text(d['Status']);count=integer(d['UrlCount']) if 'UrlCount' in d else None
   if status not in {'Success'}:gaps.append({'url':u,'reason':'feed_status_requires_review','status':status})
   entries.append({'url':u,'status':status,'url_count':count,'last_crawled':past(d.get('LastCrawled'),captured_at),'submitted_at':past(d.get('Submitted'),captured_at)})
  else:
   key=scoped(d['Query']) if method=='GetPageStats' else text(d['Query'])
   clicks=integer(d['Clicks']);impressions=integer(d['Impressions'])
   def position(k):
    v=d.get(k)
    if v is not None and (type(v) not in {int,float} or not math.isfinite(v) or v<0):raise ValueError('invalid_position')
    return v
   entries.append({'dimension':'page' if method=='GetPageStats' else 'query','key':key,'clicks':clicks,'impressions':impressions,'avg_click_position':position('AvgClickPosition'),'avg_impression_position':position('AvgImpressionPosition'),'date':past(d['Date'],captured_at),'raw_date':d['Date']})
 result={'kind':{'GetCrawlIssues':'crawl_issues','GetFeeds':'sitemaps','GetPageStats':'performance','GetQueryStats':'performance'}[method],'entries':entries,'gaps':gaps,'exhaustive':False,'live_observation':False}
 if method=='GetFeeds':result.update(indexed_count=None,url_inventory_complete=False)
 return result
