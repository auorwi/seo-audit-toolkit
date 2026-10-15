"""Canonical and refresh declarations; no fetching or JavaScript execution."""
import re
from html.parser import HTMLParser
from urllib.parse import urljoin,urlsplit
from .shared import url_id,header_pairs

DISQUALIFY={'hreflang','lang','media','type'}

class Extractor(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.in_head=False;self.inert=0;self.links=[];self.bases=[];self.refreshes=[]

    def handle_starttag(self,tag,attrs):
        if tag=='head':self.in_head=True
        if tag=='body':self.in_head=False
        if tag=='template':self.inert+=1
        if self.inert:return
        a={}
        for key,value in attrs:a.setdefault(key,value)
        if tag=='base' and self.in_head and a.get('href') is not None:self.bases.append(a['href'])
        if tag=='link' and 'canonical' in (a.get('rel') or '').lower().split():
            self.links.append({'kind':'html','raw_target':a.get('href') or '',
                'attributes':a,'in_head':self.in_head,'line':self.getpos()[0]})
        if tag=='meta' and (a.get('http-equiv') or '').lower()=='refresh':
            self.refreshes.append({'kind':'meta_refresh','value':a.get('content') or '','line':self.getpos()[0]})

    def handle_endtag(self,tag):
        if tag=='head':self.in_head=False
        if tag=='template':self.inert=max(0,self.inert-1)

def split_header(value,separator):
    result=[];start=0;quote=False;angle=False;escaped=False
    for i,char in enumerate(value):
        if escaped:escaped=False;continue
        if char=='\\' and quote:escaped=True;continue
        if char=='"':quote=not quote
        if not quote:
            if char=='<':angle=True
            elif char=='>':angle=False
            elif char==separator and not angle:result.append(value[start:i].strip());start=i+1
    result.append(value[start:].strip());return result

def unquote(value):
    if len(value)>1 and value[0]==value[-1]=='"':return re.sub(r'\\(.)',r'\1',value[1:-1])
    return value

def link_rows(value):
    result=[]
    for part in split_header(value,','):
        match=re.match(r'^\s*<([^>]*)>(.*)$',part,re.S)
        if not match:continue
        attrs={}
        for param in split_header(match.group(2),';'):
            if '=' not in param:continue
            key,val=param.split('=',1);attrs.setdefault(key.strip().lower(),unquote(val.strip()))
        if 'canonical' in attrs.get('rel','').lower().split():
            result.append({'kind':'http_link','raw_target':match.group(1),'attributes':attrs,'line':None})
    return result

def parse(html,headers,url):
    url=url_id(url);parser=Extractor();parser.feed(html)
    pairs=header_pairs(headers);warnings=[];base=url
    if len(parser.bases)>1:warnings.append('multiple_base_elements')
    if parser.bases:
        try:base=url_id(urljoin(url,parser.bases[0]))
        except (ValueError,UnicodeError):warnings.append('invalid_base')
    declarations=parser.links
    for key,value in pairs:
        if key=='link':declarations.extend(link_rows(value))
        elif key=='refresh':parser.refreshes.append({'kind':'http_refresh','value':value,'line':None})
    targets=[]
    for row in declarations:
        row['usable']=True;row['target']=None
        if row['kind']=='html' and not row['in_head']:
            warnings.append('canonical_outside_head');row['usable']=False
        if DISQUALIFY.intersection(row['attributes']):
            warnings.append('canonical_alternate_attributes');row['usable']=False
        if row['kind']=='http_link' and 'anchor' in row['attributes']:
            warnings.append('link_anchor_context_unverified');row['usable']=False
        raw=row['raw_target'].strip()
        if not raw:
            warnings.append('canonical_empty_target');row['usable']=False;continue
        try:
            resolved=urljoin(base if row['kind']=='html' else url,raw)
            target=url_id(resolved)
        except (ValueError,UnicodeError):
            warnings.append('canonical_invalid_target');row['usable']=False;continue
        row['resolved_target']=resolved;row['target']=target
        if urlsplit(resolved).fragment:warnings.append('canonical_fragment')
        if not urlsplit(raw).scheme:warnings.append('canonical_relative_reference')
        if row['usable']:targets.append(target)
    refreshes=[]
    for row in parser.refreshes:
        match=re.fullmatch(r'\s*(\d+(?:\.\d+)?)\s*;\s*url\s*=\s*(.*?)\s*',row['value'],re.I|re.S)
        if not match:
            warnings.append('refresh_unparsed');continue
        raw=match.group(2).strip().strip('\'"')
        try:
            if not raw:raise ValueError('empty_refresh')
            target=url_id(urljoin(base if row['kind']=='meta_refresh' else url,raw))
        except (ValueError,UnicodeError):warnings.append('refresh_unparsed');continue
        delay=float(match.group(1))
        refreshes.append({**row,'target':target,'delay_seconds':delay,'signal':'permanent_hint' if delay==0 else 'temporary_hint'})
    if len(targets)>len(set(targets)):warnings.append('duplicate_canonical_declarations')
    unique=list(dict.fromkeys(targets))
    return {'url':url,'base_url':base,'declarations':declarations,'targets':unique,
        'conflict':len(unique)>1,'refreshes':refreshes,'warnings':sorted(set(warnings)),
        'engine_selected_canonical':'unknown'}
