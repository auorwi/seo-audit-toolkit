
import sys as _site_sys
from pathlib import Path as _SitePath
_site_dependency=_SitePath(__file__).resolve().parents[3]/'seo-crawlability/scripts'
if str(_site_dependency) not in _site_sys.path:_site_sys.path.insert(0,str(_site_dependency))
from crawlability.site import get_profile,site_host,site_origin,allowed_hosts,in_scope,require_url,brand_name,business_profile
import fcntl, hashlib, html, json, os, pathlib, re, subprocess, xml.etree.ElementTree as ET
from contextlib import contextmanager
from urllib.parse import urlsplit
from .core import canonical, digest, parse

def parse_response(code,stdout):
 if code!=0:raise ValueError('Lark CLI failed; inspect its protected local error log')
 x=parse(stdout)
 if x.get('ok') is not True or not isinstance(x.get('data'),dict):raise ValueError('Lark rejected operation')
 d=x['data']
 if d.get('result') in {'failed','partial_success'}:raise ValueError('Lark partial/failed write; readback required')
 return d
class Lark:
 def __init__(self,logs):self.logs=pathlib.Path(logs);self.logs.mkdir(parents=True,exist_ok=True)
 def call(self,action,**kw):
  args=['lark-cli','docs'];xml=kw.get('xml');args+=['+fetch' if action=='fetch' else '+create' if action=='create' else '+update','--as','user']
  if action!='create':args+=['--doc',kw['url']]
  if action=='fetch':args+=['--detail','with-ids']
  elif action!='create':args+=['--command','block_replace' if action=='replace' else 'block_insert_after','--block-id',kw['block_id']]
  if xml is not None:args+=['--content','-']
  env=dict(os.environ,LARKSUITE_CLI_NO_UPDATE_NOTIFIER='1',LARKSUITE_CLI_NO_SKILLS_NOTIFIER='1')
  result=subprocess.run(args,input=xml,text=True,capture_output=True,timeout=120,env=env)
  # Errors can contain account identifiers; keep logs local, not in public artifacts.
  if result.returncode:(self.logs/'last-error.txt').write_text(result.stderr)
  d=parse_response(result.returncode,result.stdout)
  if action=='create':return d['document']['url']
  if action=='fetch':return d['document']['content']
  return d

def valid_url(url):
 p=urlsplit(url)
 if p.scheme!='https' or not p.hostname or not p.hostname.endswith(('.feishu.cn','.larksuite.com')) or p.username or p.password or p.query or not re.fullmatch('/docx/[A-Za-z0-9]+',p.path):raise ValueError('Feishu doc URL required')
 return url
@contextmanager
def lock(state):
 state=pathlib.Path(state);state.mkdir(parents=True,exist_ok=True)
 with (state/'publish.lock').open('a') as f:
  try:fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
  except BlockingIOError:raise ValueError('publication already running') from None
  yield state

def state_read(p):return parse(p.read_bytes()) if p.exists() else {'docs':{}}
def save(p,x):
 tmp=p.with_suffix('.tmp');
 with tmp.open('w') as f:f.write(canonical(x));f.flush();os.fsync(f.fileno())
 tmp.replace(p)
def doc_marker(key):return 'SEODOC-'+digest(key)[:24]
def sec_marker(doc,section):return 'SEOSEC-'+digest([doc,section])[:24]
def root(xml):
 try:return ET.fromstring('<root>'+xml+'</root>')
 except ET.ParseError:raise ValueError('invalid fetched XML') from None
def signature(e):return ' '.join(' '.join(e.itertext()).split())+' |LINKS| '+canonical([n.get('href') for n in e.iter('a')])
def section_xml(key,s):
 try:e=ET.fromstring(s['xml'])
 except ET.ParseError:raise ValueError('single valid root per section required') from None
 if e.tag not in {'p','table'}:raise ValueError('section must be p or table')
 marker=sec_marker(key,s['key'])
 if e.tag=='p':e.text=marker+' '+(e.text or '')
 else:
  caption=ET.Element('tr');cell=ET.SubElement(caption,'td');cell.text=marker
  tb=e.find('tbody')
  if tb is None:tb=ET.SubElement(e,'tbody')
  # Marker uses a complete row with the same number of columns as the table.
  n=len(e.find('thead/tr')) if e.find('thead/tr') is not None else 1
  for _ in range(n-1):ET.SubElement(caption,'td').text=''
  tb.insert(0,caption)
 return ET.tostring(e,encoding='unicode'),signature(e)
def locate(xml,marker):
 matches=[e for e in root(xml) if marker in signature(e)]
 if len(matches)>1:raise ValueError('duplicate publication marker')
 return matches[0] if matches else None

def adopt(key,url,state,transport):
 valid_url(url)
 with lock(state) as p:
  path=p/'publication-state.json';st=state_read(path);record=st['docs'].get(key)
  if record is None or record.get('url'):raise ValueError('only pending unknown creation can be adopted')
  content=transport.call('fetch',url=url)
  if locate(content,doc_marker(key)) is None:raise ValueError('document marker mismatch')
  record['url']=url;record['pending_create']=False;save(path,st)
 return url

def publish_document(doc,state,transport):
 sections=[(s,*section_xml(doc['key'],s)) for s in doc['sections']]
 if len({s['key'] for s in doc['sections']})!=len(sections):raise ValueError('duplicate section key')
 with lock(state) as p:
  path=p/'publication-state.json';st=state_read(path);key=doc['key'];content_hash=digest(doc);record=st['docs'].get(key)
  if record and not doc['mutable'] and record['content_hash']!=content_hash:raise ValueError('immutable run changed; choose a new run_id')
  if record is None:
   record={'content_hash':content_hash,'pending_create':True,'url':None,'sections':{}};st['docs'][key]=record;save(path,st)
   xml='<title>'+html.escape(doc['title'])+'</title><p>'+doc_marker(key)+'</p>'
   url=valid_url(transport.call('create',xml=xml));record['url']=url;record['pending_create']=False;save(path,st)
  elif not record.get('url'):raise ValueError('uncertain creation: locate marker and adopt existing document; do not recreate')
  url=record['url'];xml=transport.call('fetch',url=url)
  if locate(xml,doc_marker(key)) is None:raise ValueError('document identity marker missing')
  for s,desired,sig in sections:
   marker=sec_marker(key,s['key']);found=locate(xml,marker);old=record['sections'].get(s['key'])
   if found is not None and signature(found)==sig:
    record['sections'][s['key']]={'signature':sig,'pending':False};save(path,st);continue
   if old and old.get('pending'):raise ValueError('uncertain section write lacks exact readback; reconcile before retry')
   if found is not None:
    if old is None or signature(found)!=old['signature']:raise ValueError('generated block manually changed; preserve and review')
    action='replace';block=found.get('id')
   else:
    if old:raise ValueError('previously published block missing; preserve manual deletion')
    action='insert';children=list(root(xml));block=children[-1].get('id') if children else None
   if not block:raise ValueError('readback block ID required')
   record['sections'][s['key']]={'signature':old['signature'] if old else None,'pending':True,'expected_signature':sig};save(path,st)
   transport.call(action,url=url,block_id=block,xml=desired)
   xml=transport.call('fetch',url=url);found=locate(xml,marker)
   if found is None or signature(found)!=sig:raise ValueError('full text readback failed; no success recorded')
   record['sections'][s['key']]={'signature':sig,'pending':False};save(path,st)
  record['content_hash']=content_hash;save(path,st)
  return url

def publish_all(docs,run_id,state,transport):
 ledger=publish_document(docs['ledger'],state,transport)
 report=publish_document(docs['report'],state,transport)
 entry={'key':'entry','title':site_host()+' SEO · 审查报告入口','mutable':True,'sections':[{'key':'ledger','xml':'<p>持续台账：<a href="'+ledger+'">全部问题与最新复查</a>。保留首次/末次记录；观察和候选不等于已确认根因。</p>'},{'key':'run-'+run_id,'xml':'<p>'+html.escape(run_id)+'：<a href="'+report+'">现有审查结果汇总</a>。具体覆盖和证据日期以报告为准。</p>'}]}
 entry_url=publish_document(entry,state,transport)
 return {'entry':entry_url,'report':report,'ledger':ledger}
