"""Traceable robots matching for normal Googlebot, Bingbot and YandexBot."""
import re
from urllib.parse import quote,urlsplit

UNRESERVED=set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-._~')

def _origin(url):
    p=urlsplit(url)
    if p.scheme.lower() not in {'http','https'} or not p.hostname or p.username is not None:
        raise ValueError('invalid_http_origin')
    if not p.netloc.isascii():raise ValueError('Unicode hostnames are not supported; use explicit ASCII punycode A-labels')
    host=p.hostname.lower()
    return p.scheme.lower(),host,p.port or (443 if p.scheme.lower()=='https' else 80)

def _normalized_path(value,pattern=False):
    # Decode only unreserved octets; retain reserved separators and UTF-8 escapes.
    def octet(match):
        char=chr(int(match.group(1),16))
        return char if char in UNRESERVED else '%'+match.group(1).upper()
    value=re.sub(r'%([0-9a-fA-F]{2})',octet,value)
    return quote(value,safe="/%?:@!&'()+,;=-._~"+('*' if pattern else ''))

def _matches(pattern,target,end):
    # Greedy wildcard matching avoids exponential regular-expression backtracking.
    pattern += '' if end else '*'
    p=t=0; star=-1;mark=0
    while t<len(target):
        if p<len(pattern) and pattern[p]!='*' and pattern[p]==target[t]:p+=1;t+=1
        elif p<len(pattern) and pattern[p]=='*':star=p;mark=t;p+=1
        elif star!=-1:mark+=1;t=mark;p=star+1
        else:return False
    while p<len(pattern) and pattern[p]=='*':p+=1
    return p==len(pattern)

def _agent_token(value):
    if value.strip()=='*':return '*'
    match=re.match(r'[a-z_-]+',value.strip().lower())
    return match.group(0) if match else ''

def evaluate_rules(body,url,agent,robots_url):
    result={'allowed':None,'reason':'unknown','selected_agents':[],'matched_rules':[],'warnings':[],'agent':agent,'robots_url':robots_url}
    try:
        p=urlsplit(robots_url)
        if p.path!='/robots.txt' or p.query or p.fragment:
            result['reason']='robots_location_invalid';return result
        if _origin(url)!=_origin(robots_url):
            result['reason']='robots_origin_mismatch';return result
    except (ValueError,UnicodeError):
        result['reason']='invalid_url';return result
    product=_agent_token(agent)
    if product not in {'googlebot','bingbot','yandexbot'}:
        result['reason']='unsupported_agent_profile';return result
    if product=='googlebot' and len(body)>512000:
        body=body[:512000];result['warnings'].append('robots_size_truncated')
    try:text=body.decode('utf-8-sig')
    except UnicodeDecodeError:
        text=body.decode('utf-8-sig',errors='replace');result['warnings'].append('robots_encoding_invalid')
    if re.match(r'\s*(?:<!doctype\s+html|<html\b)',text,re.I):
        result['warnings'].append('robots_html_response')
    groups=[];agents=[];rules=[];had_rules=False
    for number,line in enumerate(text.splitlines(),1):
        line=line.split('#',1)[0].strip()
        if ':' not in line:continue
        field,value=[v.strip() for v in line.split(':',1)];field=field.lower()
        if field=='user-agent':
            if had_rules:
                groups.append((agents,rules));agents=[];rules=[];had_rules=False
            token=_agent_token(value)
            if token:agents.append(token)
        elif field in {'allow','disallow'} and agents:
            had_rules=True
            if not value:continue
            if not value.startswith('/'):
                result['warnings'].append('robots_rule_path_invalid');continue
            end=value.endswith('$')
            normalized=_normalized_path(value[:-1] if end else value,pattern=True)
            rules.append({'line':number,'directive':field,'pattern':value,'normalized':normalized,'end':end,'specificity':len(normalized)+(1 if end else 0)})
        elif field=='noindex':result['warnings'].append('robots_noindex_unsupported')
    if agents:groups.append((agents,rules))
    best=-1;selected=[];chosen=[]
    for names,rules in groups:
        matching=[name for name in names if name in {'*',product} or (product=='yandexbot' and name=='yandex')]
        if not matching:continue
        weight=max(0 if name=='*' else len(name) for name in matching)
        if weight>best:best=weight;selected=list(rules);chosen=[name for name in matching if (0 if name=='*' else len(name))==weight]
        elif weight==best:selected.extend(rules);chosen.extend(name for name in matching if (0 if name=='*' else len(name))==weight)
    target=urlsplit(url);target=_normalized_path((target.path or '/')+('?' + target.query if target.query else ''))
    matched=[r for r in selected if _matches(r['normalized'],target,r['end'])]
    longest=max((r['specificity'] for r in matched),default=-1)
    matched=[r for r in matched if r['specificity']==longest]
    result.update({'allowed':any(r['directive']=='allow' for r in matched) if matched else True,
        'reason':'matched_rules' if matched else 'no_matching_restriction','selected_agents':sorted(set(chosen)),
        'matched_rules':[{k:r[k] for k in ('line','directive','pattern','specificity')} for r in matched],
        'warnings':sorted(set(result['warnings']))})
    return result
