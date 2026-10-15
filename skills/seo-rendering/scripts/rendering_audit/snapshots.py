"""Normalize explicit capture fields without inventing browser execution or coverage."""
import json
import sys
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urljoin
from .shared import url_id

dependency=Path(__file__).resolve().parents[3]/'seo-canonical-routing/scripts'
if not (dependency/'canonical_routing/declarations.py').is_file():raise ImportError('Requires sibling seo-canonical-routing')
if str(dependency) not in sys.path:sys.path.insert(0,str(dependency))
from canonical_routing.declarations import parse as canonical_declarations

FIELDS={'title','titles','descriptions','canonical','h1','main_text','identity','schema','links',
    'placeholder_count','page_errors','console_errors','document_ready_state','network_idle','visible_items','page_indicator'}
LIST_TEXT={'titles','descriptions','canonical','h1','page_errors','console_errors','visible_items'}
TEXT={'title','main_text','identity','document_ready_state','page_indicator'}
VOID={'area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr'}

def text(value):return ' '.join(value.split())

class Extractor(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True);self.stack=[];self.titles=[];self.h1=[];self.main=[]
        self.descriptions=[];self.links=[];self.schema=[]

    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs);inherited_skip=any(f['skip'] for f in self.stack)
        in_head=any(f['tag']=='head' for f in self.stack)
        frame={'tag':tag,'skip':inherited_skip or tag in {'script','style','template'},'parts':[],'field':None}
        if not inherited_skip:
            if tag=='title' and in_head:frame['field']='title'
            elif tag=='h1':frame['field']='h1'
            elif (tag=='main' or attrs.get('role')=='main') and not any(f['field']=='main' for f in self.stack):frame['field']='main'
            elif tag=='script' and (attrs.get('type') or '').lower()=='application/ld+json':frame['field']='schema'
            elif tag=='a' and 'href' in attrs:frame['field']='link';frame['href']=attrs['href'] or ''
            if tag=='meta' and in_head and (attrs.get('name') or '').lower()=='description':self.descriptions.append(attrs.get('content') or '')
        if tag not in VOID:self.stack.append(frame)

    def handle_data(self,data):
        if self.stack and self.stack[-1]['field']=='schema':self.stack[-1]['parts'].append(data)
        if any(f['skip'] for f in self.stack):return
        for frame in self.stack:
            if frame['field'] in {'title','h1','main','link'}:frame['parts'].append(data)

    def finish(self,frame):
        value=text(' '.join(frame['parts']))
        if frame['field']=='title':self.titles.append(value)
        elif frame['field']=='h1':self.h1.append(value)
        elif frame['field']=='main':self.main.append(value)
        elif frame['field']=='link':self.links.append({'raw_href':frame['href'],'text':value})
        elif frame['field']=='schema':
            raw=''.join(frame['parts'])
            try:parsed=json.loads(raw);error=None
            except (ValueError,TypeError):parsed=None;error='invalid_json'
            self.schema.append({'raw':raw,'parsed':parsed,'error':error})

    def handle_endtag(self,tag):
        indexes=[i for i,f in enumerate(self.stack) if f['tag']==tag]
        if not indexes:return
        index=indexes[-1]
        for frame in reversed(self.stack[index:]):self.finish(frame)
        del self.stack[index:]

    def complete(self):
        for frame in reversed(self.stack):self.finish(frame)
        self.stack=[]

def extract_html(html,url,*,max_text_chars=20000,max_links=2000):
    if not isinstance(html,str):raise ValueError('html_text_required')
    if type(max_text_chars) is not int or max_text_chars<=0 or type(max_links) is not int or max_links<=0:raise ValueError('invalid_capture_limit')
    url=url_id(url);parser=Extractor();parser.feed(html);parser.complete()
    declarations=canonical_declarations(html,[],url);links=[]
    for link in parser.links[:max_links]:
        try:href=url_id(urljoin(declarations['base_url'],link['raw_href']))
        except (ValueError,UnicodeError):href=None
        links.append({**link,'href':href})
    main=text(' '.join(parser.main)) if parser.main else None
    values={'url':url,'title':parser.titles[0] if parser.titles else '', 'titles':parser.titles,
        'descriptions':parser.descriptions,'canonical':[r['target'] for r in declarations['declarations'] if r['usable'] and r['target']],
        'h1':parser.h1,'main_text':main[:max_text_chars] if main is not None else None,'identity':None,
        'schema':parser.schema,'links':links,'placeholder_count':None,'page_errors':None,'console_errors':None,
        'document_ready_state':None,'network_idle':None,'representation':'initial_html','full_dom':False,
        'visibility':'source_text_visibility_unknown'}
    coverage={key:'unknown' for key in FIELDS}
    for key in ('title','titles','descriptions','canonical','h1','schema','links'):coverage[key]='complete'
    if main is not None:coverage['main_text']='partial' if len(main)>max_text_chars else 'complete'
    if len(parser.links)>max_links:coverage['links']='partial'
    values['coverage']=coverage
    return values

def normalize_dom(payload):
    if not isinstance(payload,dict):raise ValueError('dom_snapshot_must_be_object')
    coverage=payload.get('coverage',{})
    if not isinstance(coverage,dict) or not set(coverage)<=FIELDS:raise ValueError('invalid_capture_fields')
    result={'url':url_id(payload['url']),'representation':'dom_fields','full_dom':False,'coverage':{}}
    for field in FIELDS:
        state=coverage.get(field,'unknown')
        if state not in {'complete','partial','unknown'}:raise ValueError('invalid_field_coverage')
        result['coverage'][field]=state
        if state=='unknown':result[field]=None;continue
        if field not in payload:raise ValueError('captured_value_missing:'+field)
        value=payload[field]
        if field in LIST_TEXT and (not isinstance(value,list) or not all(isinstance(v,str) for v in value)):raise ValueError('invalid_list_field:'+field)
        if field in TEXT and value is not None and not isinstance(value,str):raise ValueError('invalid_text_field:'+field)
        if field in {'schema','links'} and (not isinstance(value,list) or not all(isinstance(v,dict) for v in value)):raise ValueError('invalid_object_list:'+field)
        if field=='placeholder_count' and value is not None and (type(value) is not int or value<0):raise ValueError('invalid_placeholder_count')
        if field=='network_idle' and value is not None and type(value) is not bool:raise ValueError('invalid_network_idle')
        result[field]=value
    return result
