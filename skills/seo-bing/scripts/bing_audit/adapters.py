"""Hash-bound Bing browser/API evidence. Nothing here contacts signed-in sessions."""

import sys as _site_sys
from pathlib import Path as _SitePath
_site_dependency=_SitePath(__file__).resolve().parents[3]/'seo-crawlability/scripts'
if str(_site_dependency) not in _site_sys.path:_site_sys.path.insert(0,str(_site_dependency))
from crawlability.site import get_profile,site_host,site_origin,allowed_hosts,in_scope,require_url,brand_name,business_profile
from crawlability.site import in_scope as in_scope_url
import json,hashlib,re
from pathlib import Path
from collections import Counter
from datetime import date
from urllib.parse import urlsplit,parse_qs
from .contracts import obj,arr,text,integer,site_id,belongs,url_id,moment,fresh,api,http,past
REPORTS={'url_inspection','live_url','site_scan','recommendations','site_explorer','sitemaps','performance','submission','security','crawl_stats'}
DEVICES={'MOBILE','DESKTOP','UNKNOWN'}
SECRET=re.compile(r'(?i)(?:authorization\s*:\s*(?:bearer|basic)|(?:api[_-]?key|access_token|refresh_token|cookie)\s*[=:])')

def clean(v):
 if isinstance(v,dict):
  for k,x in v.items():
   if str(k).lower() in {'apikey','api_key','api-key','access_token','refresh_token','authorization','cookie','cookies','password'}:raise ValueError('credential_material_rejected')
   clean(x)
 elif isinstance(v,list):
  for x in v:clean(x)
 elif isinstance(v,str) and SECRET.search(v):raise ValueError('credential_material_rejected')

def decode(b):
 def pairs(v):
  d={}
  for k,x in v:
   if k in d:raise ValueError('duplicate_json_key')
   d[k]=x
  return d
 def constant(v):raise ValueError('non_json_number')
 d=json.loads(b,object_pairs_hook=pairs,parse_constant=constant);clean(d);return d

def proof(root,ref):
 obj(ref);name=text(ref['path']);p=(root/name).resolve()
 if Path(name).is_absolute() or not p.is_relative_to(root.resolve()):raise ValueError('proof_path_outside_root')
 if p.stat().st_size>8*1024*1024:raise ValueError('proof_too_large')
 b=p.read_bytes()
 if hashlib.sha256(b).hexdigest()!=ref['sha256']:raise ValueError('proof_hash_mismatch')
 return b

def norm(v):return ' '.join(text(v).split())
def urls(v):
 out=set()
 for s in re.findall(r'https?://[^\s<>"\']+',v):
  try:out.add(url_id(s))
  except ValueError:pass
 return out

def source_date(q,fmt):
 if fmt=='YYYY-MM-DD':return date.fromisoformat(q)
 if fmt=='D MMM YYYY':
  m=re.fullmatch(r'(\d{1,2}) ([A-Za-z]+) (\d{4})',q);months={'Jan':1,'Feb':2,'Mar':3,'Apr':4,'May':5,'Jun':6,'Jul':7,'Aug':8,'Sep':9,'Sept':9,'Oct':10,'Nov':11,'Dec':12}
  if m and m[2] in months:return date(int(m[3]),months[m[2]],int(m[1]))
 if fmt in {'D/M/YYYY','M/D/YYYY'}:
  m=re.fullmatch(r'(\d{1,2})/(\d{1,2})/(\d{4})',q)
  if m:
   a,b,y=map(int,m.groups());return date(y,a,b) if fmt.startswith('M/') else date(y,b,a)
 raise ValueError('unsupported_date_quote')

def ui(raw,root):
 site=site_id(raw['site']);source=obj(raw['source']);p=urlsplit(text(source['url']))
 if p.username or p.password or p.scheme!='https' or p.hostname not in {'www.bing.com','www2.bing.com','bing.com'} or not p.path.startswith('/webmasters'):raise ValueError('not_bing_webmaster_source')
 q=parse_qs(p.query).get('siteUrl')
 if not q or len(q)!=1 or site_id(q[0])!=site:raise ValueError('source_site_mismatch')
 body=proof(root,source).decode('utf-8');clean(body);n=norm(body);tokens=urls(n)
 def quote(q):
  q=norm(q)
  if not q or q not in n:raise ValueError('unsubstantiated_quote')
  return q
 sq=quote(raw['site_quote']);host=urlsplit(site).netloc
 if not re.search(r'(?<![\w.-])'+re.escape(host)+r'(?![\w.-])',sq):raise ValueError('site_quote_mismatch')
 if not text(raw['reviewer']).strip():raise ValueError('reviewer_required')
 report=raw['report']
 if report not in REPORTS:raise ValueError('unknown_report')
 obj(raw['filters']);d=raw.get('report_date');gaps=[]
 if d is not None:
  if date.fromisoformat(text(d))!=source_date(quote(raw['report_date_quote']),raw.get('report_date_format','YYYY-MM-DD')):raise ValueError('report_date_quote_mismatch')
  if date.fromisoformat(d)>moment(raw['captured_at']).date():raise ValueError('future_report_date')
 elif report not in {'url_inspection','live_url'}:gaps.append('report_data_date_unavailable')
 unit=raw['count_unit']
 if unit not in {'pages','urls','issues','occurrences','items','sitemaps','not_applicable'}:raise ValueError('invalid_count_unit')
 total=raw.get('reported_total')
 if total is not None:
  integer(total);q=quote(raw['total_quote']);s=q.replace(',','').replace(' ','')
  if not re.search(r'(?<![\d,.])'+re.escape(q)+r'(?![\d,.])',n):raise ValueError('total_number_boundary_mismatch')
  if not s.isascii() or not s.isdigit() or int(s)!=total:raise ValueError('total_quote_mismatch')
 def bind(u,q,related=False):
  u=url_id(u);s=quote(q)
  host=urlsplit(u).hostname
  in_scope=belongs(site,u) or (related and in_scope_url(u))
  if not in_scope or u not in tokens or u not in urls(s):raise ValueError('url_quote_mismatch')
  return u
 rows=[]
 for row in arr(raw.get('rows',[])):
  obj(row);key=text(row['reason_key']);label=norm(row['reason_label']);q=quote(row['quote'])
  if not re.fullmatch(r'[a-z][a-z0-9_]{0,79}',key) or not label or label not in q:raise ValueError('invalid_reason_binding')
  u=bind(row['url'],row['url_quote'],related=True) if row.get('url') else None;device=row.get('device','UNKNOWN')
  if device not in DEVICES:raise ValueError('invalid_device')
  rows.append({**row,'url':u,'device':device,'outside_site_prefix':bool(u and not belongs(site,u))})
 if unit in {'pages','urls'} and total is not None and total<len({r['url'] for r in rows if r['url']}):raise ValueError('examples_exceed_total')
 inspection=None
 if 'inspection' in raw:
  if report not in {'url_inspection','live_url'}:raise ValueError('inspection_in_wrong_report')
  item=obj(raw['inspection']);u=bind(item['url'],item['url_quote']);device=item.get('device','UNKNOWN')
  if device not in DEVICES:raise ValueError('invalid_device')
  inspection={'url':u,'device':device,'indexed':None,'fetch_state':'UNKNOWN','http_status':None,'last_crawled':None,'mode':'live' if report=='live_url' else 'index','field_bindings':{}}
  allowed={'indexed','fetch_state','http_status','last_crawled','index_reason','crawl_allowed'}
  for key,b in obj(item['fields']).items():
   if key not in allowed:raise ValueError('unsupported_inspection_field')
   obj(b);q=quote(b['quote']);v=b['value']
   if key=='indexed':
    if report=='live_url' or type(v) is not bool:raise ValueError('indexed_boolean_only_in_index_report')
   elif key=='fetch_state':
    if v not in {'SUCCESS','FAILED','UNKNOWN'}:raise ValueError('unknown_fetch_state')
   elif key=='http_status':
    http(v)
    if str(v) not in re.findall(r'(?<!\d)\d{3}(?!\d)',q):raise ValueError('http_quote_mismatch')
   elif key=='last_crawled':
    # A displayed naive/date-only string cannot be silently assigned a timezone.
    v=past(v,raw['captured_at'])
    if past(q,raw['captured_at'])!=v:raise ValueError('crawl_date_quote_mismatch')
   elif key=='crawl_allowed':
    if v is not None and type(v) is not bool:raise ValueError('invalid_crawl_allowed')
   else:text(v)
   inspection[key]=v;inspection['field_bindings'][key]=dict(b)
  if report=='url_inspection' and inspection['indexed'] is None:gaps.append('explicit_index_status_unavailable')
 if report=='site_scan':
  scan=obj(raw.get('scan',{}));text(scan['id'])
  if 'completed_date' in scan and 'completed_at' in scan:raise ValueError('ambiguous_scan_time')
  if 'completed_date' in scan:
   sd=date.fromisoformat(scan['completed_date'])
   if sd!=source_date(quote(scan['quote']),scan.get('date_format','YYYY-MM-DD')):raise ValueError('scan_date_quote_mismatch')
   age=(moment(raw['captured_at']).date()-sd).days
   if age<0:raise ValueError('future_scan_date')
   if age>7:gaps.append('historical_site_scan_not_current_live_capture')
  else:
   t=past(scan['completed_at'],raw['captured_at'])
   if past(quote(scan['quote']),raw['captured_at'])!=t:raise ValueError('scan_time_quote_mismatch')
   if not fresh(t,raw['captured_at'],168):gaps.append('historical_site_scan_not_current_live_capture')
 return {'kind':'ui_report','report':report,'report_date':d,'filters':raw['filters'],'count_unit':unit,'reported_total':total,'rows':rows,'inspection':inspection,'scan':raw.get('scan'),'source':source,'reviewer':raw['reviewer'],'examples_exhaustive':False,'gaps':gaps}

def load_manifest(path,*,at,max_age_hours=24):
 moment(at);fresh(at,at,max_age_hours);path=Path(path);root=path.parent.resolve()
 if path.stat().st_size>8*1024*1024:raise ValueError('manifest_too_large')
 m=obj(decode(path.read_bytes()));site=site_id(m['site'])
 if type(m.get('schema_version')) is not int or m['schema_version']!=1:raise ValueError('unsupported_schema')
 kind=m.get('run_kind','audit')
 if kind not in {'audit','historical_replay','controlled_fixture'}:raise ValueError('invalid_run_kind')
 scope=[];seen=set()
 for s in arr(m['scope']):
  obj(s);u=url_id(s['url']);device=s['device']
  if not belongs(site,u) or device not in DEVICES:raise ValueError('invalid_scope')
  if (u,device) not in seen:scope.append({'url':u,'device':device});seen.add((u,device))
 refs=arr(m['evidence']);ids=Counter(text(obj(r)['id']) for r in refs);hashes=set();observations=[];gaps=[]
 for ref in refs:
  try:
   if not ref['id'] or ids[ref['id']]>1:raise ValueError('duplicate_evidence_id')
   b=proof(root,ref)
   if ref['sha256'] in hashes:raise ValueError('duplicate_evidence_content')
   raw=obj(decode(b));k=raw['kind']
   if k!=ref['kind'] or site_id(raw['site'])!=site:raise ValueError('kind_or_site_mismatch')
   captured=raw['captured_at']
   if not fresh(captured,at,max_age_hours):raise ValueError('stale_or_future_capture')
   if k=='bing_ui':d=ui(raw,root)
   elif k=='bing_api':
    if type(raw['http_status']) is not int or raw['http_status']!=200:raise ValueError('api_http_error')
    if site_id(raw['request']['siteUrl'])!=site:raise ValueError('api_site_mismatch')
    d=api(raw['method'],raw['request'],raw['response'],captured_at=captured)
   elif k=='live_http':
    u=url_id(raw['url']);final=url_id(raw['final_url']);status=http(raw['status']);device=raw['device']
    if status is None or raw['method']!='GET' or device not in DEVICES or not belongs(site,u) or not belongs(site,final) or not text(raw['source_description']).strip():raise ValueError('invalid_http_observation')
    d={'kind':'live_http','url':u,'final_url':final,'device':device,'status':status,'source_description':raw['source_description']}
   else:raise ValueError('unknown_evidence_kind')
   hashes.add(ref['sha256']);observations.append({'id':ref['id'],'kind':k,'site':site,'captured_at':captured,'proof':dict(ref),'data':d})
  except (ValueError,TypeError,KeyError,OSError,UnicodeError,OverflowError) as exc:
   reason=str(exc) if not isinstance(exc,OSError) else 'proof_unreadable'
   gaps.append({'evidence_id':ref['id'],'reason':reason})
 return {'site':site,'scope':scope,'run_kind':kind,'observations':observations,'gaps':gaps,'manifest_sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
