"""Phase comparisons, path coverage and persistent findings for 005."""

import sys as _site_sys
from pathlib import Path as _SitePath
_site_dependency=_SitePath(__file__).resolve().parents[3]/'seo-crawlability/scripts'
if str(_site_dependency) not in _site_sys.path:_site_sys.path.insert(0,str(_site_dependency))
from crawlability.site import get_profile,site_host,site_origin,allowed_hosts,in_scope,require_url,brand_name,business_profile
import json
from pathlib import Path
from . import shared
from crawlability.report import csv_file,md

def write_report(output,result,history):
    output=Path(output)
    if output.exists() and any(output.iterdir()):raise ValueError('output_directory_not_empty')
    output.mkdir(parents=True,exist_ok=True)
    for filename,data in [('report.json',result),('issue-history.json',history)]:
        (output/filename).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    coverage=[{'url':r['url'],'entry_mode':r['entry_mode'],'readiness':r['readiness']['state'],
        'unmet':r['readiness']['unmet'],'initial':r['initial'],'rendered':r['rendered'],
        'baseline_relation':r.get('baseline_relation'),'comparison_fields':r['comparison_fields'],'unchecked_fields':r['unchecked_fields']} for r in result['rows']]
    csv_file(output/'coverage.csv',coverage,['url','entry_mode','readiness','unmet','baseline_relation','comparison_fields','unchecked_fields','initial','rendered'])
    csv_file(output/'changes.csv',result['changes'],['url','entry_mode','field','change','baseline_relation','before','after','evidence'])
    csv_file(output/'interactions.csv',result['interactions'],['id','url','kind','verification','comparison','readiness','before_id','after_id','before_page','after_page','before_items','after_items','source','checked_at','evidence'])
    csv_file(output/'findings.csv',result['findings'],['issue_id','url','entry_mode','rule','classification','observed_at','recommendation','evidence'])
    csv_file(output/'issue-history.csv',history,['issue_id','first_seen','last_seen','status','sightings','payload'])
    totals=result['coverage']
    lines=['# '+site_host()+' 005：JavaScript 渲染与交互审查','',f"审查时点：{md(result['at'])}",'',
        f"指定 {totals['requested_urls']} 个 URL；{totals['ready_paths']} 条进入路径取得就绪观察。未声明全站覆盖。",'',
        '初始HTML、浏览器字段快照和完整DOM分别记录。网络空闲不等于页面就绪；HTTP成功不等于实际渲染正确。正常补全与故障候选分开，未知/截断字段不当作内容缺失。','',
        '## 路径与证据覆盖','', '| URL | 进入方式 | 就绪状态 | 未满足条件 | 未检查字段 |','|---|---|---|---|---|']
    for row in coverage:lines.append('| '+' | '.join(md(row[k]) for k in ['url','entry_mode','readiness','unmet','unchecked_fields'])+' |')
    lines+=['','## 阶段变化','']
    for change in result['changes']:
        lines += [f"- {md(change['url'])} · {md(change['entry_mode'])} · {md(change['change'])}（基线关系：{md(change.get('baseline_relation'))}）：{md(change['before'])} → {md(change['after'])}"]
    lines+=['','## 实际交互','']
    for event in result['interactions']:
        lines += [f"- {md(event.get('id'))} · {md(event.get('kind'))} · {md(event.get('verification'))}",f"  前后对照：{md(event.get('comparison'))}",f"  就绪证据：{md(event.get('readiness'))}"]
    lines+=['','## 发现及建议','']
    for finding in result['findings']:
        lines += [f"### {md(finding['rule'])}",'',f"URL：{md(finding['url'])}",f"问题ID：{md(finding['issue_id'])}",f"分类：{md(finding['classification'])}",'',md(finding['recommendation']),'',f"证据：{md(finding['evidence'])}",'']
    lines+=['## 缺口与边界','',f"未覆盖路径：{md(totals['missing_entry_modes'])}",'',f"输入缺口：{md(result.get('input_gaps',[]))}",'',
        '只对已观察的公开分页、筛选、内链和返回进行比较；操作尝试不能替代前后快照。未发生的新证据不会自动关闭历史问题。此报告不证明真实搜索引擎已渲染或索引。','',
        '规则背景：[Google JavaScript SEO基础](https://developers.google.com/search/docs/crawling-indexing/javascript/javascript-seo-basics)。','']
    (output/'report.md').write_text('\n'.join(lines),encoding='utf-8')
