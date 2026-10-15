"""Human report plus lossless JSON, CSV and durable issue-history view."""

import sys as _site_sys
from pathlib import Path as _SitePath
_site_dependency=_SitePath(__file__).resolve().parents[3]/'seo-crawlability/scripts'
if str(_site_dependency) not in _site_sys.path:_site_sys.path.insert(0,str(_site_dependency))
from crawlability.site import get_profile,site_host,site_origin,allowed_hosts,in_scope,require_url,brand_name,business_profile
import json
from pathlib import Path
from . import contracts
from crawlability.report import md,csv_file

STATUS_LABELS={
    'historical_error_not_reproduced':'历史错误本次未复现，Google 修复状态未确认',
    'failure_reproduced_at_http_layer':'当前 HTTP 层重现同类失败',
    'current_access_limited':'当前访问受限，不能判定全站故障',
    'different_landing_unverified':'实际落点变化，目标页面待验证',
    'platform_url_not_inspected':'未读取该 URL 的索引快照',
    'engine_device_unmatched':'引擎抓取设备无法匹配',
    'live_url_not_checked':'缺少同 URL、同设备当前证据',
    'conflicting_engine_snapshots':'同一时点的引擎证据冲突',
    'conflicting_live_observations':'同一时点的当前证据冲突',
    'observations_available_requires_specialist_review':'对照证据已备齐，专业结论另行核验'
}

def write_report(output,result,history):
    output=Path(output)
    if output.exists() and any(output.iterdir()):raise ValueError('output_directory_not_empty')
    output.mkdir(parents=True,exist_ok=True)
    for name,value in [('report.json',result),('checks.json',result['checks']),('issue-history.json',history),('referrals.json',result['referrals'])]:
        (output/name).write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
    csv_file(output/'findings.csv',result['findings'],['issue_id','property','url','report','rule','classification','recommendation','retest','evidence'])
    csv_file(output/'issue-history.csv',history,['issue_id','first_seen','last_seen','status','sightings','payload'])
    c=result['coverage'];lines=['# '+site_host()+' 014 Google Search Console 审查','',f"审查时点：{md(result['at'])}；资源：{md(result['property'])}",'',
      f"声明 {c['declared_urls']} 个 URL、{c['declared_variants']} 个 URL × 设备组合；已读取索引快照 {c['declared_urls_inspected']} 个声明 URL；当前 HTTP 观察 {c['live_declared_variants']} 个组合，可对照 {c['paired_variants']} 个组合。",'',
      f"平台观察去重 {len(result['findings'])} 条；证据缺口 {len(result['gaps'])} 条。这里的平台观察数不等于已确认网站故障数。",'',
      '报表样例数、页面数、结构化数据项目数和 CWV 分组数分别保留，不相加为受影响页面总数。','',
      '[逐 URL 对照](checks.json) · [完整证据与覆盖](report.json) · [问题清单](findings.csv) · [历史](issue-history.csv) · [专业转交](referrals.json)','',
      '## 逐 URL 对照','', '| URL | 设备 | 对照结果 | GSC 证据 | 当前证据 |','|---|---|---|---|---|']
    if result.get('run_kind')=='controlled_fixture':lines[2:2]=['**控制样例演练：不是线上 GSC 或目标网站实际状态。**','']
    elif result.get('run_kind')=='historical_replay':lines[2:2]=['**历史证据重放：不是本次重新读取的线上状态。**','']
    for r in result['checks']:lines.append('| '+' | '.join(md(x) for x in [r['url'],r['device'],STATUS_LABELS.get(r['comparison'],r['comparison']),r['engine_evidence'],r['live_evidence']])+' |')
    lines+=['','GSC 最后抓取与当前采集分别记录：','']
    for r in result['checks']:
        if r.get('last_google_crawl') or r.get('live_captured_at'):lines.append(f"- {md(r['url'])} / {md(r['device'])}：Google 最后抓取 {md(r.get('last_google_crawl'))}；当前 HTTP {md(r.get('live_http_status'))}，采集 {md(r.get('live_captured_at'))}。")
    lines+=['','## 已读取的平台报表','']
    for report in result['platform_reports']:
        if report.get('kind') in {'ui_report','live_test'}:lines.append(f"- {md(report['report'])}：数据日期 {md(report.get('report_date'))}；报告数量 {md(report.get('reported_total'))}，单位 {md(report.get('count_unit'))}；实际读取的 URL 样例 {md(report.get('observed_url_examples'))}。")
        elif report.get('kind')=='submitted_sitemaps':lines.append(f"- 已提交 Sitemap 响应包含 {len(report['entries'])} 条记录；不是全站 Sitemap 库存。")
    lines+=['','## 平台观察与处理方向','']
    for f in result['findings']:
        lines += [f"### {md(f['rule'])} — {md(f['classification'])}",'',f"URL：{md(f['url']) if f['url'] else '报表级观察，未绑定具体 URL'}",f"稳定问题 ID：{f['issue_id']}",'',md(f['recommendation']),'',f"复测：{md(f['retest'])}",'']
        for e in f['evidence']:
            lines.append(f"- 原始证据 {md(e['evidence_id'])}；采集 {md(e['captured_at'])}；模式 {md(e.get('observation_mode'))}；SHA256 {md(e['proof']['sha256'])}")
            for row in e['observation'].get('rows',[]):
                if row.get('url')==f['url'] and row.get('reason_key')==f['rule']:
                    lines.append(f"  原文：{md(row['quote'])}")
        lines.append('')
    lines+=['## 搜索表现对照','']
    for comparison in result.get('performance_comparisons',[]):
        v=comparison['result'];lines += [f"证据 {md(comparison['before_evidence'])} → {md(comparison['after_evidence'])}；只比较两窗口都出现的行，缺失行不算零。",'']
        for row in v['matched_rows']:
            lines.append('- '+md(json.dumps({'dimensions':row['dimensions'],'clicks_delta':row['clicks_delta'],'impressions_delta':row['impressions_delta'],'ctr_percentage_point_delta':row['ctr_percentage_point_delta'],'position_delta':row['position_delta']},ensure_ascii=False)))
        lines += ['','这些变化不证明全站流量变化或具体故障因果关系。','']
    lines+=['## 证据缺口','']
    for g in result['gaps']:lines.append('- '+md(json.dumps(g,ensure_ascii=False)))
    lines+=['','## 判断边界','']+['- '+md(x) for x in result['limitations']]
    lines+=['','未发现新的观察不代表旧问题已解决；首次和最后发现时间保存在问题历史中。','']
    (output/'report.md').write_text('\n'.join(lines))
