"""Evidence-led Chinese report and interoperable structured artifacts."""

import sys as _site_sys
from pathlib import Path as _SitePath
_site_dependency=_SitePath(__file__).resolve().parents[3]/'seo-crawlability/scripts'
if str(_site_dependency) not in _site_sys.path:_site_sys.path.insert(0,str(_site_dependency))
from crawlability.site import get_profile,site_host,site_origin,allowed_hosts,in_scope,require_url,brand_name,business_profile
import json
from pathlib import Path
from . import contracts
from crawlability.report import md,csv_file
LABELS={'historical_http_failure_not_reproduced':'历史HTTP故障本次未复现；未确认引擎恢复','index_snapshot_unavailable':'缺少同URL/设备/JS模式的搜索状态快照','current_http_unavailable':'缺少当前普通HTTP证据','different_landing_unverified':'当前最终落点不同，路由等价性待核验','http_failure_reproduced':'当前HTTP层仍复现错误','engine_live_failed_public_http_success':'引擎实时失败、普通HTTP成功，客户端差异待核验','engine_and_public_access_limited':'引擎实时与普通HTTP均访问受限','observations_available_requires_specialist_review':'对照证据已取得，专业内容与索引意图另行核验'}
def write_report(output,result,history):
 output=Path(output)
 if output.exists() and any(output.iterdir()):raise ValueError('output_directory_not_empty')
 output.mkdir(parents=True,exist_ok=True)
 for name,v in [('report.json',result),('checks.json',result['checks']),('issue-history.json',history),('referrals.json',result['referrals'])]:(output/name).write_text(json.dumps(v,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
 csv_file(output/'findings.csv',result['findings'],['issue_id','host_id','url','rule','group_id','classification','owner_skill','recommendation','retest','evidence'])
 csv_file(output/'issue-history.csv',history,['issue_id','first_seen','last_seen','status','sightings','payload'])
 c=result['coverage'];lines=['# '+site_host()+' 016 · Yandex Webmaster 审查','',f"Host：{md(result['host_id'])}；采集比较时点：{md(result['at'])}",'']
 if result['run_kind']=='controlled_fixture':lines+=['**控制样例：不是实际网站检查。**','']
 elif result['run_kind']=='historical_replay':lines+=['**历史证据重放：未重新读取当前平台。**','']
 lines += [f"声明 {c['declared_urls']} 个 URL／{c['declared_variants']} 个环境组合；搜索状态快照 {c['index_snapshots']}；当前HTTP配对 {c['paired_variants']}。",f"平台观察 {len(result['findings'])} 条，证据缺口 {len(result['gaps'])} 条；这些数量不是网站根因数或全站受影响页面总数。",'', '[证据与原始字段](report.json) · [逐URL对照](checks.json) · [问题清单](findings.csv) · [历史](issue-history.csv) · [专业转交](referrals.json)','', '## 逐 URL 对照','', '| URL | 设备 | JS | 搜索快照 | 比较结果 | 证据：数据库／实时／HTTP |','|---|---|---|---|---|---|']
 for x in result['checks']:lines.append('| '+' | '.join(md(v) for v in [x['url'],x['device'],x['js'],x['searchable'],LABELS.get(x['comparison'],x['comparison']),[x['engine_evidence'],x['engine_live_evidence'],x['http_evidence']]])+' |')
 lines+=['','## 数据源与时间','']
 for e in result['platform_reports']:lines.append(f"- {md(e['id'])}：{md(e['report'])}；模式 {md(e['mode'])}；采集 {md(e['captured_at'])}；数据库日期 {md(e.get('database_date'))}；proof {md(e['source'])}；筛选 {md(e.get('filters'))}。")
 lines+=['','## 平台观察与修复方向','']
 for f in result['findings']:
  lines += [f"### {md(f['rule'])}",'',f"ID：{f['issue_id']}；URL：{md(f['url']) if f['url'] else '报表级，未绑定具体URL'}；主责 {f['owner_skill']}",f"分类：{md(f['classification'])}；已确认网站缺陷：{md(f['verified_site_defect'])}",'',md(f['recommendation']),'',md(f['retest']),'']
  for e in f['evidence']:lines += [f"- {md(e['id'])} · {md(e['mode'])} · {md(e['captured_at'])} · {md(e['source'])}", '  原始观察：'+md(e['row'])]
  lines.append('')
 lines+=['## 覆盖缺口','']+['- '+md(g) for g in result['gaps']]+['','## 判断边界','']+['- '+md(v) for v in result['limitations']]+['']
 (output/'report.md').write_text('\n'.join(lines))
