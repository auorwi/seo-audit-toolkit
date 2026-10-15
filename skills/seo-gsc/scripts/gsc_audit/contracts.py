"""Typed GSC observations; absence and API history are never live-site proof."""

import sys as _site_sys
from pathlib import Path as _SitePath
_site_dependency=_SitePath(__file__).resolve().parents[3]/'seo-crawlability/scripts'
if str(_site_dependency) not in _site_sys.path:_site_sys.path.insert(0,str(_site_dependency))
from crawlability.site import get_profile,site_host,site_origin,allowed_hosts,in_scope,require_url,brand_name,business_profile
import math,sys
from copy import deepcopy
from pathlib import Path
from datetime import date
from urllib.parse import urlsplit
p=Path(__file__).resolve().parents[3]/'seo-crawlability'/'scripts'
if not p.is_dir():raise ImportError('Requires sibling seo-crawlability')
if str(p) not in sys.path:sys.path.insert(0,str(p))
from crawlability.common import url_id,moment,fresh


def object_(v):
    if not isinstance(v,dict):raise ValueError('object_required')
    if 'error' in v:raise ValueError('api_error_response')
    return v

def array(v):
    if not isinstance(v,list):raise ValueError('array_required')
    return v

def text(v):
    if not isinstance(v,str):raise ValueError('string_required')
    return v

def integer(v,*,strings=False):
    if strings and isinstance(v,str) and v.isascii() and v.isdigit():v=int(v)
    if type(v) is not int or v<0:raise ValueError('nonnegative_integer_required')
    return v

def boolean(v):
    if type(v) is not bool:raise ValueError('boolean_required')
    return v

def property_id(v):
    text(v)
    if v.startswith('sc-domain:'):
        raw_host=v[len('sc-domain:'):]
        if not raw_host.isascii():raise ValueError('Unicode hostnames are not supported; use explicit ASCII punycode A-labels')
        host=raw_host.lower()
        if host not in allowed_hosts() or any(x in host for x in '/?#@:') or any(not q or not all(c.isascii() and (c.isalnum() or c=='-') for c in q) for q in host.split('.')):raise ValueError('invalid_site_property')
        return 'sc-domain:'+host
    norm=url_id(v);parts=urlsplit(norm)
    if not in_scope(norm) or parts.query or '#' in v or '?' in v or not parts.path.endswith('/'):raise ValueError('invalid_url_prefix_property')
    return norm

def belongs(prop,url):
    prop=property_id(prop);url=url_id(url);p=urlsplit(url)
    if prop.startswith('sc-domain:'):
        d=prop[len('sc-domain:'):];return p.hostname==d or p.hostname.endswith('.'+d)
    return url.startswith(prop)

ENUMS={
 'verdict':{'VERDICT_UNSPECIFIED','PASS','FAIL','NEUTRAL','PARTIAL'},
 'robotsTxtState':{'ROBOTS_TXT_STATE_UNSPECIFIED','ALLOWED','DISALLOWED'},
 'indexingState':{'INDEXING_STATE_UNSPECIFIED','INDEXING_ALLOWED','BLOCKED_BY_META_TAG','BLOCKED_BY_HTTP_HEADER','BLOCKED_BY_ROBOTS_TXT'},
 'pageFetchState':{'PAGE_FETCH_STATE_UNSPECIFIED','SUCCESSFUL','SOFT_404','BLOCKED_ROBOTS_TXT','NOT_FOUND','ACCESS_DENIED','SERVER_ERROR','REDIRECT_ERROR','ACCESS_FORBIDDEN','BLOCKED_4XX','INTERNAL_CRAWL_ERROR','INVALID_URL'},
 'crawledAs':{'CRAWLING_USER_AGENT_UNSPECIFIED','DESKTOP','MOBILE'}}

def inspection(request,body):
    object_(request);body=object_(body);prop=property_id(request['siteUrl']);u=url_id(request['inspectionUrl'])
    if not belongs(prop,u):raise ValueError('inspection_out_of_property')
    raw=object_(body['inspectionResult']);idx=object_(raw.get('indexStatusResult',{}));gaps=[];out={}
    if not idx:gaps.append('index_status_unavailable')
    for field,allowed in ENUMS.items():
        v=idx.get(field)
        if v is not None:
            text(v)
            if v not in allowed:gaps.append('unknown_enum:'+field)
            if v in {'PARTIAL','BLOCKED_BY_ROBOTS_TXT'}:gaps.append('reserved_enum:'+field)
        out[field]=v
    for field in ['coverageState','lastCrawlTime','googleCanonical','userCanonical']:
        v=idx.get(field)
        if v is not None:
            text(v)
            if field=='lastCrawlTime':moment(v)
            elif field.endswith('Canonical'):url_id(v)
        out[field]=v
    for field in ['sitemap','referringUrls']:
        v=idx.get(field)
        if v is not None:
            for u2 in array(v):url_id(u2)
        out[field]=v
    if out['verdict'] in {None,'VERDICT_UNSPECIFIED','PARTIAL'}:gaps.append('index_verdict_unavailable')
    rich=raw.get('richResultsResult')
    if rich is not None:
        object_(rich)
        if 'verdict' in rich:text(rich['verdict'])
        for group in array(rich.get('detectedItems',[])):
            object_(group);text(group['richResultType'])
            for item in array(group.get('items',[])):
                object_(item)
                for issue in array(item.get('issues',[])):
                    object_(issue);text(issue['issueMessage']);text(issue['severity'])
    return {'property':prop,'url':u,'kind':'indexed_snapshot','live_test':False,'index':out,'rich_results':deepcopy(rich),
            'sitemap_list_exhaustive':False,'deprecated_mobile_usability_present':'mobileUsabilityResult' in raw,'cwv':None,'gaps':gaps}

DIMENSIONS={'country','device','page','query','searchAppearance','date','hour'}

def analytics(request,body):
    request=object_(request);body=object_(body)
    start=date.fromisoformat(text(request['startDate']));end=date.fromisoformat(text(request['endDate']))
    if start>end:raise ValueError('reversed_date_window')
    dims=array(request.get('dimensions',[]))
    if not all(isinstance(d,str) and d in DIMENSIONS for d in dims) or len(dims)!=len(set(dims)):raise ValueError('invalid_dimensions')
    limit=integer(request.get('rowLimit',1000));offset=integer(request.get('startRow',0))
    if not 1<=limit<=25000:raise ValueError('invalid_row_limit')
    state=text(request.get('dataState','final')).lower();kind=request.get('type','web');agg=request.get('aggregationType','auto')
    if state not in {'final','all','hourly_all'} or kind not in {'web','image','video','news','discover','googleNews'} or agg not in {'auto','byPage','byProperty','byNewsShowcasePanel'}:raise ValueError('invalid_query_mode')
    filters=array(request.get('dimensionFilterGroups',[]));haspage='page' in dims
    for group in filters:
        object_(group)
        if group.get('groupType','and')!='and':raise ValueError('unsupported_filter_group')
        for f in array(group.get('filters',[])):
            object_(f)
            if f.get('dimension') not in DIMENSIONS or f.get('operator','equals') not in {'contains','equals','notContains','notEquals','includingRegex','excludingRegex'} or len(text(f['expression']))>4096:raise ValueError('invalid_filter')
            haspage=haspage or f['dimension']=='page'
    if agg=='byProperty' and haspage:raise ValueError('page_cannot_aggregate_by_property')
    rows=[]
    if len(array(body.get('rows',[])))>limit:raise ValueError('response_exceeds_requested_limit')
    for row in array(body.get('rows',[])):
        object_(row);keys=array(row.get('keys',[]))
        if len(keys)!=len(dims) or not all(isinstance(k,str) for k in keys):raise ValueError('dimension_key_mismatch')
        values={}
        for k in ['clicks','impressions','ctr','position']:
            n=row[k]
            if type(n) not in {int,float} or not math.isfinite(n) or n<0 or (k=='ctr' and n>1):raise ValueError('invalid_metric:'+k)
            values[k]=n
        if values['clicks']>values['impressions']:raise ValueError('clicks_exceed_impressions')
        if any(values[k]>2**53-1 for k in ['clicks','impressions']):raise ValueError('counts_exceed_supported_exact_numeric_range')
        rows.append({'dimensions':dict(zip(dims,keys)),**values})
    meta=object_(body.get('metadata',{}))
    if 'first_incomplete_date' in meta:date.fromisoformat(text(meta['first_incomplete_date']))
    if 'first_incomplete_hour' in meta:text(meta['first_incomplete_hour'])
    return {'kind':'search_analytics','query':deepcopy(request),'rows':rows,'timezone':'America/Los_Angeles','exhaustive':False,'indexing_evidence':False,
            'response_aggregation':body.get('responseAggregationType'),'metadata':deepcopy(meta),'may_include_incomplete_data':state!='final' or bool(meta),
            'start_row':offset,'row_limit':limit,'next_start_row_candidate':offset+len(rows) if len(rows)==limit else None,
            'gaps':['top_rows_only_not_inventory']}

def sitemaps(body):
    body=object_(body);entries=[];gaps=[]
    for raw in array(body.get('sitemap',[])):
        raw=object_(raw);r={'path':url_id(raw['path']),'contents':[]}
        for field in ['errors','warnings']:
            r[field]=integer(raw[field],strings=True) if field in raw else None
        for field in ['isPending','isSitemapsIndex']:
            r[field]=boolean(raw[field]) if field in raw else None
        for field in ['type','lastDownloaded','lastSubmitted']:
            r[field]=text(raw[field]) if field in raw else None
        for content in array(raw.get('contents',[])):
            object_(content);row={'type':text(content['type']),'submitted':integer(content['submitted'],strings=True) if 'submitted' in content else None}
            r['contents'].append(row)
            if 'indexed' in content:gaps.append('deprecated_indexed_ignored')
        entries.append(r)
    return {'kind':'submitted_sitemaps','entries':entries,'full_site_inventory':False,'gaps':sorted(set(gaps))}
