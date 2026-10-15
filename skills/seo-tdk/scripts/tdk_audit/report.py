"""Readable summaries with complete machine-readable evidence and drafts."""

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
    for name,data in [('report.json',result),('drafts.json',{'drafts':result['drafts'],'withheld':result['withheld_drafts']}),('issue-history.json',history)]:
        (output/name).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    csv_file(output/'coverage.csv',result['rows'],['url','snapshot_id','status','representation','lengths','keywords_inventory','rewrite_blocked'])
    csv_file(output/'findings.csv',result['findings'],['issue_id','url','rule','field','classification','original','template','language','recommendation','retest','evidence'])
    csv_file(output/'duplicate-clusters.csv',result['duplicate_clusters'],['cluster_id','field','language','normalized_value','classification','members','recommendation'])
    csv_file(output/'handoffs.csv',result['handoffs'],['owner_skill','url','rule','recommendation','evidence'])
    csv_file(output/'issue-history.csv',history,['issue_id','first_seen','last_seen','status','sightings','payload'])
    def short(value,limit=600):
        text=value if isinstance(value,str) else json.dumps(value,ensure_ascii=False,sort_keys=True)
        return md(text[:limit]+'…（完整内容见JSON）' if len(text)>limit else text)
    c=result['coverage'];lines=['# '+site_host()+' 007：TDK与搜索意图审查','',f"审查时点：{md(result['at'])}",'',
        f"指定 {c['requested_urls']} 个URL；就绪DOM {c['ready_pages']} 个；仅原始HTML {c['source_only_pages']} 个；可聚类样本 {c['cluster_eligible_pages']} 个。",'',
        '发现记录含改写待审、显示提醒和重复候选，不等于相同数量的SEO故障。缺description不等于不能收录；长度不设硬性通过线；meta keywords仅盘点，不安排补写。','',
        '[完整证据](report.json) · [逐项记录](findings.csv) · [重复聚类](duplicate-clusters.csv) · [草稿及拦截](drafts.json) · [历史](issue-history.csv)','',
        '## 覆盖','']
    for row in result['rows']:lines.append(f"- {md(row['url'])}：{md(row['status'])}；{md(row.get('representation'))}")
    groups={}
    for f in result['findings']:groups.setdefault((f['rule'],f['classification']),[]).append(f)
    lines+=['','## 发现与修复','']
    for (rule,classification),items in groups.items():
        lines += [f"### {md(rule)} · {md(classification)}",'',f"{len(items)} 条；最多展示3条，其余见逐项记录。",'']
        for f in items[:3]:
            lines += [f"- {md(f['url'])}；ID：{md(f['issue_id'])}",f"  - 原值：{short(f.get('original'))}",f"  - 建议：{short(f['recommendation'])}",f"  - 复测：{short(f['retest'])}",f"  - 证据：{short(f['evidence'])}"]
        lines.append('')
    lines+=['## 改写草稿与交接','',f"可供审稿的草稿 {len(result['drafts'])} 条；拦截草稿 {len(result['withheld_drafts'])} 条；交接 {len(result['handoffs'])} 条。",'',
        '所有草稿均需复核语言、产品状态、服务区域和事实准确性。没有自动发布。路由/正文/产品错配先交004或012，不能只改标题掩盖问题。','']
    for draft in result['drafts'][:10]:
        lines += ['- '+short(draft.get('proposed')), '  - 事实引用：'+short(draft.get('fact_ids')), '  - 更新规则：'+short(draft.get('update_rule'))]
    lines+=['','## 待审与证据缺口','']
    for p in result['pending_reviews'][:20]:lines.append('- '+short(p))
    for gap in (result['gaps']+result.get('input_gaps',[]))[:20]:lines.append('- '+short(gap))
    lines+=['','全部待审、缺口与交接见完整证据。重复仅覆盖已提取的指定样本；本轮未见不自动关闭历史。','',
        '规则依据：[Google标题链接](https://developers.google.com/search/docs/appearance/title-link)、[描述摘要](https://developers.google.com/search/docs/appearance/snippet)、[支持的元标签](https://developers.google.com/search/docs/crawling-indexing/special-tags)。','']
    (output/'report.md').write_text('\n'.join(lines),encoding='utf-8')
