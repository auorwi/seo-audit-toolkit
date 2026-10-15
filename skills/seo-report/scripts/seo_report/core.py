
import sys as _site_sys
from pathlib import Path as _SitePath
_site_dependency=_SitePath(__file__).resolve().parents[3]/'seo-crawlability/scripts'
if str(_site_dependency) not in _site_sys.path:_site_sys.path.insert(0,str(_site_dependency))
from crawlability.site import get_profile,site_host,site_origin,allowed_hosts,in_scope,require_url,brand_name,business_profile
import collections, datetime as dt, hashlib, json, pathlib, re, sqlite3
from urllib.parse import urlsplit, parse_qsl
SKILLS={f'{i:03}' for i in range(1,18)}
SECRET={'access_token','refresh_token','authorization','cookie','set-cookie','password','client_secret','appsecret','api_key'}
def canonical(x):return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)
def digest(x):return hashlib.sha256(x if isinstance(x,bytes) else canonical(x).encode()).hexdigest()
def timestamp(s):
 try:
  v=dt.datetime.fromisoformat(s.replace('Z','+00:00'))
  if v.tzinfo is None:raise ValueError()
  return v.astimezone(dt.timezone.utc)
 except (ValueError,TypeError,AttributeError):raise ValueError('timezone-aware timestamp required') from None
def pairs(items):
 d={}
 for k,v in items:
  if k in d:raise ValueError('duplicate JSON key')
  d[k]=v
 return d
def parse(b):
 try:return json.loads(b,object_pairs_hook=pairs,parse_constant=lambda x:(_ for _ in ()).throw(ValueError('nonfinite JSON')))
 except (UnicodeError,json.JSONDecodeError):raise ValueError('invalid JSON') from None
def scan(x):
 if isinstance(x,dict):
  for k,v in x.items():
   if k.lower() in SECRET:raise ValueError('credential-bearing source rejected')
   scan(v)
 elif isinstance(x,list):
  for v in x:scan(v)
 elif isinstance(x,str):
  if re.search(r'https?://[^/\s]+@',x):raise ValueError('URL userinfo rejected')
  if re.search(r'(?i)(?:Bearer\s+[A-Za-z0-9._-]{8,}|(?:access_token|refresh_token|api_key|client_secret)=)',x):raise ValueError('credential-bearing text rejected')
def load_manifest(path):
 p=pathlib.Path(path).resolve();m=parse(p.read_bytes());scan(m)
 if m.get('site')!=site_host() or not re.fullmatch('[A-Za-z0-9._-]{1,100}',m.get('run_id','')):raise ValueError('site/run_id invalid')
 at=timestamp(m.get('at'))
 requested=m.get('requested_skills',sorted(SKILLS))
 if not isinstance(requested,list) or not requested or any(not isinstance(v,str) or v not in SKILLS for v in requested) or len(requested)!=len(set(requested)):raise ValueError('requested_skills must be unique supported IDs')
 if not isinstance(m.get('sources'),list) or not m['sources']:raise ValueError('sources required')
 loaded=[]
 for e in m['sources']:
  skill=e.get('skill');rel=pathlib.Path(e.get('path',''))
  if skill not in SKILLS or rel.is_absolute():raise ValueError('unsupported skill or path')
  source=(p.parent/rel).resolve()
  if not source.is_relative_to(p.parent) or not source.is_file() or source.stat().st_size>64*1024*1024:raise ValueError('source missing/escaped/oversized')
  b=source.read_bytes()
  if digest(b)!=e.get('sha256'):raise ValueError('source SHA mismatch')
  r=parse(b);scan(r)
  if not isinstance(r,dict):raise ValueError('report object required')
  if r.get('configured_site',site_host())!=site_host():raise ValueError('source site mismatch')
  if 'fixture' in str(r.get('run_kind','')).lower() or 'synthetic' in str(r.get('run_kind','')).lower():raise ValueError('fixture not accepted in production ledger')
  if skill=='001':
   if 'url_count' not in r or 'coverage_claim' not in r:raise ValueError('001 summary contract required')
   date=r.get('generated_at');findings=[];coverage=r
  else:
   if str(r.get('skill_id',r.get('skill'))) not in {skill,skill+'-sitemap'}:raise ValueError('source skill mismatch')
   date=r.get('at');findings=r.get('findings',[]);coverage=r.get('coverage',{})
   if skill!='017' and not isinstance(r.get('findings'),list):raise ValueError('findings required')
   if skill=='017' and not isinstance(r.get('rechecks'),list):raise ValueError('rechecks required')
  if timestamp(date)>at:raise ValueError('future source')
  for f in findings:
   if not isinstance(f,dict) or not isinstance(f.get('issue_id',f.get('id')),str) or not f.get('rule'):raise ValueError('finding ID/rule required')
   if f.get('observed_at') and timestamp(f['observed_at'])>timestamp(date):raise ValueError('future finding')
  for rcheck in r.get('rechecks',[]):
   if not rcheck.get('issue_id') or rcheck.get('status') not in {'passed','partial_pass','failed','inconclusive'}:raise ValueError('invalid recheck')
  loaded.append({'skill':skill,'path':e['path'],'sha256':e['sha256'],'at':date,'report':r,'coverage':coverage})
 return dict(m,loaded=loaded)
def category(f):
 if not f.get('evidence') and not f.get('link_occurrences'):return 'evidence_gap'
 c=f.get('classification',f.get('certainty','unknown'))
 if c=='evidence_gap':return 'evidence_gap'
 if 'environment_limited' in c:return 'environment_limited'
 if c in {'engine_observation','historical_observation','platform_recommendation'}:return 'platform_observation'
 if c in {'confirmed','evidence_supported_conflict','html_conformance_error','accessibility_violation'}:return 'confirmed'
 return 'review'
def db_open(state):
 state=pathlib.Path(state);state.mkdir(parents=True,exist_ok=True)
 db=sqlite3.connect(state/'ledger.sqlite');db.row_factory=sqlite3.Row
 db.executescript('''CREATE TABLE IF NOT EXISTS observations(event TEXT PRIMARY KEY,issue TEXT NOT NULL,at TEXT NOT NULL,source TEXT NOT NULL,data TEXT NOT NULL);
 CREATE TABLE IF NOT EXISTS rechecks(event TEXT PRIMARY KEY,issue TEXT NOT NULL,at TEXT NOT NULL,data TEXT NOT NULL);
 CREATE TABLE IF NOT EXISTS sources(hash TEXT PRIMARY KEY,data TEXT NOT NULL);''')
 return db
def aggregate(m,state):
 db=db_open(state)
 try:
  with db:
   identities={};same_time={}
   for row in db.execute('SELECT issue,at,data FROM observations'):
    f=parse(row['data']);identities[row['issue']]=(f.get('url'),f['rule']);same_time[(row['issue'],timestamp(row['at']))]=canonical(f)
   active=set()
   for s in m['loaded']:
    for f in s['report'].get('findings',[]):
     key=f.get('issue_id',f.get('id'));identity=(f.get('url'),f['rule']);date=f.get('observed_at') or s['at'];event_at=timestamp(date)
     if key in identities and identities[key]!=identity:raise ValueError('issue ID collision')
     if (key,event_at) in same_time and same_time[(key,event_at)]!=canonical(f):raise ValueError('same-time finding conflict')
     identities[key]=identity;same_time[(key,event_at)]=canonical(f);active.add(key)
   recheck_times={(row['issue'],timestamp(row['at'])):row['data'] for row in db.execute('SELECT * FROM rechecks')}
   for s in m['loaded']:
    for r in s['report'].get('rechecks',[]):
     rk=(r['issue_id'],timestamp(s['at']))
     if rk in recheck_times and recheck_times[rk]!=canonical(r):raise ValueError('same-time recheck conflict')
     recheck_times[rk]=canonical(r)
     if r['issue_id'] in identities and identities[r['issue_id']]!=(r.get('original_url'),r.get('rule')):raise ValueError('recheck identity mismatch')
   for s in m['loaded']:
    meta={k:v for k,v in s.items() if k!='report'}
    db.execute('INSERT OR IGNORE INTO sources VALUES(?,?)',(s['sha256'],canonical(meta)))
    for f in s['report'].get('findings',[]):
     key=f.get('issue_id',f.get('id'));date=f.get('observed_at') or s['at']
     db.execute('INSERT OR IGNORE INTO observations VALUES(?,?,?,?,?)',(digest([key,date,f]),key,date,canonical(meta),canonical(f)))
    for r in s['report'].get('rechecks',[]):db.execute('INSERT OR IGNORE INTO rechecks VALUES(?,?,?,?)',(digest([s['at'],r]),r['issue_id'],s['at'],canonical(r)))
   buckets=collections.defaultdict(list)
   for row in db.execute('SELECT * FROM observations'):buckets[row['issue']].append(dict(row))
   checks=collections.defaultdict(list)
   for row in db.execute('SELECT * FROM rechecks'):checks[row['issue']].append(dict(row))
   issues=[]
   for key,rows in sorted(buckets.items()):
    rows.sort(key=lambda r:(timestamp(r['at']),r['event']));f=parse(rows[-1]['data']);src=parse(rows[-1]['source'])
    rechecks=sorted(checks.get(key,[]),key=lambda r:(timestamp(r['at']),r['event']))
    issues.append({'issue_id':key,'url':f.get('url'),'rule':f['rule'],'source_skill':src['skill'],'source':src,'category':category(f),'status':'open','seen_in_run':key in active,'first_seen':rows[0]['at'],'last_seen':rows[-1]['at'],'finding':f,'recheck':parse(rechecks[-1]['data']) if rechecks else None,'recheck_at':rechecks[-1]['at'] if rechecks else None,'observation_count':len(rows)})
   sources=[]
   for s in sorted(m['loaded'],key=lambda s:(s['skill'],timestamp(s['at']),s['sha256'])):
    sources.append(dict({k:v for k,v in s.items() if k!='report'},gaps=s['report'].get('gaps',[]),input_gaps=s['report'].get('input_gaps',[]),limitations=s['report'].get('limitations',[]),platform_reports=s['report'].get('platform_reports',[]),finding_count=len(s['report'].get('findings',[]))))
   return {'skill_id':'018','version':'1.0.0','run_id':m['run_id'],'at':m['at'],'mode':'existing_evidence_consolidation','full_site_verified':False,'raw_evidence_revalidated':False,'sources':sources,'issues':issues,'counts':dict(sorted(collections.Counter(x['category'] for x in issues).items())),'missing_skills':sorted(set(m.get('requested_skills',SKILLS))-{s['skill'] for s in sources}),'orphan_rechecks':[parse(r['data']) for k,rs in sorted(checks.items()) if k not in buckets for r in rs],'source_report_window':[min((s['at'] for s in sources),key=timestamp),max((s['at'] for s in sources),key=timestamp)],'notes':['现有审查结果汇总，不是本次重新全站扫描；报告时间不等于平台数据库/爬虫日期。','沿用原问题ID；不同技能的相似症状不自动合并为同一根因。','状态open表示待处置记录，包含候选/缺口，不表示全部确认缺陷。','复查通过不自动关闭问题或证明搜索引擎恢复。','源报告SHA已核对；底层网页、截图等证据本次没有全部重新核验。']}
 finally:db.close()
