
import sys as _site_sys
from pathlib import Path as _SitePath
_site_dependency=_SitePath(__file__).resolve().parents[3]/'seo-crawlability/scripts'
if str(_site_dependency) not in _site_sys.path:_site_sys.path.insert(0,str(_site_dependency))
from crawlability.site import get_profile,site_host,site_origin,allowed_hosts,in_scope,require_url,brand_name,business_profile
import json
from pathlib import Path
from collections import Counter
from . import shared
from crawlability.report import md,csv_file

def write_report(output,result,history):
    output=Path(output)
    if output.exists() and any(output.iterdir()):raise ValueError('output_directory_not_empty')
    output.mkdir(parents=True,exist_ok=True)
    for name,data in [('report.json',result),('issue-history.json',history),('regressions.json',result['comparison'])]:(output/name).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    groups=result['laboratory']['groups'];lab=[]
    for g in groups:lab.append({**{k:g[k] for k in ['requested_url','final_url','device','environment_key','n','sufficient','suitable_for_regression','environment_statuses']},**{m:v['median'] for m,v in g['metrics'].items()}})
    csv_file(output/'lab-matrix.csv',lab,['requested_url','final_url','device','n','sufficient','suitable_for_regression','environment_statuses','environment_key','LCP','CLS','TBT','FCP','SI','TTFB','INP'])
    csv_file(output/'field-matrix.csv',result['field_assessments'],['source','scope','key','device','collection_period','metrics','current_assessment','usable_for_current_assessment','gaps','evidence'])
    csv_file(output/'coverage.csv',result['coverage']['missing_cells'],['url','device','minimum_valid_runs'])
    csv_file(output/'findings.csv',result['findings'],['issue_id','url','device','rule','metric_or_audit','classification','recommendation','retest','evidence'])
    csv_file(output/'excluded-runs.csv',result['laboratory']['excluded'],['reason','run'])
    all_runs=[r for g in groups for r in g['runs']]+[e['run'] for e in result['laboratory']['excluded']]
    csv_file(output/'page-reviews.csv',all_runs,['run_id','requested_url','device','page_content_validity','page_review','page_review_evidence','evidence','exclusion'])
    csv_file(output/'issue-history.csv',history,['issue_id','first_seen','last_seen','status','sightings','payload'])
    c=result['coverage'];lines=['# '+site_host()+' 011：Core Web Vitals与性能审查','',f"审查时点：{md(result['at'])}",'',
        f"计划 {c['expected_cells']} 个URL×设备单元；可解析且目标匹配的实验室观察 {c['valid_lab_runs']} 次；未满足3次有效同环境样本的单元 {len(c['missing_cells'])} 个。",'',
        f"环境检查：{'计划范围未检出高负载，可作有条件回归比较' if c['reliable_lab_scope_complete'] else '尚未形成计划范围的可靠回归基线'}；受高负载或环境证据不足限制的组数 {len(c['environment_limited_groups'])}。这些组的数值保留作诊断观察，不输出确定的改善/回退结论。低负载也不自动证明全部外部干扰已消除。",'',
        '实验室LCP/CLS/TBT用于定位和回归；导航Lighthouse没有测得真实用户INP。真实用户数据按来源、URL/origin、设备与统计窗口单列。缺值不是0，origin数据不代替每个URL。','',
        f"业务页面复核：{'计划范围已逐次复核' if c['business_page_scope_complete'] else '未完成全部目标业务页面确认'}；尚未确认的有效测量 {len(c['unconfirmed_business_runs'])} 次。截图仅证明捕获时可见内容，不证明加载全过程无骨架屏或位移。",'',
        '[实验室矩阵](lab-matrix.csv) · [真实用户数据矩阵](field-matrix.csv) · [业务页面复核](page-reviews.csv) · [未完成单元](coverage.csv) · [失败/重复/不可比测量](excluded-runs.csv) · [全部问题](findings.csv) · [历史](issue-history.json)','',
        '## 实验室重复测量','', '以下为全部有效可比样本的中位数；时间单位毫秒，CLS无单位。未满足3次有效样本的行只作观察，不作为稳定基线。','',
        '| URL | 设备 | 有效次数 | LCP ms | CLS | TBT ms | 样本足够 | 环境可作回归 |','|---|---|---:|---:|---:|---:|---|---|']
    for r in lab:lines.append('| '+ ' | '.join(md(str(r[k])) for k in ['requested_url','device','n','LCP','CLS','TBT','sufficient','suitable_for_regression'])+' |')
    lines += ['',f"本轮实验室工程预算：{md(json.dumps(result['lab_budgets']))}。预算超出不等于搜索引擎判定CWV不通过；工具分数也不等于页面或业务内容正确。",'', '## 真实用户数据','']
    if not result['field_assessments']:lines+=['本轮未取得可解析的真实用户字段记录，保持未知。']
    for r in result['field_assessments']:
        lines += [f"- {md(r.get('scope'))}：{md(r.get('key'))}；{md(r.get('device'))}；来源 {md(r.get('source'))}",f"  - 窗口：{md(json.dumps(r.get('collection_period'),ensure_ascii=False))}",f"  - p75：{md(json.dumps(r.get('metrics'),ensure_ascii=False))}；本轮可采用结论：{md(r['current_assessment'])}"]
    lines += ['', 'PSI在INP样本不足而LCP/CLS良好时的特殊通过标为pass_inp_unavailable，不当成三指标均已观察。窗口不明、数据过期、API配额失败均保留未知。','', '## 问题与改进候选','']
    by_rule={}
    for f in result['findings']:by_rule.setdefault(f['rule'],[]).append(f)
    for rule,items in by_rule.items():
        lines += [f'### {md(rule)}','',f'{len(items)} 条记录；以下最多3条，完整资源/节点与原始报告关联见findings.csv。','']
        for f in items[:3]:
            evidence=json.dumps(f['evidence'],ensure_ascii=False);lines += [f"- {md(f['url'])} · {md(f['device'])} · {md(f['metric_or_audit'])} · {f['issue_id']}",f"  - 建议：{md(f['recommendation'])}",f"  - 复测：{md(f['retest'])}",f"  - 证据：{md(evidence[:1200])}"+('…' if len(evidence)>1200 else '')]
        lines.append('')
    lines += ['## 回归与边界','',f"同环境可比较组数：{len(result['comparison']['comparisons'])}。版本、设备、节流、缓存和主机环境改变时不强行给前后改善率。各审计项估算收益可能重叠，不能相加承诺。",'']
    lines += ['- '+md(x) for x in result['pending_reviews']]
    lines += ['', '证据缺口按原因汇总：','']+['- '+md(reason)+f'：{count}' for reason,count in Counter(str(g.get('reason')) for g in result['gaps']).most_common()]
    lines += ['', '相同稳定ID累计观察；本轮未见不自动关闭。真实用户窗口包含历史体验，部署后不会立即全部重置。','',
        '依据：[Web Vitals](https://web.dev/articles/vitals)、[PSI数据说明](https://developers.google.com/speed/docs/insights/v5/about)、[CrUX API](https://developer.chrome.com/docs/crux/api/)、[Lighthouse CI](https://github.com/GoogleChrome/lighthouse-ci)。','']
    (output/'report.md').write_text('\n'.join(lines),encoding='utf-8')
