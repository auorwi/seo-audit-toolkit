"""Explicit, reloadable site policy. Scope checks are offline; live DNS needs validation too."""
import ipaddress
import json
import os
import re
from pathlib import Path
from urllib.parse import parse_qsl, urlsplit

SENSITIVE = {'access_token','refresh_token','token','id_token','password','passwd','secret','api_key','apikey','session','sessionid','authorization','email','auth_code','client_secret','cookie','set-cookie','appsecret'}

def _host(value):
    if not isinstance(value,str) or not value or value != value.strip() or any(c in value for c in '/?#@*\\') or value.endswith('.'):
        raise ValueError('invalid_profile_hostname')
    if not value.isascii():raise ValueError('Unicode hostnames are not supported; use explicit ASCII punycode A-labels')
    try:
        ip=ipaddress.ip_address(value)
        return ip.compressed
    except ValueError:
        pass
    if re.fullmatch(r'[0-9.]+',value):raise ValueError('noncanonical_ip_literal')
    h=value.lower()
    if len(h)>253 or any(not re.fullmatch(r'[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?',v) for v in h.split('.')):
        raise ValueError('invalid_profile_hostname')
    return h

def _no_credentials(value):
    if isinstance(value,dict):
        for key,item in value.items():
            if str(key).lower().replace('-','_') in SENSITIVE:raise ValueError('credentials_not_allowed_in_profile')
            _no_credentials(item)
    elif isinstance(value,list):
        for item in value:_no_credentials(item)

def get_profile():
    name=os.environ.get('SEO_SITE_PROFILE')
    if not name:raise ValueError('SEO_SITE_PROFILE_required')
    try:p=json.loads(Path(name).expanduser().read_text(encoding='utf-8'))
    except (OSError,ValueError) as e:raise ValueError('invalid_site_profile') from e
    if not isinstance(p,dict):raise ValueError('invalid_site_profile')
    _no_credentials(p)
    p=dict(p);p['site']=_host(p.get('site'))
    hosts=p.get('allowed_hosts')
    if not isinstance(hosts,list) or not hosts:raise ValueError('profile_requires_allowed_hosts')
    p['allowed_hosts']=[_host(h) for h in hosts]
    if p['site'] not in p['allowed_hosts']:raise ValueError('site_must_be_allowed')
    if p.get('business_profile','generic') not in {'generic','bingx'}:raise ValueError('unknown_business_profile')
    if not isinstance(p.get('brand',''),str):raise ValueError('invalid_brand')
    if type(p.get('test_only_allow_loopback',False)) is not bool:raise ValueError('invalid_fixture_option')
    if p.get('test_only_allow_loopback') and (type(p.get('fixture_port')) is not int or not 1<=p['fixture_port']<=65535):raise ValueError('fixture_port_required')
    if type(p.get('allow_system_dns_alias',False)) is not bool:raise ValueError('invalid_dns_alias_option')
    if not isinstance(p.get('allowed_schemes',['http','https']),list) or not p.get('allowed_schemes',['http','https']) or not set(p.get('allowed_schemes',['http','https']))<={'http','https'}:raise ValueError('invalid_allowed_schemes')
    for key in ('seeds','sitemaps'):
        if not isinstance(p.get(key,[]),list) or any(not _allowed(u,p) for u in p.get(key,[])):raise ValueError('invalid_profile_'+key)
    excluded=p.get('excluded_path_patterns',[])
    if not isinstance(excluded,list) or any(not isinstance(v,str) for v in excluded):raise ValueError('invalid_excluded_path_patterns')
    try:
        for v in excluded:re.compile(v)
    except re.error:raise ValueError('invalid_excluded_path_patterns') from None
    if type(p.get('query_variants_per_path',2)) is not int or p.get('query_variants_per_path',2)<0:raise ValueError('invalid_query_variant_limit')
    return p

def _allowed(value,p):
    if not isinstance(value,str) or not value or re.search(r'[\x00-\x20\x7f\\]',value):return False
    try:
        u=urlsplit(value)
        if not u.netloc.isascii():return False
        host=_host(u.hostname)
        if u.scheme not in p.get('allowed_schemes',['http','https']) or u.username is not None or u.password is not None or host not in p['allowed_hosts']:return False
        fixture=False
        try:
            ip=ipaddress.ip_address(host);fixture=ip.is_loopback
            if not ip.is_global and not (fixture and p.get('test_only_allow_loopback')):return False
        except ValueError:
            fixture=host=='localhost'
            if (fixture or '.' not in host or host.endswith(('.localhost','.local','.internal','.test','.invalid'))) and not (fixture and p.get('test_only_allow_loopback')):return False
        port=u.port
        if fixture and p.get('test_only_allow_loopback'):
            if u.scheme!='http' or port!=p['fixture_port']:return False
        elif port not in (None,443 if u.scheme=='https' else 80):return False
        if any(k.lower() in SENSITIVE for k,_ in parse_qsl(u.query,keep_blank_values=True)):return False
        return True
    except (ValueError,TypeError,UnicodeError):return False

def site_host():return get_profile()['site']
def site_origin():
    p=get_profile();h=p['site'];h='['+h+']' if ':' in h else h
    if p.get('test_only_allow_loopback'):return 'http://'+h+':'+str(p['fixture_port'])
    return 'https://'+h
def allowed_hosts():return set(get_profile()['allowed_hosts'])
def in_scope(url):
    try:return _allowed(url,get_profile())
    except ValueError:return False
def require_url(url):
    if not in_scope(url):raise ValueError('outside_configured_site_or_unsafe_url')
    return url
def brand_name():
    p=get_profile();return p.get('brand') or p['site']
def business_profile():return get_profile().get('business_profile','generic')
