"""Small, deterministic evidence helpers shared within 003."""
import math
import re
from datetime import datetime,timezone
from urllib.parse import urlsplit,urlunsplit

def moment(value):
    if not isinstance(value,str):raise ValueError('timestamp_required')
    normalized=re.sub(r'([+-]\d{2})(\d{2})$',r'\1:\2',value.replace('Z','+00:00').replace(',','.'))
    # Python 3.10 requires 3/6 fractional digits; preserve microseconds on all versions.
    normalized=re.sub(r'\.(\d+)(?=[+-]|$)',lambda m:'.'+m[1].ljust(6,'0')[:6],normalized)
    try:dt=datetime.fromisoformat(normalized)
    except ValueError as e:raise ValueError('invalid_timestamp') from e
    if dt.tzinfo is None:raise ValueError('timestamp_requires_timezone')
    return dt.astimezone(timezone.utc)

def fresh(value,at,hours):
    if not math.isfinite(hours) or hours<=0:raise ValueError('invalid_freshness_window')
    try:delta=(moment(at)-moment(value)).total_seconds()
    except ValueError:return False
    return 0<=delta<=hours*3600

def header_pairs(headers):
    if isinstance(headers,dict):headers=list(headers.items())
    if not isinstance(headers,list):raise ValueError('headers_must_be_object_or_pairs')
    result=[]
    for row in headers:
        if not isinstance(row,(tuple,list)) or len(row)!=2 or not all(isinstance(v,str) for v in row):
            raise ValueError('invalid_header_pair')
        result.append((row[0].lower(),row[1]))
    return result

def url_id(value):
    if not isinstance(value,str) or any(c.isspace() or ord(c)<32 for c in value):raise ValueError('invalid_url')
    p=urlsplit(value)
    if p.scheme.lower() not in {'http','https'} or not p.hostname or p.username is not None or p.password is not None:
        raise ValueError('invalid_url')
    if not p.netloc.isascii():raise ValueError('Unicode hostnames are not supported; use explicit ASCII punycode A-labels')
    host=p.hostname.lower()
    if ':' in host:host='['+host+']'
    if p.port is not None and p.port!=(443 if p.scheme.lower()=='https' else 80):host+=':'+str(p.port)
    return urlunsplit((p.scheme.lower(),host,p.path or '/',p.query,''))

def origin(url):
    p=urlsplit(url_id(url));return p.scheme+'://'+p.netloc
