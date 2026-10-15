"""Readable platform observations and lossless JSON, with CSV injection protection."""

import sys as _site_sys
from pathlib import Path as _SitePath
_site_dependency=_SitePath(__file__).resolve().parents[3]/'seo-crawlability/scripts'
if str(_site_dependency) not in _site_sys.path:_site_sys.path.insert(0,str(_site_dependency))
from crawlability.site import get_profile,site_host,site_origin,allowed_hosts,in_scope,require_url,brand_name,business_profile
import json
from pathlib import Path
from . import contracts
from crawlability.report import md,csv_file
LABELS={'historical_generic_failure_not_reproduced':'历史笼统抓取失败，本次普通HTTP未复现；原失败状态码未知','historical_error_not_reproduced':'历史HTTP错误本次未复现，未确认Bing修复','failure_reproduced_at_http_layer':'当前HTTP复现同类失败','engine_live_failure_public_http_success':'Bing实时失败、普通HTTP成功：客户端差异待定位','engine_and_public_access_limited':'Bing实时和普通HTTP均访问受限','current_access_limited':'当前普通HTTP访问受限','different_landing_unverified':'当前落点已变化，原URL/目标关系待核验','index_snapshot_unavailable':'缺少精确URL与设备的Bing索引快照','current_http_unavailable':'缺少同URL、设备的当前HTTP证据','conflicting_index_snapshots':'同一时点索引证据冲突','conflicting_public_observations':'同一时点公共HTTP证据冲突','conflicting_engine_live_observations':'同一时点Bing实时证据冲突','observations_available_requires_specialist_review':'对照证据可用，专业核验结论另列'}
def write_report(output,result,history):
 output=Path(output)
 if output.exists() and any(output.iterdir()):raise ValueError('output_directory_not_empty')
 output.mkdir(parents=True,exist_ok=True)
 for n,d in [('report.json',result),('checks.json',result['checks']),('issue-history.json',history),('referrals.json',result['referrals'])]:(output/n).write_text(json.dumps(d,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
 csv_file(output/'findings.csv',result['findings'],['issue_id','site','url','rule','classification','observation_modes','recommendation','retest','evidence'])
 csv_file(output/'issue-history.csv',history,['issue_id','first_seen','last_seen','status','sightings','payload'])
 c=result['coverage'];lines=['# '+site_host()+' 015 · Bing Webmaster 审查','',f"站点：{md(result['site'])}；审查时点：{md(result['at'])}",'',f"声明 {c['declared_urls']} 个 URL、{c['declared_variants']} 个组合；索引快照 {c['index_snapshots']} 个组合，可与普通 HTTP 对照 {c['paired_variants']} 个组合。",'',f"{len(result['findings'])} 条平台观察，{len(result['gaps'])} 条证据缺口。平台观察不是已确认网站根因，数量不等于独立受影响页面。",'', '[完整证据](report.json) · [逐URL对照](checks.json) · [问题](findings.csv) · [历史](issue-history.csv) · [转交](referrals.json)','', '## 逐 URL 对照','', '| URL | 设备 | 对照结论 | 索引证据 | Bing实时证据 | 普通HTTP证据 |','|---|---|---|---|---|---|']
 if result['run_kind']=='controlled_fixture':lines[2:2]=['**控制样例：不是当前 Bing 后台或网站实际状态。**','']
 elif result['run_kind']=='historical_replay':lines[2:2]=['**历史证据重放：不是重新读取的当前后台状态。**','']
 for x in result['checks']:lines.append('| '+' | '.join(md(v) for v in [x['url'],x['device'],LABELS.get(x['comparison'],x['comparison']),x['engine_evidence'],x['engine_live_evidence'],x['live_evidence']])+' |')
 lines+=['','UNKNOWN 表示设备无法确定；即使键可配对，也不宣称普通请求与 Bing 测试的网络/客户端条件一致。','', '## 已读取报告','']
 for p in result['platform_reports']:
  if p['kind']=='ui_report':lines.append(f"- {md(p['report'])}：数据日期 {md(p.get('report_date'))}；数量 {md(p.get('reported_total'))}，单位 {md(p.get('count_unit'))}；筛选 {md(p.get('filters'))}；扫描 {md(p.get('scan'))}。")
  else:lines.append(f"- {md(p['kind'])}，证据 {md(p['evidence_id'])}；API 顶部记录不构成全站 URL 库存。")
 lines+=['','## 观察、证据与处理方向','']
 for f in result['findings']:
  lines += [f"### {md(f['rule'])}",'',f"URL：{md(f['url']) if f['url'] else '报表级观察，未绑定具体URL'}",f"稳定 ID：{f['issue_id']}",f"分类：{md(f['classification'])}；来源模式：{md(f['observation_modes'])}",'',md(f['recommendation']),'',f"复核：{md(f['retest'])}",'']
  for e in f['evidence']:
   lines.append(f"- {md(e['evidence_id'])}；采集 {md(e['captured_at'])}；模式 {md(e['mode'])}；proof {md(e['proof'].get('path'))}，SHA256 {md(e['proof']['sha256'])}。")
   for row in e['observation'].get('rows',[]):
    if row.get('url')==f['url'] and row.get('reason_key')==f['rule']:lines.append('  原文：'+md(row['quote']))
   i=e['observation'].get('inspection')
   if i and i['url']==f['url']:
    for name,binding in i.get('field_bindings',{}).items():lines.append('  '+md(name)+'：'+md(binding['quote']))
  lines.append('')
 lines+=['## 覆盖缺口','']+['- '+md(g) for g in result['gaps']]+['','## 判断边界','']+['- '+md(v) for v in result['limitations']]+['','未执行的专业转交仍待核验；缺席、提交成功或当前可访问均不自动关闭历史问题。','']
 (output/'report.md').write_text('\n'.join(lines))
