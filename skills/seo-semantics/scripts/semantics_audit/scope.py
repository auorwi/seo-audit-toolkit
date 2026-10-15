"""Freeze the exact announced URL list; never infer a sample from a full request."""

import sys as _site_sys
from pathlib import Path as _SitePath
_site_dependency=_SitePath(__file__).resolve().parents[3]/'seo-crawlability/scripts'
if str(_site_dependency) not in _site_sys.path:_site_sys.path.insert(0,str(_site_dependency))
from crawlability.site import get_profile,site_host,site_origin,allowed_hosts,in_scope,require_url,brand_name,business_profile
import hashlib
import json
from urllib.parse import urlsplit
from .shared import moment, url_id

# Hosts are resolved from the explicit site profile on every call.

def public_url(value):
    url=url_id(value);p=urlsplit(url)
    if not in_scope(url):
        raise ValueError('unsupported_public_scope_url: '+value)
    return url

def fingerprint(plan):
    payload={k:v for k,v in plan.items() if k!='scope_id'}
    return hashlib.sha256(json.dumps(payload,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def build_plan(rows,*,mode,source,at,urls=None,ids=None):
    moment(at)
    if mode not in {'single','subset','all'}:raise ValueError('scope_mode_required')
    if not isinstance(rows,list):raise ValueError('scope_input_must_be_array')
    urls=[public_url(u) for u in urls or []];ids=ids or []
    if mode=='all' and (urls or ids):raise ValueError('all_cannot_have_subset_filters')
    if mode in {'single','subset'} and not (urls or ids):raise ValueError('explicit_selection_required')
    available=[];excluded=[]
    for value in rows:
        row={'url':value} if isinstance(value,str) else dict(value)
        row['url']=public_url(row['url'])
        if row.get('kind','page')!='page':
            excluded.append({**row,'reason':'technical_file_not_page'});continue
        available.append(row)
    known_ids={r.get('id') for r in available}
    if any(i not in known_ids for i in ids):raise ValueError('unknown_selected_id')
    selected=available if mode=='all' else [r for r in available if r.get('id') in ids or r['url'] in urls]
    if mode!='all':
        found={r['url'] for r in selected}
        selected += [{'url':u,'page_type':'用户指定页面'} for u in urls if u not in found]
        excluded += [{**r,'reason':'not_selected'} for r in available if r['url'] not in {v['url'] for v in selected}]
    targets=[];seen=set()
    for row in selected:
        if row['url'] in seen:continue
        seen.add(row['url'])
        required=row.get('required_tools',['nu','axe'])
        if not isinstance(required,list) or not required or not set(required)<={'nu','axe'}:raise ValueError('invalid_required_tools')
        targets.append({**row,'page_type':row.get('page_type') or row.get('template') or '待识别',
                        'locale':row.get('locale') or '待识别','required_tools':required})
    if not targets or (mode=='single' and len(targets)!=1):raise ValueError('invalid_selected_page_count')
    plan={'schema_version':1,'mode':mode,'source':source,'created_at':at,'count':len(targets),
          'whole_site_claim':False,'targets':targets,'excluded':excluded}
    plan['scope_id']=fingerprint(plan)
    return plan

def validate_plan(plan):
    if not isinstance(plan,dict) or plan.get('schema_version')!=1 or plan.get('scope_id')!=fingerprint(plan):raise ValueError('scope_integrity_mismatch')
    if plan.get('mode') not in {'single','subset','all'} or plan.get('whole_site_claim') is not False:raise ValueError('invalid_scope_contract')
    rows=plan.get('targets');moment(plan.get('created_at'))
    if not isinstance(rows,list) or not rows or plan.get('count')!=len(rows):raise ValueError('scope_count_mismatch')
    urls=[public_url(r['url']) for r in rows]
    if len(set(urls))!=len(urls) or (plan['mode']=='single' and len(urls)!=1):raise ValueError('scope_identity_mismatch')
    return plan
