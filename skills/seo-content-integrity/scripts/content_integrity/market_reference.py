"""Interpret only explicit states from a recorded official spot-symbol response."""

import sys as _site_sys
from pathlib import Path as _SitePath
_site_dependency=_SitePath(__file__).resolve().parents[3]/'seo-crawlability/scripts'
if str(_site_dependency) not in _site_sys.path:_site_sys.path.insert(0,str(_site_dependency))
from crawlability.site import get_profile,site_host,site_origin,allowed_hosts,in_scope,require_url,brand_name,business_profile
import json
from urllib.parse import urlsplit
from .shared import fresh,moment

def review_response(row, *, symbol, at, max_age_hours=24):
    moment(at);result={'state':'unknown','market':'spot','symbol':symbol,'all_products_verified':False,'reference':row}
    if business_profile()!='bingx':return {**result,'reason':'market_reference_extension_not_configured'}
    try:
        u=urlsplit(row['url'])
        if u.scheme!='https' or u.hostname!='open-api.bingx.com' or u.username or u.password or u.port or u.path!='/openApi/spot/v1/common/symbols':return {**result,'reason':'unsupported_reference_endpoint'}
        if row.get('method')!='GET' or row.get('source')!='actual public HTTP response' or row.get('status')!=200 or not fresh(row.get('captured_at'),at,max_age_hours):return {**result,'reason':'reference_not_current_successful_read'}
        data=json.loads(row['body'])
        if type(data.get('code')) is not int or data['code']!=0:return {**result,'reason':'api_error_or_unknown_code'}
        rows=data['data']['symbols']
        if rows is None:return {**result,'reason':'symbol_absent_not_proof_of_delisting'}
        matches=[r for r in rows if r.get('symbol')==symbol]
        if not matches:return {**result,'reason':'symbol_absent_not_proof_of_delisting'}
        states=[r.get('status') for r in matches]
        if any(type(s) is not int or s not in {0,1} for s in states) or len(set(states))!=1:return {**result,'reason':'ambiguous_symbol_status'}
        return {**result,'state':'active' if states[0]==1 else 'inactive','observed_symbol_rows':matches}
    except (ValueError,KeyError,TypeError,AttributeError):return {**result,'reason':'invalid_reference_response'}
