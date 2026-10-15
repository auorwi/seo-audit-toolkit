"""Inventory actual anchors and potential controls; no inferred click destinations."""

import sys as _site_sys
from pathlib import Path as _SitePath
_site_dependency=_SitePath(__file__).resolve().parents[3]/'seo-crawlability/scripts'
if str(_site_dependency) not in _site_sys.path:_site_sys.path.insert(0,str(_site_dependency))
from crawlability.site import get_profile,site_host,site_origin,allowed_hosts,in_scope,require_url,brand_name,business_profile
from html.parser import HTMLParser
from urllib.parse import urljoin,urlsplit
from .shared import url_id
VOID={'area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr'}
def compact(text):return ' '.join(text.split())

class Parser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True);self.stack=[];self.nodes=[];self.bases=[];self.lang=None;self.gaps=[]
    def handle_starttag(self,tag,attrs):
        values={};duplicates=[]
        for k,v in attrs:
            if k in values:duplicates.append(k)
            else:values[k]=v
        inert=any(x['tag']=='template' for x in self.stack) or tag=='template'
        frame={'tag':tag,'node':None};line,column=self.getpos()
        if tag=='html' and self.lang is None:self.lang=values.get('lang')
        if not inert:
            if tag=='base' and 'href' in values:self.bases.append(values['href'] or '')
            if tag=='a' or tag=='button' or values.get('role','').lower()=='link':
                component=next((x['tag'] for x in reversed(self.stack) if x['tag'] in {'main','nav','header','footer'}),'unknown')
                node={'tag':tag,'attrs':values,'text':[],'image_alt':[],'component':component,'locator':f'{tag}[observed-index={len(self.nodes)}]','line':line,'column':column,'conditional_noscript':any(x['tag']=='noscript' for x in self.stack)}
                self.nodes.append(node);frame['node']=node
                if duplicates:self.gaps.append({'reason':'duplicate_attributes','locator':node['locator'],'attributes':duplicates})
            if tag=='img':
                for x in self.stack:
                    if x['node'] and values.get('alt'):x['node']['image_alt'].append(values['alt'])
        if tag not in VOID:self.stack.append(frame)
    def handle_endtag(self,tag):
        for i in range(len(self.stack)-1,-1,-1):
            if self.stack[i]['tag']==tag:del self.stack[i:];break
    def handle_startendtag(self,tag,attrs):
        self.handle_starttag(tag,attrs)
        if tag not in VOID:self.handle_endtag(tag)
    def handle_data(self,data):
        if any(x['tag'] in {'script','style','template'} for x in self.stack):return
        for frame in self.stack:
            if frame['node']:frame['node']['text'].append(data)

def extract_links(html,url,*,internal_hosts=None):
    url=url_id(url);p=Parser();p.feed(html);p.close();hosts=set(internal_hosts or allowed_hosts())
    base=url;gaps=list(p.gaps)
    if p.bases:
        try:base=url_id(urljoin(url,p.bases[0].strip()))
        except ValueError:base=None;gaps.append({'reason':'invalid_base_url','value':p.bases[0]})
    result={'url':url,'base_url':base,'html_lang':p.lang,'links':[],'controls':[],'gaps':gaps,'findings':[]}
    for n in p.nodes:
        a=n['attrs'];href=a.get('href');text=compact(''.join(n['text']));alt=compact(' '.join(n['image_alt']));title=compact(a.get('title') or '')
        row={k:n[k] for k in ['tag','component','locator','line','column','conditional_noscript']}
        row.update(href=href,anchor_text=text,image_alt=alt,title=title,aria_label=a.get('aria-label'),seo_text_candidate=text or alt or title,accessible_name_unverified=True,
            rel=sorted(set((a.get('rel') or '').lower().split())),hreflang=a.get('hreflang'),target=None,fragment='',internal=False,http_link=False,same_document=False,kind='missing_href',visibility='not_observed')
        if n['tag']!='a':row['kind']='control';result['controls'].append(row);continue
        if href is not None:
            raw=href.strip();row['kind']='empty_href' if not raw else 'http_href'
            try:
                scheme=urlsplit(raw).scheme.lower()
                if scheme and scheme not in {'http','https'}:row['kind']='non_http_href'
                elif base is not None or scheme:
                    resolved=urljoin(base or url,raw);row['target']=url_id(resolved);row['fragment']=urlsplit(resolved).fragment
                    row['internal']=urlsplit(row['target']).hostname in hosts;row['http_link']=True;row['same_document']=row['target']==url
            except ValueError as error:row['kind']='invalid_href';gaps.append({'reason':'invalid_href','locator':row['locator'],'value':href,'error':str(error)})
        result['links'].append(row)
    return result
