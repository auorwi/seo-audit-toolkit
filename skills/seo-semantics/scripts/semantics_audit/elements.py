"""Bounded source-element evidence; not a browser or an HTML5 conformance parser."""
import hashlib
from collections import Counter
from .shared import url_id
from crawlability.html_compat import HTMLParser

VOID={'area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr'}
TEXT_EXCLUDED={'script','style','template'}

class SourceElements(HTMLParser):
    def __init__(self,max_nodes,max_text_chars):
        super().__init__(convert_charrefs=True)
        self.limit=max_nodes;self.text_limit=max_text_chars;self.nodes=[];self.stack=[];self.roots=Counter();self.stopped=False

    def handle_starttag(self,tag,pairs):
        if self.stopped:return
        if len(self.nodes)>=self.limit:self.stopped=True;return
        attributes={}
        for key,value in pairs:
            if key not in attributes:attributes[key]=value if value is not None else ''
        parent=self.stack[-1] if self.stack else None
        counts=parent['_children'] if parent else self.roots;counts[tag]+=1
        path=(parent['source_path']+' > ' if parent else '')+tag+':nth-of-type('+str(counts[tag])+')'
        line,column=self.getpos()
        node={'node_id':'source-'+str(len(self.nodes)+1),'tag':tag,'attributes':attributes,
            'attribute_pairs':[[k,v if v is not None else ''] for k,v in pairs],
            'parent_id':parent['node_id'] if parent else None,'ancestor_tags':[n['tag'] for n in self.stack],
            'source_path':path,'location':{'line':line,'column':column+1},'snippet':self.get_starttag_text(),
            'source_text':'','text_truncated':False,'visibility':'unknown','accessible_name':None,
            'hidden_hint':'hidden' in attributes or bool(parent and parent['hidden_hint']),
            'aria_hidden_hint':attributes.get('aria-hidden','').lower()=='true' or bool(parent and parent['aria_hidden_hint']),
            'inert_hint':tag=='template' or 'inert' in attributes or bool(parent and parent['inert_hint']),
            '_children':Counter()}
        self.nodes.append(node)
        if tag not in VOID:self.stack.append(node)

    def handle_startendtag(self,tag,attrs):
        self.handle_starttag(tag,attrs)
        if tag not in VOID:self.handle_endtag(tag)

    def handle_endtag(self,tag):
        if self.stopped:return
        for i in range(len(self.stack)-1,-1,-1):
            if self.stack[i]['tag']==tag:
                del self.stack[i:];break

    def handle_data(self,data):
        if self.stopped or any(n['tag'] in TEXT_EXCLUDED for n in self.stack):return
        for node in self.stack:
            remaining=self.text_limit-len(node['source_text'])
            node['source_text']+=data[:remaining]
            if len(data)>remaining:node['text_truncated']=True

def parse_html(html,url,*,max_nodes=50000,max_text_chars=20000):
    url=url_id(url)
    if not isinstance(html,str):raise ValueError('html_string_required')
    if type(max_nodes) is not int or max_nodes<1 or type(max_text_chars) is not int or max_text_chars<1:raise ValueError('positive_capture_limits_required')
    parser=SourceElements(max_nodes,max_text_chars);parser.feed(html);parser.close()
    for node in parser.nodes:
        node['source_text']=' '.join(node['source_text'].split());del node['_children']
    return {'url':url,'representation':'source_elements','html5_dom_parser':False,'source_sha256':hashlib.sha256(html.encode()).hexdigest(),
        'coverage':{'nodes':'partial' if parser.stopped else 'complete','visibility':'unknown','accessible_names':'unknown'},'nodes':parser.nodes}
