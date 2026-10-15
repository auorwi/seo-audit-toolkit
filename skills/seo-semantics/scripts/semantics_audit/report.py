"""Keep conformance, accessibility, semantic reviews and evidence gaps distinct."""

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
    for name,data in [('report.json',result),('issue-history.json',history),('pending-reviews.json',result['pending_reviews'])]:
        (output/name).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    csv_file(output/'coverage.csv',result['rows'],['url','source_capture','rendered_capture','browser_state','tools'])
    csv_file(output/'findings.csv',result['findings'],['issue_id','url','rule','classification','impact_domain','owner_skill','observed_at','recommendation','retest','evidence'])
    csv_file(output/'handoffs.csv',result['handoffs'],['owner_skill','url','rule','question','alt_state','locator','target','html','snapshot_id','document_sha256'])
    csv_file(output/'issue-history.csv',history,['issue_id','first_seen','last_seen','status','sightings','payload'])
    c=result['coverage']
    def short(value,limit=700):
        text=value if isinstance(value,str) else json.dumps(value,ensure_ascii=False,sort_keys=True)
        return md(text if len(text)<=limit else text[:limit]+'…（完整内容见JSON）')
    lines=['# '+site_host()+' 006：语义化结构审查','',f"审查时点：{md(result['at'])}",'',
        f"指定 {c['requested_urls']} 个URL；就绪浏览器文档 {c['ready_documents']} 份；可用校验器结果 {c['usable_tool_runs']} 份。",'',
        'HTML规范、可访问性规则、最佳实践和语义待审分别标注。无H1/多个H1不作为收录硬规则；自动检查不等于完整可访问性认证。','',
        '[完整证据](report.json) · [逐元素记录](findings.csv) · [覆盖清单](coverage.csv) · [历史](issue-history.csv)','',
        '## 检查覆盖','']
    for row in result['rows']:
        tools='；'.join(str(t['tool'])+': '+str(t['status'])+' ('+str(t.get('checker_version','版本未知'))+')' for t in row['tools'])
        lines.append(f"- {md(row['url'])}：{md(tools)}")
    groups={}
    for finding in result['findings']:
        groups.setdefault((finding['rule'],finding['classification']),[]).append(finding)
    lines+=['','## 发现与复测','',f"共 {len(result['findings'])} 条记录，按规则与分类汇成 {len(groups)} 组。记录包含最佳实践和待审项，不等于相同数量的SEO故障。",'']
    for (rule,classification),items in groups.items():
        lines += [f"### {md(rule)} · {md(classification)}",'',f"{len(items)} 条记录；以下最多展示3条，其余见逐元素记录。",'']
        for finding in items[:3]:
            lines += [f"- URL：{md(finding['url'])}；ID：{md(finding['issue_id'])}",f"  - 建议：{short(finding['recommendation'])}",f"  - 复测：{short(finding['retest'])}"]
            for evidence in finding.get('evidence',[])[:2]:
                element=evidence.get('element') or {}
                location=evidence.get('target') or evidence.get('location') or element.get('selector') or evidence.get('locator')
                message=evidence.get('message') or evidence.get('review',{}).get('reason')
                snippet=evidence.get('html') or element.get('snippet')
                if location:lines.append('  - 位置：'+short(location,400))
                if message:lines.append('  - 依据：'+short(message))
                if snippet:lines.append('  - 片段：'+short(snippet,500))
                provenance=evidence.get('provenance',evidence)
                if provenance.get('document_sha256'):lines.append('  - 文档SHA256：'+md(provenance['document_sha256']))
            if len(finding.get('evidence',[]))>2:lines.append('  - 多处重复证据完整保留在report.json。')
        lines.append('')
    lines+=['## 人工语义评审与媒体交接','']
    for row in result['pending_reviews']:
        lines.append(f"- {md(row['url'])}：全页待审 {short(row['topics'])}；已有局部评审 {short(row.get('reviewed_topics',[]))}。")
    lines += ['',f"媒体交接 {len(result['handoffs'])} 条，见[交接清单](handoffs.csv)。空alt先确认装饰或信息用途；交013共享，不在006重复登记同一图片问题。局部语义评审不自动清空全页待审范围。",'',
        '## 证据缺口','']
    gaps=result['gaps']+result.get('input_gaps',[])
    lines.append(f'共 {len(gaps)} 条；缺口不计为网站错误。')
    lines.extend('- '+short(g) for g in gaps[:20])
    if len(gaps)>20:lines.append('其余缺口见完整证据。')
    lines+=['','同问题跨周期更新，未出现不自动关闭历史问题。','',
        '规则来源：[Nu Html Checker](https://github.com/validator/validator)、[axe-core](https://github.com/dequelabs/axe-core)。','']
    (output/'report-details.md').write_text('\n'.join(lines),encoding='utf-8')
    from .page_report import render_checklist
    render_checklist(output,result)
