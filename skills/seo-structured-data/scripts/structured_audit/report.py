"""Readable four-layer report, complete entities, edges and original observations."""

import sys as _site_sys
from pathlib import Path as _SitePath
_site_dependency=_SitePath(__file__).resolve().parents[3]/'seo-crawlability/scripts'
if str(_site_dependency) not in _site_sys.path:_site_sys.path.insert(0,str(_site_dependency))
from crawlability.site import get_profile,site_host,site_origin,allowed_hosts,in_scope,require_url,brand_name,business_profile
import json
from pathlib import Path
from . import shared
from crawlability.report import md,csv_file

def write_report(output,result,history):
    output=Path(output)
    if output.exists() and any(output.iterdir()):raise ValueError('output_directory_not_empty')
    output.mkdir(parents=True,exist_ok=True)
    for name,data in [('report.json',result),('entities.json',result['entity_inventory']),('examples.json',result['examples']),('engine-evidence.json',result['engine_results']),('issue-history.json',history)]:
        (output/name).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    csv_file(output/'coverage.csv',result['rows'],['url','snapshot_id','entry_mode','representation','status','entities','extraction_complete','profile','layers'])
    csv_file(output/'findings.csv',result['findings'],['issue_id','url','rule','layer','classification','entity','field','value','source_url','recommendation','retest','evidence'])
    csv_file(output/'graph-edges.csv',result['graph_edges'],['url','snapshot_id','syntax','from_entity','to_entity','reference_path','relationship'])
    csv_file(output/'issue-history.csv',history,['issue_id','first_seen','last_seen','status','sightings','payload'])
    def short(value,limit=600):
        text=value if isinstance(value,str) else json.dumps(value,ensure_ascii=False,sort_keys=True)
        return md(text[:limit]+'…（完整内容见JSON）' if len(text)>limit else text)
    c=result['coverage'];lines=['# '+site_host()+' 008：结构化数据与实体图审查','',f"审查时点：{md(result['at'])}",'',
        f"指定 {c['requested_urls']} 个URL；就绪DOM {c['ready_documents']} 份；三种语法提取完整 {c['complete_extractions']} 份。",'',
        '语法、Schema用法、引擎资格和实际展示分别记录。本地字段规则与词汇核验不等于完整Schema认证或搜索引擎测试；富媒体结果不保证展示。','',
        '[完整证据](report.json) · [逐项记录](findings.csv) · [实体](entities.json) · [引用图边](graph-edges.csv) · [修正示例](examples.json) · [引擎及历史证据](engine-evidence.json)','',
        '## 覆盖与四层结论','']
    for row in result['rows']:lines.append(f"- {md(row['url'])} · {md(row['entry_mode'])} · {md(row['representation'])}：{md(row['status'])}；{short(row['layers'])}")
    groups={}
    for f in result['findings']:groups.setdefault((f['rule'],f['layer'],f['classification']),[]).append(f)
    lines+=['','## 发现与修复','',f"共 {len(result['findings'])} 条记录，包含规则观察、重复候选和待审项；不等于相同数量的已确认SEO故障。",'']
    for (rule,layer,classification),items in groups.items():
        lines += [f"### {md(rule)} · {md(layer)} · {md(classification)}",'',f"{len(items)} 条，最多展示3条，完整条目见CSV/JSON。",'']
        for f in items[:3]:
            lines += [f"- {md(f['url'])}；ID：{md(f['issue_id'])}",f"  - 实体/字段：{short(f['entity'])} / {short(f['field'])}",f"  - 实际值：{short(f['value'])}",f"  - 建议：{short(f['recommendation'])}",f"  - 复测：{short(f['retest'])}",f"  - 证据：{short(f['evidence'])}"]
            if f.get('source_url'):lines.append('  - 规则来源：'+md(f['source_url']))
        lines.append('')
    lines+=['## 修正示例和历史状态','',f"有事实绑定的数值格式示例 {len(result['examples'])} 条；仅适用于采集时点，不应硬编码动态价格。",'']
    for example in result['examples'][:10]:lines.append('- '+short(example,1000))
    for engine in result['engine_results']:
        lines.append('- '+short({'url':engine['url'],'engine_validation':engine['engine_validation'],'actual_display':engine['actual_display'],'history':engine['history']},1000))
    lines+=['','历史“本轮范围未复现”不代表平台已重抓或问题已关闭；当前缺少实体/检查范围时保留未验证。','',
        '## 待审及证据缺口','']
    for row in result['pending_reviews'][:10]:lines.append('- '+short(row))
    gaps=result['gaps']+result.get('input_gaps',[])
    lines.append(f'- 证据缺口 {len(gaps)} 条（前20条如下，全部见完整证据）：')
    lines.extend('- '+short(g) for g in gaps[:20])
    lines+=['','不将同一@id的合法引用判错，不将末级面包屑缺item批量判错，不自动给币种介绍页套购物资格，不补造评分或收益信息。','',
        '参考：[Schema.org](https://schema.org/docs/datamodel.html)、[Google结构化数据政策](https://developers.google.com/search/docs/appearance/structured-data/sd-policies)、[extruct](https://github.com/scrapinghub/extruct)。','']
    (output/'report.md').write_text('\n'.join(lines),encoding='utf-8')
