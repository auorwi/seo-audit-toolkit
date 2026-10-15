"""Bound original issues and comparable captures for retesting, without network IO."""

import sys as _site_sys
from pathlib import Path as _SitePath
_site_dependency=_SitePath(__file__).resolve().parents[3]/'seo-crawlability/scripts'
if str(_site_dependency) not in _site_sys.path:_site_sys.path.insert(0,str(_site_dependency))
from crawlability.site import get_profile,site_host,site_origin,allowed_hosts,in_scope,require_url,brand_name,business_profile
import sys,json,hashlib,re,math
from pathlib import Path
from collections import Counter
from urllib.parse import urlsplit
from .checks import evaluate
shared=Path(__file__).resolve().parents[3]/'seo-crawlability'/'scripts'
if not shared.is_dir():raise ImportError('Requires sibling seo-crawlability')
sys.path.insert(0,str(shared))
from crawlability.common import url_id,moment,fresh
MAX_BYTES=16*1024*1024

def no_secrets(v):
 if isinstance(v,dict):
  for k,x in v.items():
   if k.lower().replace('-','_') in {'access_token','refresh_token','api_key','authorization','cookie','set_cookie','password'}:raise ValueError('credential_field')
   no_secrets(x)
 elif isinstance(v,list):
  for x in v:no_secrets(x)
 elif isinstance(v,str) and re.search(r'(?i)(authorization\s*:\s*(?:bearer|oauth|basic)|(?:access_token|api_key|refresh_token)\s*[=:])',v):raise ValueError('credential_text')
def decode(text):
 def pairs(xs):
  d={}
  for k,v in xs:
   if k in d:raise ValueError('duplicate_json_key')
   d[k]=v
  return d
 def bad(v):raise ValueError('nonfinite_json')
 return json.loads(text,object_pairs_hook=pairs,parse_constant=bad)
def proof(root,ref):
 p=Path(ref['path'])
 if p.is_absolute():raise ValueError('absolute_path')
 p=(root/p).resolve()
 if not p.is_relative_to(root.resolve()) or p.stat().st_size>MAX_BYTES:raise ValueError('path_boundary_or_size')
 b=p.read_bytes()
 if hashlib.sha256(b).hexdigest()!=ref['sha256']:raise ValueError('sha256_mismatch')
 text=b.decode('utf-8');no_secrets(text);return text

def hashes(v):
 result=set()
 if isinstance(v,dict):
  for k,x in v.items():
   if k=='sha256' and isinstance(x,str):result.add(x)
   result.update(hashes(x))
 elif isinstance(v,list):
  for x in v:result.update(hashes(x))
 return result

def page(v):
 u=url_id(v);h=urlsplit(u).hostname
 if '#' in v or not in_scope(u):raise ValueError('outside_site_or_fragment')
 return u

def snapshot(desc,case,root,at,max_age_hours,baseline=False):
 v=decode(proof(root,desc['source']));no_secrets(v);stamp=moment(v['captured_at'])
 if stamp>moment(at) or (not baseline and not fresh(v['captured_at'],at,max_age_hours)):raise ValueError('capture_stale_or_future')
 if page(v['url'])!=case['url'] or v['device']!=case['device'] or v['js']!=case['js'] or desc['entry']!=case['entry']:raise ValueError('capture_environment_mismatch')
 kind=desc['kind']
 if kind not in {'http','dom'}:raise ValueError('unsupported_capture_kind')
 complete=[]
 if kind=='http':
  if v.get('method')!='GET' or v['js']!='DISABLED' or type(v.get('status')) is not int or not 100<=v['status']<=599:raise ValueError('invalid_http_capture')
  if page(v['final_url'])!=case['url']:raise ValueError('different_landing_unverified')
  complete=['status','final_url']
 else:
  if v['js']!='ENABLED':raise ValueError('dom_js_mismatch')
  complete=[x for x in ['title','description','h1','canonical'] if x in v]
  # body_excerpt remains incomplete even if a caller adds a body_complete flag.
 if v.get('navigation_at') and moment(v['navigation_at'])>stamp:raise ValueError('navigation_after_capture')
 return {'navigation_at':v.get('navigation_at'),'source':desc['source'],'kind':kind,'captured_at':v['captured_at'],'url':v['url'],'device':v['device'],'js':v['js'],'entry':desc['entry'],'values':v,'complete_fields':complete}

def load_plan(path,*,at,max_age_hours=24):
 if not math.isfinite(max_age_hours) or max_age_hours<=0:raise ValueError('invalid_freshness')
 moment(at);path=Path(path);root=path.parent.resolve()
 if path.stat().st_size>MAX_BYTES:raise ValueError('plan_too_large')
 m=decode(path.read_text());no_secrets(m)
 if m.get('schema_version')!=1 or m.get('run_kind') not in {'audit','historical_replay','controlled_fixture'}:raise ValueError('invalid_plan')
 if not isinstance(m['issues'],list) or not m['issues']:raise ValueError('issues_required')
 ids=Counter(x.get('issue_id') for x in m['issues'] if isinstance(x,dict) and isinstance(x.get('issue_id'),str));out=[];gaps=[]
 for item in m['issues']:
  iid=item.get('issue_id') if isinstance(item,dict) else None
  try:
   if not isinstance(iid,str) or not iid or ids[iid]!=1:raise ValueError('duplicate_or_invalid_issue_id')
   report=decode(proof(root,item['source_report']));source_at=report.get('at')
   if source_at and moment(source_at)>moment(at):raise ValueError('future_source_report')
   found=[f for f in report['findings'] if f['issue_id']==iid]
   if len(found)!=1:raise ValueError('original_issue_not_unique')
   original=found[0];allowed=hashes(original);scope=item['scope_type']
   if scope not in {'url','template','unknown'}:raise ValueError('invalid_issue_scope')
   if scope=='url' and not original.get('url'):raise ValueError('report_level_issue_requires_broader_scope')
   dep=item.get('deployment');deployment_at=None
   if dep:
    text=proof(root,dep['source']);q=dep['quote']
    if not isinstance(q,str) or not q or q not in text or dep['at'] not in q:raise ValueError('deployment_time_not_bound')
    if moment(dep['at'])>moment(at):raise ValueError('deployment_in_future')
    deployment_at=dep['at']
   cases=item['cases']
   if not isinstance(cases,list) or not cases or not any(x.get('role')=='symptom' for x in cases):raise ValueError('symptom_case_required')
   cids=[x['id'] for x in cases]
   if len(set(cids))!=len(cids):raise ValueError('duplicate_case_id')
   new={'issue_id':iid,'original':original,'source_report':item['source_report'],'source_at':source_at,'scope_type':scope,'deployment_at':deployment_at,'deployment':dep,'cases':[],'engine_reports':[]}
   for case in cases:
    c=dict(case);c['url']=page(c['url'])
    if c['role'] not in {'symptom','control'} or c['device'] not in {'MOBILE','DESKTOP','UNKNOWN'} or c['js'] not in {'ENABLED','DISABLED','UNKNOWN'} or c['entry'] not in {'direct','internal','back'}:raise ValueError('invalid_case_environment')
    if type(c['repetitions']) is not int or not 1<=c['repetitions']<=100:raise ValueError('invalid_repetition_count')
    if c['role']=='symptom' and original.get('url') and c['url']!=page(original['url']):raise ValueError('symptom_url_differs_from_original')
    evaluate({},c['predicate']);c.update(baseline=None,after=[],gaps=[])
    if case.get('baseline'):
     try:
      if case['baseline']['source']['sha256'] not in allowed:raise ValueError('baseline_not_bound_to_original_issue')
      c['baseline']=snapshot(case['baseline'],case,root,at,max_age_hours,True)
      if source_at and moment(c['baseline']['captured_at'])>moment(source_at):raise ValueError('baseline_after_original_report')
     except (ValueError,TypeError,KeyError,OSError) as ex:c['baseline']=None;c['gaps'].append(str(ex))
    elif c['role']=='symptom':c['gaps'].append('failure_baseline_missing')
    seen=set()
    for ref in case['after']:
     try:
      cap=snapshot(ref,case,root,at,max_age_hours);identity=(cap['source']['sha256'],cap['captured_at'])
      if identity in seen:continue
      seen.add(identity);c['after'].append(cap)
     except (ValueError,TypeError,KeyError,OSError) as ex:c['gaps'].append(str(ex))
    new['cases'].append(c);gaps.extend({'issue_id':iid,'case_id':c['id'],'reason':v} for v in c['gaps'])
   for ref in item.get('engine_reports',[]):
    try:
     platform=ref['platform'];codes={'google':'014','bing':'015','yandex':'016'}
     if platform not in codes:raise ValueError('unknown_platform')
     data=decode(proof(root,ref['source']));no_secrets(data)
     if (data.get('skill_id') or data.get('skill'))!=codes[platform]:raise ValueError('platform_report_mismatch')
     if not fresh(data['at'],at,max_age_hours):raise ValueError('platform_report_stale_or_future')
     new['engine_reports'].append({'platform':platform,'source':ref['source'],'report':data})
    except (ValueError,TypeError,KeyError,OSError) as ex:gaps.append({'issue_id':iid,'reason':str(ex)})
   out.append(new)
  except (ValueError,TypeError,KeyError,OSError,AttributeError) as ex:gaps.append({'issue_id':iid,'reason':str(ex)})
 return {'run_kind':m['run_kind'],'issues':out,'gaps':gaps,'declared_issues':len(m['issues'])}
