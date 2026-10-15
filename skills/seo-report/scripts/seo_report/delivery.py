
import sys as _site_sys
from pathlib import Path as _SitePath
_site_dependency=_SitePath(__file__).resolve().parents[3]/'seo-crawlability/scripts'
if str(_site_dependency) not in _site_sys.path:_site_sys.path.insert(0,str(_site_dependency))
from crawlability.site import get_profile,site_host,site_origin,allowed_hosts,in_scope,require_url,brand_name,business_profile
import csv, hashlib, html, json, pathlib
from .core import canonical, digest
LABELS={'confirmed':'已确认技术观察','review':'待专业确认','evidence_gap':'证据缺口','environment_limited':'环境受限观察','platform_observation':'平台观察'}
def esc(x):return html.escape(str(x),quote=True).replace("\n","<br/>")
def table(headers,rows):
 return '<table><thead><tr>'+''.join('<th>'+esc(h)+'</th>' for h in headers)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+esc(c)+'</td>' for c in row)+'</tr>' for row in rows)+'</tbody></table>'
def bounded(value,limit=1800):
 s=canonical(value)
 return s if len(s)<=limit else s[:limit]+'…【截断；完整内容见 report.json】'
def evidence_hint(f):
 e=f.get('evidence') or f.get('link_occurrences') or []
 return f'证据项 {len(e)}；摘录：'+bounded(e,700)+'；完整结构见源报告与本地 report.json。'
def documents(r):
 report={'key':'report-'+r['run_id'],'title':site_host()+' SEO · '+r['run_id']+' · 现有审查结果汇总','mutable':False,'sections':[]}
 report['sections'].append({'key':'scope','xml':'<p>'+esc('现有审查结果汇总；本轮未重新扫描全站。生成时间 '+r['at']+'；源报告时间范围 '+str(r['source_report_window'])+'。缺失技能 '+str(r['missing_skills'])+'。源报告SHA已核对，底层网页证据未全部重验。')+'</p>'})
 report['sections'].append({'key':'counts','xml':table(['记录类别','数量（不是根因数/受影响页面数）'],[(LABELS.get(k,k),v) for k,v in r['counts'].items()])})
 for s in r['sources']:
  key='source-'+s['skill']+'-'+s['sha256'][:12]
  report['sections'].append({'key':key,'xml':table(['来源 '+s['skill'],'内容'],[['源报告',s['path']],['时间与SHA',s['at']+' / '+s['sha256']],['记录数',s['finding_count']],['覆盖',bounded(s['coverage'])],['缺口',str(len(s['gaps'])+len(s['input_gaps']))+' 项；'+bounded(s['gaps']+s['input_gaps'])],['限制',bounded(s['limitations'])]])})
 checked=[i for i in r['issues'] if i.get('recheck')]
 if checked:report['sections'].append({'key':'rechecks','xml':table(['原问题ID / URL','最新复查','处理要求'],[(i['issue_id']+' / '+str(i['url']),i['recheck']['status'],'网页复查与引擎恢复分别判断；不自动关闭。') for i in checked])})
 focus=sorted(r['issues'],key=lambda i:(0 if (i.get('recheck') or {}).get('status')=='failed' else 1 if i['category']=='confirmed' else 2,i['source_skill'],i['issue_id']))
 focus=[i for i in focus if (i.get('recheck') or {}).get('status')=='failed' or i['category']=='confirmed'][:12]
 if focus:report['sections'].append({'key':'focus','xml':table(['重点复查 / 已确认观察（最多12条；非根因排序）','处理方向'],[(i['issue_id']+' / '+str(i['url'])+' / '+i['rule'],i['finding'].get('recommendation','待主责技能补充')) for i in focus])})
 ledger={'key':'ledger','title':site_host()+' SEO · 持久问题台账','mutable':True,'sections':[]}
 # Stable per-skill buckets keep updates bounded. Membership is URL-independent and never truncates rows.
 groups={}
 for i in r['issues']:
  bucket=hashlib.sha256(i['issue_id'].encode()).hexdigest()[0];key=i['source_skill']+'-'+bucket;groups.setdefault(key,[]).append(i)
 for key,issues in sorted(groups.items()):
  rows=[]
  for i in sorted(issues,key=lambda i:i['issue_id']):
   f=i['finding'];rc=i.get('recheck');rows.append([
    'ID: '+i['issue_id']+'; '+i['rule']+'\n'+str(i['url']),
    LABELS.get(i['category'],i['category'])+' / '+str(f.get('classification',f.get('certainty','unknown')))+'\n'+('本轮出现' if i['seen_in_run'] else '历史保留，本轮未见')+'；复查 '+(rc['status'] if rc else '未执行'),
    '首次 '+i['first_seen']+'\n末次 '+i['last_seen'],
    f.get('recommendation','待主责技能提出有证据的修复方向')+'\n验收：'+f.get('retest','需按原问题补充修复前后证据，不自动关闭')+'\n'+evidence_hint(f)+'\n源报告 '+i['source']['path']+' SHA256 '+i['source']['sha256']])
  ledger['sections'].append({'key':key,'xml':table(['问题 / 精确URL','分类 / 复查','记录时间','解决方向与证据'],rows)})
 return {'report':report,'ledger':ledger}
def csv_safe(v):
 s='' if v is None else str(v)
 return "'"+s if s.lstrip().startswith(('=','+','-','@')) or s.startswith(('\t','\r','\n')) else s
def write_outputs(r,directory):
 p=pathlib.Path(directory)
 if p.exists():raise ValueError('new output directory required')
 p.mkdir(parents=True);(p/'report.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
 docs=documents(r);(p/'publication.json').write_text(json.dumps(docs,ensure_ascii=False,indent=2)+'\n')
 with (p/'issues.csv').open('w',newline='') as f:
  w=csv.writer(f);w.writerow(['issue_id','source_skill','url','rule','category','first_seen','last_seen','recheck','recommendation'])
  for i in r['issues']:w.writerow([csv_safe(v) for v in [i['issue_id'],i['source_skill'],i['url'],i['rule'],i['category'],i['first_seen'],i['last_seen'],(i.get('recheck') or {}).get('status'),i['finding'].get('recommendation')]])
 text=['# '+site_host()+' SEO · 现有审查结果汇总','',f"汇总时间：{r['at']}。源报告范围：{r['source_report_window']}。",'',*r['notes'],'','## 分类数量（不是根因数）','']
 text.extend(f'- {LABELS.get(k,k)}：{v}' for k,v in r['counts'].items());text+=['','缺失技能：'+str(r['missing_skills']),'','## 来源与覆盖','']
 for s in r['sources']:text += [f"### {s['skill']} · {s['at']}",'',f"来源 `{s['path']}` / SHA256 `{s['sha256']}`",'',canonical(s['coverage']),'',f"缺口 {len(s['gaps'])}；输入缺口 {len(s['input_gaps'])}。完整内容见 report.json。",'']
 text+=['## 最新复查','']
 for i in r['issues']:
  if i.get('recheck'):text += [f"- {i['issue_id']}：{i['recheck']['status']}；{i['url']}"]
 text+=['','全部记录、精确URL、首次/末次时间与修复方向见 issues.csv；每项原始证据结构保留在 report.json。']
 (p/'report.md').write_text('\n'.join(text)+'\n')
