"""Bounded, hashed source ingestion. Invalid evidence is quarantined with a gap."""
import json,hashlib,math,re
from collections import Counter
from pathlib import Path
from datetime import date
from urllib.parse import urlsplit,parse_qs
from .contracts import object_,array,text,integer,property_id,belongs,url_id,moment,fresh,inspection,analytics,sitemaps,ENUMS

REPORTS={'page_indexing','sitemaps','rich_results','cwv','video_indexing','https','manual_actions','security','performance','url_inspection','live_test'}
DEVICES={'MOBILE','DESKTOP','UNKNOWN'}

def read_proof(root,ref):
    object_(ref);raw=text(ref['path']);p=(root/raw).resolve()
    if not p.is_relative_to(root.resolve()) or Path(raw).is_absolute():raise ValueError('proof_outside_root')
    if p.stat().st_size>8*1024*1024:raise ValueError('proof_too_large')
    b=p.read_bytes();sha=hashlib.sha256(b).hexdigest()
    if sha!=ref['sha256']:raise ValueError('sha256_mismatch')
    return b

def decode(b):
    def invalid(v):raise ValueError('nonfinite_json_number')
    def pairs(rows):
        out={}
        for k,v in rows:
            if k in out:raise ValueError('duplicate_json_key')
            out[k]=v
        return out
    return json.loads(b,parse_constant=invalid,object_pairs_hook=pairs)

def normalized(s):return ' '.join(text(s).split())

def quoted_urls(value):
    found=set()
    for token in re.findall(r"https?://[^\s<>\"']+",text(value),flags=re.IGNORECASE):
        try:found.add(url_id(token))
        except ValueError:continue
    return found

def report_date_value(value,format_):
    value=normalized(value)
    if format_=='YYYY-MM-DD':
        if not re.fullmatch(r'\d{4}-\d{2}-\d{2}',value):raise ValueError('date_quote_format_mismatch')
        return date.fromisoformat(value)
    if format_ in {'M/D/YY','D/M/YY','M/D/YYYY','D/M/YYYY','YYYY/M/D'}:
        parts=value.split('/')
        if len(parts)!=3 or not all(p.isascii() and p.isdigit() for p in parts):raise ValueError('date_quote_format_mismatch')
        first,second,third=map(int,parts)
        if format_=='YYYY/M/D':
            if len(parts[0])!=4:raise ValueError('date_quote_format_mismatch')
            return date(first,second,third)
        if len(parts[0])>2 or len(parts[1])>2 or len(parts[2])!=(2 if format_.endswith('/YY') else 4):raise ValueError('date_quote_format_mismatch')
        year=2000+third if format_.endswith('/YY') else third
        return date(year,first,second) if format_.startswith('M/') else date(year,second,first)
    if format_=='MMM D, YYYY':
        match=re.fullmatch(r'([A-Za-z]+) (\d{1,2}), (\d{4})',value)
        months={'jan':1,'january':1,'feb':2,'february':2,'mar':3,'march':3,'apr':4,'april':4,'may':5,'jun':6,'june':6,'jul':7,'july':7,'aug':8,'august':8,'sep':9,'sept':9,'september':9,'oct':10,'october':10,'nov':11,'november':11,'dec':12,'december':12}
        if not match or match[1].lower() not in months:raise ValueError('date_quote_format_mismatch')
        return date(int(match[3]),months[match[1].lower()],int(match[2]))
    if format_=='YYYY年M月D日':
        match=re.fullmatch(r'(\d{4})年(\d{1,2})月(\d{1,2})日',value)
        if not match:raise ValueError('date_quote_format_mismatch')
        return date(*map(int,match.groups()))
    raise ValueError('unsupported_date_quote_format')

def ui_data(raw,root):
    report=raw['report']
    if report not in REPORTS:raise ValueError('unsupported_ui_report')
    if not text(raw['reviewer']).strip():raise ValueError('reviewer_required')
    prop=property_id(raw['property']);source=object_(raw['source']);p=urlsplit(url_id(source['url']))
    if p.scheme!='https' or p.hostname!='search.google.com' or '/search-console' not in p.path:raise ValueError('not_gsc_source')
    q=parse_qs(p.query).get('resource_id')
    if q is not None and (len(q)!=1 or property_id(q[0])!=prop):raise ValueError('source_property_mismatch')
    body=read_proof(root,source).decode('utf-8');norm=normalized(body);source_urls=quoted_urls(norm)
    def quote(field):
        q=normalized(raw[field])
        if not q or q not in norm:raise ValueError('source_quote_unsubstantiated:'+field)
        return q
    pq=quote('property_quote')
    if prop.startswith('sc-domain:'):
        if not re.search(r'(?<![\w.-])'+re.escape(pq)+r'(?![\w.-])',norm):raise ValueError('property_quote_mismatch')
        if not all(re.search(r'(?<![\w.-])'+re.escape(prop.removeprefix('sc-domain:'))+r'(?![\w.-])',v) for v in [pq,norm]):raise ValueError('property_quote_mismatch')
    elif prop not in quoted_urls(pq) or prop not in source_urls:raise ValueError('property_quote_mismatch')
    d=raw.get('report_date')
    if d is not None:
        if date.fromisoformat(text(d))>moment(raw['captured_at']).date():raise ValueError('future_report_date')
        if date.fromisoformat(d)!=report_date_value(quote('report_date_quote'),raw.get('report_date_format','YYYY-MM-DD')):raise ValueError('date_quote_mismatch')
    filters=object_(raw['filters']);unit=raw['count_unit']
    if unit not in {'pages','items','groups','sitemaps','issues','not_applicable'}:raise ValueError('count_unit_required')
    total=raw.get('reported_total')
    if total is not None:
        integer(total);n=quote('total_quote').replace(',','').replace(' ','')
        if not n.isascii() or not n.isdigit() or int(n)!=total:raise ValueError('total_quote_mismatch')
    rows=[]
    for row in array(raw.get('rows',[])):
        row=object_(row);reason=text(row['reason_key'])
        if not re.fullmatch(r'[a-z][a-z0-9_]{0,79}',reason):raise ValueError('invalid_reason_key')
        label=text(row['reason_label']);citation=normalized(row['quote'])
        if not label.strip() or not citation or citation not in norm or normalized(label) not in citation:raise ValueError('row_quote_unsubstantiated')
        u=row.get('url')
        if u is not None:
            u=url_id(u);uq=normalized(row['url_quote'])
            if not belongs(prop,u) or not uq or uq not in norm or u not in quoted_urls(uq) or u not in source_urls:raise ValueError('url_quote_unsubstantiated')
        device=row.get('device','UNKNOWN')
        if device not in DEVICES:raise ValueError('invalid_device')
        rows.append({**row,'url':u,'device':device})
    if unit=='pages' and total is not None and total<len({r['url'] for r in rows if r['url']}):raise ValueError('examples_exceed_reported_page_total')
    inspected=None
    if 'inspection' in raw:
        if report!='url_inspection':raise ValueError('indexed_fields_only_in_inspection_report')
        item=object_(raw['inspection']);u=url_id(item['url']);uq=normalized(item['url_quote'])
        if not uq or uq not in norm or u not in quoted_urls(uq) or u not in source_urls or not belongs(prop,u):raise ValueError('inspection_url_quote_unsubstantiated')
        fields=object_(item['fields']);idx={}
        for key,binding in fields.items():
            if key not in set(ENUMS)|{'coverageState','lastCrawlTime','googleCanonical','userCanonical','sitemap','referringUrls'}:raise ValueError('unsupported_inspection_field')
            object_(binding);q=normalized(binding['quote'])
            if not q or q not in norm:raise ValueError('inspection_field_quote_unsubstantiated')
            value=binding['value']
            if key in {'googleCanonical','userCanonical'} and value is not None and (url_id(value) not in quoted_urls(q) or url_id(value) not in source_urls):raise ValueError('inspection_url_value_unsubstantiated')
            if key in {'sitemap','referringUrls'} and value is not None:
                if any(url_id(v) not in quoted_urls(q) or url_id(v) not in source_urls for v in array(value)):raise ValueError('inspection_url_list_unsubstantiated')
            idx[key]=value
        inspected=inspection({'siteUrl':prop,'inspectionUrl':u},{'inspectionResult':{'indexStatusResult':idx}})
        if idx.get('lastCrawlTime') and moment(idx['lastCrawlTime'])>moment(raw['captured_at']):raise ValueError('lastcrawl_after_capture')
        inspected['field_bindings']=fields
    return {'kind':'live_test' if report=='live_test' else 'ui_report','report':report,'report_date':d,'report_date_quote':raw.get('report_date_quote'),'report_date_format':raw.get('report_date_format','YYYY-MM-DD'),'filters':filters,'count_unit':unit,'reported_total':total,
            'rows':rows,'observed_url_examples':len({r['url'] for r in rows if r['url']}),'examples_exhaustive':False,'source':source,'reviewer':raw['reviewer'],'inspection':inspected,
            'gaps':(['report_data_date_unavailable'] if d is None and report not in {'url_inspection','live_test'} else [])+(inspected['gaps'] if inspected else [])}

def load_manifest(path,*,at,max_age_hours=24):
    moment(at);fresh(at,at,max_age_hours);path=Path(path);root=path.parent.resolve()
    if path.stat().st_size>8*1024*1024:raise ValueError('manifest_too_large')
    m=object_(decode(path.read_bytes()))
    if type(m.get('schema_version')) is not int or m['schema_version']!=1:raise ValueError('unsupported_schema')
    run_kind=m.get('run_kind','audit')
    if run_kind not in {'audit','controlled_fixture','historical_replay'}:raise ValueError('invalid_run_kind')
    prop=property_id(m['property']);scope=[];seen=set()
    for s in array(m['scope']):
        object_(s);u=url_id(s['url']);device=s['device']
        if not belongs(prop,u) or device not in DEVICES:raise ValueError('invalid_scope')
        if (u,device) not in seen:scope.append({'url':u,'device':device});seen.add((u,device))
    refs=array(m['evidence']);ids=Counter(text(object_(r)['id']) for r in refs);obs=[];gaps=[];hashes=set()
    for ref in refs:
        eid=ref['id']
        try:
            if not eid or ids[eid]>1:raise ValueError('duplicate_evidence_id')
            data=read_proof(root,ref)
            if ref['sha256'] in hashes:raise ValueError('duplicate_evidence_content')
            raw=object_(decode(data));kind=raw['kind']
            if kind!=ref['kind']:raise ValueError('evidence_kind_mismatch')
            if property_id(raw['property'])!=prop:raise ValueError('property_mismatch')
            captured=text(raw['captured_at'])
            if not fresh(captured,at,max_age_hours):raise ValueError('stale_or_future_capture')
            if kind in {'inspection_api','analytics_api','sitemaps_api'}:
                if type(raw['http_status']) is not int or raw['http_status']!=200:raise ValueError('api_http_error')
                req=object_(raw['request'])
                if property_id(req['siteUrl'])!=prop:raise ValueError('request_property_mismatch')
                if kind=='inspection_api':
                    parsed=inspection(req,raw['response']);last=parsed['index']['lastCrawlTime']
                    if last and moment(last)>moment(captured):raise ValueError('lastcrawl_after_capture')
                elif kind=='analytics_api':parsed=analytics(req,raw['response'])
                else:parsed=sitemaps(raw['response'])
            elif kind=='gsc_ui':parsed=ui_data(raw,root)
            elif kind=='live_http':
                u=url_id(raw['url']);final=url_id(raw['final_url']);status=raw['status'];device=raw['device']
                if not belongs(prop,u) or not belongs(prop,final):raise ValueError('live_url_out_of_property')
                if raw['method']!='GET' or type(status) is not int or not 100<=status<=599 or device not in DEVICES or not text(raw['source_description']).strip():raise ValueError('invalid_live_observation')
                parsed={'kind':'live_http','url':u,'final_url':final,'device':device,'status':status,'source_description':raw['source_description'],'indexing_evidence':False}
            else:raise ValueError('unsupported_evidence_kind')
            hashes.add(ref['sha256']);obs.append({'id':eid,'kind':kind,'property':prop,'captured_at':captured,'proof':dict(ref),'data':parsed})
        except (ValueError,KeyError,TypeError,OSError,UnicodeError,OverflowError) as e:
            gaps.append({'evidence_id':eid,'reason':str(e)})
    comparisons=array(m.get('comparisons',[]))
    for c in comparisons:object_(c);text(c['before']);text(c['after'])
    return {'run_kind':run_kind,'property':prop,'scope':scope,'observations':obs,'gaps':gaps,'comparisons':comparisons,'manifest_sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
