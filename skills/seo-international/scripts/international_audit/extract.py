"""Extract actual declarations, retaining unsuitable placements and raw targets."""
import json,re
from urllib.parse import urljoin,urlsplit
from xml.etree import ElementTree as ET
from .shared import url_id
from crawlability.html_compat import HTMLParser

def declaration(attrs,source,channel,locator,base=None,problems=None):
    href=attrs.get('href','');issues=list(problems or []);target=None
    try:target=url_id(urljoin(base or source,href))
    except (ValueError,TypeError):issues.append('invalid_url')
    if not re.match(r'^https?://',href,re.I):issues.append('not_absolute')
    try:
        if urlsplit(href).fragment:issues.append('fragment')
    except ValueError:pass
    if not attrs.get('hreflang'):issues.append('missing_locale')
    return {'source_url':source,'href':href,'target_url':target,'locale':attrs.get('hreflang'),'channel':channel,'locator':locator,'problems':issues,'eligible':not issues}

class Parser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True);self.head=False;self.ignored=0;self.links=[];self.bases=[];self.langs=[];self.scripts=[];self.script=None;self.gaps=[]
    def handle_starttag(self,tag,pairs):
        attrs={}
        for key,value in pairs:
            if key in attrs:self.gaps.append({'reason':'duplicate_attribute','tag':tag,'attribute':key});continue
            attrs[key]=value or ''
        if tag in {'template','noscript'}:self.ignored+=1
        if self.ignored:return
        if tag=='head':self.head=True
        if tag=='html':self.langs.append(attrs.get('lang'))
        if tag=='base' and self.head and attrs.get('href'):self.bases.append(attrs['href'])
        if tag=='link':self.links.append((attrs,self.head,self.getpos()))
        if tag=='script' and attrs.get('type','').lower()=='application/ld+json':self.script=[]
    def handle_endtag(self,tag):
        if tag in {'template','noscript'}:self.ignored=max(0,self.ignored-1)
        if self.ignored:return
        if tag=='head':self.head=False
        if tag=='script' and self.script is not None:self.scripts.append(''.join(self.script));self.script=None
    def handle_data(self,data):
        if self.script is not None and not self.ignored:self.script.append(data)

def extract_html(html,url):
    source=url_id(url);p=Parser();p.feed(html);p.close()
    result={'alternates':[],'canonicals':[],'html_langs':p.langs,'schema_languages':[],'gaps':p.gaps}
    base=urljoin(source,p.bases[0]) if p.bases else source
    for attrs,head,pos in p.links:
        rel=attrs.get('rel','').lower().split();locator=f'link@{pos[0]}:{pos[1]}'
        if 'alternate' in rel and 'hreflang' in attrs:
            issues=[]
            if not head:issues.append('outside_head')
            if 'media' in attrs:issues.append('media_attribute')
            result['alternates'].append(declaration(attrs,source,'html',locator,base,issues))
        if 'canonical' in rel:
            try:target=url_id(urljoin(base,attrs.get('href','')))
            except ValueError:target=None
            result['canonicals'].append({'href':attrs.get('href'),'target_url':target,'channel':'html','locator':locator,'in_head':head})
    def walk(value,path):
        if isinstance(value,dict):
            for key,child in value.items():
                if key=='inLanguage':
                    for i,lang in enumerate(child if isinstance(child,list) else [child]):result['schema_languages'].append({'value':lang,'path':path+'.'+key+(f'[{i}]' if isinstance(child,list) else '')})
                else:walk(child,path+'.'+key)
        elif isinstance(value,list):
            for i,child in enumerate(value):walk(child,path+f'[{i}]')
    for i,script in enumerate(p.scripts):
        try:walk(json.loads(script),f'$[script={i}]')
        except (ValueError,RecursionError) as e:result['gaps'].append({'reason':'jsonld_parse','script_index':i,'detail':str(e)})
    return result

def split_outside(value,separator):
    parts=[];start=0;quote=False;angle=0;escape=False
    for i,char in enumerate(value):
        if escape:escape=False;continue
        if char=='\\' and quote:escape=True;continue
        if char=='"':quote=not quote
        if not quote:
            if char=='<':angle+=1
            elif char=='>':angle=max(0,angle-1)
            elif char==separator and not angle:parts.append(value[start:i].strip());start=i+1
    parts.append(value[start:].strip());return parts

def extract_headers(headers,url):
    source=url_id(url);out={'alternates':[],'canonicals':[],'gaps':[]}
    items=headers.items() if isinstance(headers,dict) else headers
    for index,(key,value) in enumerate(items):
        if key.lower()!='link':continue
        for n,part in enumerate(split_outside(value,',')):
            match=re.match(r'^<([^>]*)>(.*)$',part)
            if not match:out['gaps'].append({'reason':'malformed_link_header','raw':part});continue
            attrs={'href':match[1]};problems=[]
            for param in split_outside(match[2],';'):
                if not param:continue
                if '=' not in param:problems.append('malformed_parameter');continue
                k,v=param.split('=',1);k=k.strip().lower();v=v.strip().strip('"')
                if k in attrs:problems.append('duplicate_parameter');continue
                attrs[k]=v
            rel=attrs.get('rel','').lower().split();locator=f'Link[{index}][{n}]'
            if 'anchor' in attrs:problems.append('alternate_context')
            if 'alternate' in rel and 'hreflang' in attrs:out['alternates'].append(declaration(attrs,source,'http',locator,problems=problems))
            if 'canonical' in rel:
                try:target=url_id(urljoin(source,attrs['href']))
                except ValueError:target=None
                out['canonicals'].append({'href':attrs['href'],'target_url':target,'channel':'http','locator':locator})
    return out

def extract_sitemap(xml):
    if re.search(r'<!\s*(DOCTYPE|ENTITY)',xml,re.I):raise ValueError('xml_external_entities_not_allowed')
    try:root=ET.fromstring(xml)
    except ET.ParseError as e:raise ValueError('sitemap_xml_parse: '+str(e)) from e
    ns='{http://www.sitemaps.org/schemas/sitemap/0.9}';xh='{http://www.w3.org/1999/xhtml}'
    out={'alternates':[],'gaps':[],'urls':[]}
    if root.tag!=ns+'urlset':out['gaps'].append({'reason':'not_namespaced_urlset'});return out
    for i,node in enumerate(root.findall(ns+'url')):
        loc=node.findtext(ns+'loc')
        try:source=url_id(loc)
        except (ValueError,TypeError):out['gaps'].append({'reason':'invalid_loc','index':i});continue
        out['urls'].append(source)
        for j,link in enumerate(node.findall(xh+'link')):
            attrs=link.attrib
            if 'alternate' in attrs.get('rel','').lower().split():out['alternates'].append(declaration(attrs,source,'sitemap',f'url[{i}]/xhtml:link[{j}]'))
    return out
