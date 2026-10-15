"""Bounded, read-only official field API collection; no fabricated responses."""

import sys as _site_sys
from pathlib import Path as _SitePath
_site_dependency=_SitePath(__file__).resolve().parents[3]/'seo-crawlability/scripts'
if str(_site_dependency) not in _site_sys.path:_site_sys.path.insert(0,str(_site_dependency))
from crawlability.site import get_profile,site_host,site_origin,allowed_hosts,in_scope,require_url,brand_name,business_profile
import json,hashlib
from pathlib import Path
from datetime import datetime,timezone
from urllib.request import Request,urlopen
from urllib.error import HTTPError,URLError
from urllib.parse import urlsplit,urlencode
from .shared import url_id,origin

def query_for(source,url,device,scope):
    url=url_id(url);p=urlsplit(url)
    if not in_scope(url):raise ValueError('unsupported_target')
    if device not in {'mobile','desktop'} or scope not in {'url','origin'}:raise ValueError('unsupported_field_scope')
    if source=='crux_api':return {scope:url if scope=='url' else origin(url),'formFactor':'PHONE' if device=='mobile' else 'DESKTOP'}
    if source=='psi_api' and scope=='url':return {'url':url,'strategy':device}
    raise ValueError('unsupported_field_source_or_scope')

def fetch_response(request,*,timeout=30):
    try:
        try:response=urlopen(request,timeout=timeout)
        except HTTPError as e:response=e
        with response:
            body=response.read(8_000_001)
            if len(body)>8_000_000:return {'status':response.status,'body':None,'error':'response_size_limit'}
            return {'status':response.status,'body':body,'headers':[(k,v) for k,v in response.headers.items() if k.lower() in {'content-type','date','retry-after'}]}
    except (URLError,TimeoutError,OSError) as e:return {'status':None,'body':None,'error':str(e)}

def collect_field(source,url,device,scope,output,*,key=None,timeout=30):
    query=query_for(source,url,device,scope);output=Path(output)
    if output.exists() and any(output.iterdir()):raise ValueError('output_directory_not_empty')
    output.mkdir(parents=True,exist_ok=True)
    def save(name,value,raw=False):
        b=value if raw else (json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode();(output/name).write_bytes(b);return {'path':name,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
    manifest={'schema_version':1,'field_records':[],'field_attempts':[]};meta={'source':source,'request':query,'observed_at':datetime.now(timezone.utc).isoformat(),'status':None}
    if source=='crux_api' and not key:meta.update(state='authorization_missing',reason='CrUX API key not configured; no HTTP request made')
    else:
        endpoint='https://chromeuxreport.googleapis.com/v1/records:queryRecord' if source=='crux_api' else 'https://www.googleapis.com/pagespeedonline/v5/runPagespeed';params={} if source=='crux_api' else query.copy()
        if key:params['key']=key
        target=endpoint+('?' +urlencode(params) if params else '');request=Request(target,data=json.dumps(query).encode() if source=='crux_api' else None,headers={'Accept':'application/json',**({'Content-Type':'application/json'} if source=='crux_api' else {})})
        response=fetch_response(request,timeout=timeout);meta.update(observed_at=datetime.now(timezone.utc).isoformat(),endpoint=endpoint,status=response['status'],headers=response.get('headers',[]))
        if response['body'] is None:meta.update(state='request_failed',reason=response.get('error','response_unavailable'))
        else:
            raw=response['body'];redacted=raw.replace(key.encode(),b'[REDACTED_API_KEY]') if key else raw
            meta.update(state='response_received',credential_redacted=redacted!=raw);body_proof=save('response.json',redacted,raw=True)
            manifest['field_records'].append({'source':source,'evidence':body_proof})
    if key and isinstance(meta.get('reason'),str):meta['reason']=meta['reason'].replace(key,'[REDACTED_API_KEY]')
    query_proof=save('query.json',meta);manifest['field_attempts']=[query_proof]
    for row in manifest['field_records']:row['query_evidence']=query_proof
    save('manifest.json',manifest);return meta
