"""Local, bounded, source-bound evidence. UI mapping remains reviewed transcription."""
import json,hashlib,re,math
from pathlib import Path
from urllib.parse import urlsplit,unquote
from datetime import datetime
from collections import Counter
from . import contracts as c
MAX_BYTES=8*1024*1024
REPORTS={'diagnostics','duplicates','sitemaps','searchable','excluded','crawl_stats','page_check','database','js_render','performance','get_parameters','security'}
SECRET=re.compile(r'(?i)(authorization\s*:\s*(?:bearer|oauth|basic)|(?:access_token|api_key|apikey|refresh_token|set-cookie)\s*[=:])')
def no_secrets(v):
 if isinstance(v,dict):
  for k,x in v.items():
   if str(k).lower().replace('-','_') in {'access_token','refresh_token','authorization','cookie','set_cookie','api_key','apikey','password'}:raise ValueError('credential_field')
   no_secrets(x)
 elif isinstance(v,list):
  for x in v:no_secrets(x)
 elif isinstance(v,str) and SECRET.search(v):raise ValueError('credential_text')
def pairs(items):
 d={}
 for k,v in items:
  if k in d:raise ValueError('duplicate_json_key')
  d[k]=v
 return d
def decode(raw):
 def bad(v):raise ValueError('nonfinite_json')
 return json.loads(raw,object_pairs_hook=pairs,parse_constant=bad)
def local(root,name):
 p=Path(name)
 if p.is_absolute():raise ValueError('absolute_evidence_path')
 p=(root/p).resolve()
 if not p.is_relative_to(root.resolve()):raise ValueError('evidence_path_escape')
 if p.stat().st_size>MAX_BYTES:raise ValueError('evidence_too_large')
 return p
def norm(v):return ' '.join(c.string(v).split())
def quote(q,raw):
 if norm(q) not in norm(raw):raise ValueError('unbound_quote')
 return q
def token(value,raw):
 # URL token boundaries preserve path, query, order, case and escaping.
 return bool(re.search(r'(?<![\w:/?&=.%+-])'+re.escape(value)+r'(?=$|[\s<>"\'])',raw))
def number(v,q):
 c.integer(v)
 tokens=re.findall(r'(?<![\d,.])\d+(?:,\d{3})*(?![\d,.])',q)
 if not any(int(x.replace(',',''))==v for x in tokens):raise ValueError('number_quote_mismatch')
def date_binding(b,raw,at):
 quote(b['quote'],raw);dt=datetime.strptime(b['quote'],b['format']).date()
 if dt.isoformat()!=b['value'] or dt>c.moment(at).date():raise ValueError('date_quote_mismatch')
 return dt.isoformat()
def fields(bindings,row_quote,at):
 out={'device':'UNKNOWN','js':'UNKNOWN','searchable':None,'http_status':None}
 for k,b in c.obj(bindings).items():
  q=quote(b['quote'],row_quote);v=b['value']
  if k=='searchable':
   if type(v) is not bool:raise ValueError('searchable_must_be_bool')
   positive={'In search','The page is indexed and appears in search results.','and is shown in search results.'}
   negative={'Not in search','The page is excluded from search results.','Excluded'}
   if q not in (positive if v else negative):raise ValueError('searchable_quote_mismatch')
  elif k in {'http_status','count'}:
   if k=='http_status':c.status(v)
   number(v,q)
  elif k=='device':
   if v not in {'DESKTOP','MOBILE','UNKNOWN'} or (v!='UNKNOWN' and not re.search(r'\b'+v+r'\b',q,re.I)):raise ValueError('device_quote_mismatch')
  elif k=='js':
   accepted={'ENABLED':['JavaScript enabled','The page was downloaded with JavaScript execution.'],'DISABLED':['JavaScript disabled','The page was downloaded without JavaScript execution.'],'UNKNOWN':[q]}
   if v not in accepted or q not in accepted[v]:raise ValueError('js_quote_mismatch')
  elif k in {'crawl_at','search_at','tested_at'}:
   v=c.stamp(v,at)
   try:source=c.stamp(q,at)
   except ValueError:raise ValueError('time_requires_source_timezone')
   if source!=v:raise ValueError('time_quote_mismatch')
  elif k in {'reason','severity','state','title','description','note','raw_date','target_url','group_id','count_display'}:c.string(v)
  else:raise ValueError('unknown_ui_field')
  if k=='state' and v not in {'PRESENT','ABSENT','UNDEFINED'}:raise ValueError('invalid_state')
  if k=='target_url':
   v=c.url_id(v)
   if not token(v,q):raise ValueError('target_url_quote_mismatch')
  if k in {'title','description','raw_date','note','count_display','group_id'} and norm(v)!=norm(q):raise ValueError('literal_field_quote_mismatch')
  out[k]=v
 return out

def load_evidence(env,root,host,at,max_age_hours):
 no_secrets(env);c.host_url(host)
 if env['host_id']!=host:raise ValueError('host_mismatch')
 captured=c.stamp(env['captured_at'],at)
 if not c.fresh(captured,at,max_age_hours):raise ValueError('stale_evidence')
 path=local(Path(root),env['source']['path']);data=path.read_bytes();digest=hashlib.sha256(data).hexdigest()
 if digest!=env['source']['sha256']:raise ValueError('sha256_mismatch')
 raw=data.decode('utf-8');no_secrets(raw)
 out={'id':c.string(env['id']),'host_id':host,'captured_at':captured,'source':dict(env['source']),'gaps':[],'rows':[],'verified_site_defect':False}
 kind=env['kind'];out['kind']=kind
 if kind=='yandex_ui':
  p=urlsplit(env['source_url']);sitepath='/site/'+host+'/'
  if p.scheme!='https' or p.hostname not in {'webmaster.yandex.com','webmaster.yandex.ru'} or p.username or p.password or not unquote(p.path).startswith(sitepath):raise ValueError('invalid_yandex_source')
  if env['report'] not in REPORTS:raise ValueError('unknown_report')
  c.string(env['reviewer']);quote(env['site_quote'],raw)
  if env['site_quote'].rstrip('/')!=c.host_url(host).rstrip('/'):raise ValueError('site_quote_mismatch')
  out.update(report=env['report'],source_url=env['source_url'],reviewed_mapping=True,reviewer=env['reviewer'],mode='engine_live' if env['report'] in {'page_check','js_render'} else 'engine_snapshot',database_date=None,filters=env.get('filters',{}))
  if env.get('database_date'):out['database_date']=date_binding(env['database_date'],raw,captured)
  else:out['gaps'].append('database_date_unavailable')
  if env['report'] in {'page_check','js_render'}:
   out['test_time_precision']='local_calendar_day_timezone_unavailable'
   if env.get('test_date'):
    out['test_date']=date_binding(env['test_date'],raw,captured)
    if out['test_date']!=c.moment(captured).date().isoformat():out['mode']='historical_test';out['gaps'].append('historical_engine_test')
   else:out['mode']='undated_test';out['gaps'].append('engine_test_date_unavailable')
  for v in c.arr(env['rows']):
   q=quote(v['quote'],raw);url=v.get('url')
   if url is not None:
    url=c.page(host,url)
    if not token(url,q):raise ValueError('url_not_exact_in_row')
   row=fields(v['fields'],q,captured);row.update(url=url,quote=q,bindings=v['fields']);out['rows'].append(row)
 elif kind=='live_http':
  v=c.obj(decode(raw));no_secrets(v)
  if v['captured_at']!=env['captured_at'] or v['method']!='GET':raise ValueError('http_capture_mismatch')
  url=c.page(host,v['url']);final=c.url_id(v['final_url']);code=c.status(v['status'])
  if v['device'] not in {'DESKTOP','MOBILE','UNKNOWN'} or v['js']!='DISABLED':raise ValueError('invalid_http_environment')
  c.string(v['source_description']);out.update(mode='ordinary_http',report='http',rows=[{'url':url,'final_url':final,'http_status':code,'device':v['device'],'js':'DISABLED','searchable':None,'source_description':v['source_description']}])
  if v.get('body'):
   body=local(Path(root),v['body']['path']).read_bytes()
   if hashlib.sha256(body).hexdigest()!=v['body']['sha256']:raise ValueError('body_hash_mismatch')
   out['body']=v['body']
 elif kind=='public_dom':
  v=c.obj(decode(raw));no_secrets(v);url=c.page(host,v['url'])
  if v['captured_at']!=env['captured_at'] or v['device'] not in {'DESKTOP','MOBILE','UNKNOWN'} or v['js']!='ENABLED':raise ValueError('dom_capture_mismatch')
  c.string(env['reviewer']);rows=[]
  for review in c.arr(env.get('reviews',[])):
   if review['reason'] not in {'ROUTE_ENTITY_MISMATCH','ERROR_PAGE_CONTENT','EMPTY_METADATA','TITLE_COUNTRY_MISSING'}:raise ValueError('unknown_public_review_rule')
   field=review['field']
   if field not in {'title','description','h1','body_excerpt'} or field not in v:raise ValueError('invalid_dom_review_field')
   value=v[field];text=' '.join(value) if isinstance(value,list) else value;q=review['quote']
   if q=='':
    if text!='' or review['reason']!='EMPTY_METADATA':raise ValueError('empty_review_quote')
   else:quote(q,text)
   rows.append({'url':url,'device':v['device'],'js':'ENABLED','searchable':None,'reason':review['reason'],'quote':q,'field':field,'observed_value':value,'reviewer':env['reviewer']})
  out.update(mode='public_dom',report='dom',rows=rows,dom=v,reviewed_mapping=True)
 elif kind=='yandex_api':
  p=urlsplit(env['request_url'])
  expected=r'/v4/user/\d+/hosts/'+re.escape(host)+'/'+re.escape(env['endpoint'])+r'/?'
  if p.scheme!='https' or p.hostname!='api.webmaster.yandex.net' or p.username or p.password or not re.fullmatch(expected,unquote(p.path)):raise ValueError('api_request_host_endpoint_mismatch')
  v=c.api(env['endpoint'],host,decode(raw),captured);out.update(mode='engine_snapshot',report=env['endpoint'],rows=v['rows'],api_metadata=v);out['gaps']+=v['gaps']
 else:raise ValueError('unknown_evidence_kind')
 return out

def load_manifest(path,*,at,max_age_hours=24):
 if not math.isfinite(max_age_hours) or max_age_hours<=0:raise ValueError('invalid_freshness')
 c.moment(at);path=Path(path);root=path.parent.resolve()
 if path.stat().st_size>MAX_BYTES:raise ValueError('manifest_too_large')
 m=c.obj(decode(path.read_text()));no_secrets(m)
 if m.get('schema_version')!=1:raise ValueError('unsupported_schema')
 host=m['host_id'];c.host_url(host)
 if m['run_kind'] not in {'audit','historical_replay','controlled_fixture'}:raise ValueError('invalid_run_kind')
 scope=[]
 for s in c.arr(m['scope']):
  u=c.page(host,s['url'])
  if s['device'] not in {'DESKTOP','MOBILE','UNKNOWN'} or s['js'] not in {'ENABLED','DISABLED','UNKNOWN'}:raise ValueError('invalid_scope_environment')
  item={'url':u,'device':s['device'],'js':s['js']}
  if item not in scope:scope.append(item)
 if not scope:raise ValueError('empty_declared_scope')
 pending=[];gaps=[]
 for name in c.arr(m['evidence']):
  try:pending.append((name,decode(local(root,name).read_text())))
  except (ValueError,OSError,UnicodeError,TypeError) as x:gaps.append({'path':str(name),'reason':str(x)})
 ids=Counter(x.get('id') for _,x in pending if isinstance(x,dict));seen=set();ev=[]
 for name,x in pending:
  try:
   if ids[x['id']]!=1:raise ValueError('duplicate_evidence_id')
   item=load_evidence(x,root,host,at,max_age_hours);key=(item['source']['sha256'],item['report'],item['captured_at'])
   if key in seen:raise ValueError('duplicate_evidence_capture')
   seen.add(key);ev.append(item)
  except (ValueError,TypeError,KeyError,OSError,UnicodeError) as ex:gaps.append({'path':str(name),'reason':str(ex)})
 return {'host_id':host,'scope':scope,'run_kind':m['run_kind'],'evidence':ev,'gaps':gaps}
