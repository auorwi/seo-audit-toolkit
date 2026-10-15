"""Read source metadata without pretending to implement browser HTML5 recovery."""
import re
from html.parser import HTMLParser

class MetadataParser(HTMLParser):
    def __init__(self,limit):
        super().__init__(convert_charrefs=True)
        self.limit=limit;self.stack=[];self.active_title=None;self.active_h1=None;self.body=[];self.body_length=0
        self.result={'titles':[],'descriptions':[],'keywords':[],'h1':[],'html_lang':None,'body_text':'',
            'coverage':{'body_complete':True,'closed_head':False,'head_seen':False,'source_parser_not_browser':True}}
    def handle_starttag(self,tag,attrs):
        attrs=dict(reversed(attrs));ignored=any(t in {'script','style','template','noscript'} for t in self.stack)
        if tag=='html' and self.result['html_lang'] is None:self.result['html_lang']=attrs.get('lang')
        if not ignored:
            if tag=='head':self.result['coverage']['head_seen']=True
            if tag=='title' and 'head' in self.stack and not any(t in {'svg','math'} for t in self.stack):
                line,col=self.getpos();row={'value':'','line':line,'column':col+1,'attributes':attrs}
                self.result['titles'].append(row);self.active_title=row
            if tag=='meta' and 'head' in self.stack:
                field={'description':'descriptions','keywords':'keywords'}.get((attrs.get('name') or '').casefold())
                if field:
                    line,col=self.getpos();self.result[field].append({'value':attrs.get('content'),'line':line,'column':col+1,'attributes':attrs})
            if tag=='h1' and 'body' in self.stack:self.active_h1=[]
        if tag not in {'area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr'}:self.stack.append(tag)
        elif tag=='br' and not ignored:self.handle_data(' ')
    def handle_startendtag(self,tag,attrs):
        self.handle_starttag(tag,attrs)
        if self.stack and self.stack[-1]==tag:self.handle_endtag(tag)
    def handle_endtag(self,tag):
        ignored=any(t in {'script','style','template','noscript'} for t in self.stack)
        if tag=='title' and not ignored:self.active_title=None
        if tag=='h1' and self.active_h1 is not None and not ignored:
            self.result['h1'].append(re.sub(r'\s+',' ',''.join(self.active_h1)).strip());self.active_h1=None
        if tag=='head' and not ignored:self.result['coverage']['closed_head']=True
        if tag in self.stack:
            self.stack=self.stack[:len(self.stack)-1-self.stack[::-1].index(tag)]
        if tag in {'div','p','main','section','li','h1','h2','h3','article'} and 'body' in self.stack:self.handle_data(' ')
    def handle_data(self,data):
        if any(t in {'script','style','template','noscript'} for t in self.stack):return
        if self.active_title is not None:self.active_title['value']+=data
        if self.active_h1 is not None:self.active_h1.append(data)
        if 'body' in self.stack and 'head' not in self.stack:
            remaining=self.limit-self.body_length
            if len(data)>remaining:self.result['coverage']['body_complete']=False
            chunk=data[:max(remaining,0)];self.body.append(chunk);self.body_length+=len(chunk)

def extract(html,url,*,max_text_chars=500000):
    if not isinstance(html,str) or max_text_chars<=0:raise ValueError('invalid_extraction_input')
    parser=MetadataParser(max_text_chars);parser.feed(html);parser.close()
    parser.result['body_text']=re.sub(r'\s+',' ',''.join(parser.body)).strip();parser.result['url']=url
    return parser.result
