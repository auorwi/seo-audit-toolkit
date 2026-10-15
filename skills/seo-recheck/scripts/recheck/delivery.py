"""Idempotent retest events; source issue ledgers are never rewritten."""

import sys as _site_sys
from pathlib import Path as _SitePath
_site_dependency=_SitePath(__file__).resolve().parents[3]/'seo-crawlability/scripts'
if str(_site_dependency) not in _site_sys.path:_site_sys.path.insert(0,str(_site_dependency))
from crawlability.site import get_profile,site_host,site_origin,allowed_hosts,in_scope,require_url,brand_name,business_profile
import json,hashlib,sqlite3
from pathlib import Path
from .evidence import moment
from crawlability.report import md,csv_file

def packed(v):return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)
def connect(path):
 path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);db=sqlite3.connect(path,timeout=30);db.row_factory=sqlite3.Row
 db.executescript('CREATE TABLE IF NOT EXISTS events (run_id TEXT, namespace TEXT, issue_id TEXT, at TEXT, payload TEXT, PRIMARY KEY(run_id,namespace,issue_id)); CREATE TABLE IF NOT EXISTS latest (namespace TEXT,issue_id TEXT,first_seen TEXT,last_seen TEXT,status TEXT,payload TEXT,PRIMARY KEY(namespace,issue_id));');return db

def record(path,result):
 at=moment(result['at']).isoformat().replace('+00:00','Z');run_id='recheck-'+hashlib.sha256(packed(result).encode()).hexdigest()[:24];namespace='fixture' if result['run_kind']=='controlled_fixture' else 'audit';db=connect(path)
 try:
  with db:
   for r in result['rechecks']:
    iid=r['issue_id'];payload=packed(r);db.execute('INSERT OR IGNORE INTO events VALUES(?,?,?,?,?)',(run_id,namespace,iid,at,payload));old=db.execute('SELECT * FROM latest WHERE namespace=? AND issue_id=?',(namespace,iid)).fetchone()
    if old:
     first=min(old['first_seen'],at,key=moment);last=max(old['last_seen'],at,key=moment);newer=moment(at)>=moment(old['last_seen']);db.execute('UPDATE latest SET first_seen=?,last_seen=?,status=?,payload=? WHERE namespace=? AND issue_id=?',(first,last,r['status'] if newer else old['status'],payload if newer else old['payload'],namespace,iid))
    else:db.execute('INSERT INTO latest VALUES(?,?,?,?,?,?)',(namespace,iid,at,at,r['status'],payload))
  return run_id
 finally:db.close()

def history(path):
 db=connect(path)
 try:
  rows=[]
  for x in db.execute('SELECT l.*,COUNT(e.run_id) AS sightings FROM latest l LEFT JOIN events e ON e.namespace=l.namespace AND e.issue_id=l.issue_id GROUP BY l.namespace,l.issue_id ORDER BY l.namespace,l.issue_id'):
   r=dict(x);r['payload']=json.loads(r['payload']);rows.append(r)
  return rows
 finally:db.close()

def write_report(output,result,hist):
 output=Path(output)
 if output.exists() and any(output.iterdir()):raise ValueError('output_not_empty')
 output.mkdir(parents=True,exist_ok=True)
 for n,v in [('report.json',result),('recheck-history.json',hist)]:(output/n).write_text(json.dumps(v,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
 csv_file(output/'rechecks.csv',result['rechecks'],['issue_id','rule','owner_skill','status','scope_type','deployment_at','repair_verified','engine_state','engine_recovery_confirmed'])
 cases=[{'issue_id':r['issue_id'],**c} for r in result['rechecks'] for c in r['cases']];csv_file(output/'cases.csv',cases,['issue_id','case_id','url','device','js','entry','status','current_status','predicate','baseline','attempts','gaps'])
 csv_file(output/'recheck-history.csv',hist,['namespace','issue_id','first_seen','last_seen','status','sightings','payload'])
 lines=['# '+site_host()+' 017 · 修复复测','',f"复测比较时点：{md(result['at'])}",'']
 if result['run_kind']=='controlled_fixture':lines+=['**控制样例：不是实际部署或线上修复结果。**','']
 elif result['run_kind']=='historical_replay':lines+=['**历史证据重放：未重新检查线上。**','']
 lines += [f"声明 {result['coverage']['declared_issues']} 个问题，载入 {result['coverage']['loaded_issues']} 个，{result['coverage']['cases']} 个验收用例。",'', '[完整证据](report.json) · [验收结论](rechecks.csv) · [逐项前后对照](cases.csv) · [历史](recheck-history.csv)','', '| 原问题ID | 规则 | 状态 | 声明范围已验证修复 | 引擎恢复 |','|---|---|---|---|---|']
 for r in result['rechecks']:lines.append('| '+' | '.join(md(v) for v in [r['issue_id'],r['rule'],r['status'],r['repair_verified'],r['engine_state']])+' |')
 for r in result['rechecks']:
  lines += ['', '## '+md(r['issue_id']),'',f"原报告：{md(r['source_report'])}；原范围：{md(r['scope_type'])}；部署时间：{md(r['deployment_at'])}",'']
  lines += ['引擎观察：'+md(r.get('engine_observations',[])),'']
  for c in r['cases']:
   lines += [f"### {md(c['case_id'])}",'',f"{md(c['url'])} · {md(c['device'])} · JS {md(c['js'])} · {md(c['entry'])}",f"验收 {md(c['predicate'])}；本次状态 {md(c['current_status'])}；修复判定 {md(c['status'])}",f"修复前：{md(c['baseline'])}",'']
   for a in c['attempts']:lines.append('- '+md(a))
   lines+=['',f"缺口：{md(c['gaps'])}",'']
  lines.append('范围缺口：'+md(r['gaps']))
 lines+=['','## 数据缺口','']+['- '+md(g) for g in result['gaps']]+['','## 边界','']+['- '+md(v) for v in result['limitations']]+['']
 (output/'report.md').write_text('\n'.join(lines))
