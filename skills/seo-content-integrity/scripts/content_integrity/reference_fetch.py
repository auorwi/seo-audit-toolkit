"""One bounded unauthenticated public spot-symbol GET; preserve failures verbatim."""

import sys as _site_sys
from pathlib import Path as _SitePath
_site_dependency=_SitePath(__file__).resolve().parents[3]/'seo-crawlability/scripts'
if str(_site_dependency) not in _site_sys.path:_site_sys.path.insert(0,str(_site_dependency))
from crawlability.site import get_profile,site_host,site_origin,allowed_hosts,in_scope,require_url,brand_name,business_profile
import re,time,uuid
from datetime import datetime,timezone
from urllib.request import Request,urlopen
from urllib.parse import urlencode
from urllib.error import HTTPError,URLError

def fetch(symbol):
    if business_profile()!='bingx':raise ValueError('bingx_business_profile_required')
    if not isinstance(symbol,str) or not re.fullmatch(r'[A-Z0-9]{1,40}-[A-Z0-9]{1,40}',symbol):raise ValueError('invalid_spot_symbol')
    url='https://open-api.bingx.com/openApi/spot/v1/common/symbols?'+urlencode({'symbol':symbol,'timestamp':int(time.time()*1000)})
    row={'reference_id':'spot-'+str(uuid.uuid4()),'url':url,'method':'GET','source':'actual public HTTP response','status':None,'body':'','symbol_requested':symbol}
    request=Request(url,headers={'Accept':'application/json','User-Agent':'BingX-SEO-content-integrity/1.0'},method='GET')
    try:
        try:response=urlopen(request,timeout=20)
        except HTTPError as e:response=e
        with response:
            raw=response.read(8_000_001);row['status']=response.code
            if len(raw)>8_000_000:row['error']='response_size_limit';row['body_truncated']=True;raw=raw[:8_000_000]
            row['body']=raw.decode('utf-8',errors='replace')
            row['headers']={k:v for k,v in response.headers.items() if k.lower() in {'content-type','date','retry-after'}}
    except (URLError,TimeoutError,OSError) as e:row['error']=str(e)
    row['captured_at']=datetime.now(timezone.utc).isoformat()
    return row
