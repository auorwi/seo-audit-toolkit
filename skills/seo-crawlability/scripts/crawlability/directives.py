"""Observed directives and their scope; this does not assert search indexing."""
import re
from datetime import datetime,timezone
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from .common import header_pairs,moment

ALIASES={'googlebot':{'all','robots','googlebot'},'bingbot':{'all','robots','bingbot'},'yandexbot':{'all','robots','yandex','yandexbot'}}
VALUED={'unavailable_after','max-snippet','max-image-preview','max-video-preview'}
BREAK=re.compile(r',(?=\s*(?:[a-z_-]+\s*:|(?:all|none|noindex|index|nofollow|follow|indexifembedded|nosnippet|noimageindex)\b))',re.I)

class MetaParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True);self.rows=[];self.template_depth=0;self.in_body=False

    def handle_starttag(self,tag,attrs):
        if tag=='body':self.in_body=True
        if tag=='template':self.template_depth+=1
        if tag!='meta' or self.template_depth:return
        a={}
        for key,value in attrs:a.setdefault(key,value)
        name=(a.get('name') or '').lower()
        if name in {'robots','googlebot','googlebot-news','bingbot','yandex','yandexbot'}:
            self.rows.append({'kind':'meta','scope':name,'value':a.get('content') or '', 'line':self.getpos()[0],'in_body':self.in_body})

    def handle_endtag(self,tag):
        if tag=='template':self.template_depth=max(0,self.template_depth-1)

def _parts(value,scope,allow_agent):
    rows=[]
    for part in BREAK.split(value):
        part=part.strip()
        match=re.match(r'^([a-z_-]+)\s*:\s*(.*)$',part,re.I|re.S)
        if allow_agent and match and match.group(1).lower() not in VALUED:
            scope=match.group(1).lower();part=match.group(2).strip()
        valued=re.match(r'^([a-z_-]+)\s*:\s*(.*)$',part,re.I|re.S)
        if valued and valued.group(1).lower() in VALUED:
            rows.append((scope,valued.group(1).lower(),valued.group(2).strip()))
        else:
            rows.extend((scope,word.lower(),None) for word in re.split(r'[,\s]+',part) if word)
    return rows

def _expiration(value,at):
    try:
        if re.fullmatch(r'\d{4}-\d{2}-\d{2}',value):
            day=datetime.fromisoformat(value).date();today=moment(at).date()
            return None if day==today else day<today
        try:parsed=datetime.fromisoformat(value.replace('Z','+00:00'))
        except ValueError:parsed=parsedate_to_datetime(value)
        if parsed.tzinfo is None:return None
        return parsed.astimezone(timezone.utc)<=moment(at)
    except (ValueError,TypeError,OverflowError):return None

def parse_directives(html,headers,agent,at):
    moment(at)
    product=agent.lower()
    if product not in ALIASES:raise ValueError('unsupported_agent_profile')
    parser=MetaParser();parser.feed(html)
    sources=parser.rows
    sources += [{'kind':'header','scope':'all','value':value,'line':None} for key,value in header_pairs(headers) if key=='x-robots-tag']
    tokens=set();expirations=[];warnings=[]
    for source in sources:
        parts=_parts(source['value'],source['scope'],source['kind']=='header')
        source['applies']=any(scope in ALIASES[product] for scope,_,_ in parts)
        source['parsed']=[{'scope':scope,'directive':token,'value':value} for scope,token,value in parts]
        if source.get('in_body') and product!='googlebot' and source['applies']:
            source['applies']=False;warnings.append('body_meta_behavior_unverified');continue
        for scope,token,value in parts:
            if scope not in ALIASES[product]:continue
            tokens.add(token)
            if token=='unavailable_after':expirations.append(value)
    if 'none' in tokens:tokens.update(['noindex','nofollow'])
    states=[_expiration(value,at) for value in expirations]
    expired=True if True in states else None if None in states else False
    if None in states:warnings.append('unavailable_after_unparsed')
    if expirations and product!='googlebot':
        expired=None;warnings.append('engine_expiration_behavior_unverified')
    return {'agent':product,'noindex':'noindex' in tokens,'nofollow':'nofollow' in tokens,
        'index_conflict':{'index','noindex'}<=tokens,'follow_conflict':{'follow','nofollow'}<=tokens,
        'embedded_exception':product=='googlebot' and {'noindex','indexifembedded'}<=tokens,
        'expired':expired,'expiration_values':expirations,'tokens':sorted(tokens),'sources':sources,
        'warnings':sorted(set(warnings)),'index_status':'unknown'}
