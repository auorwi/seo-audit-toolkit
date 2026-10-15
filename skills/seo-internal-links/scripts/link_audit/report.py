"""Compact human report with complete observed graph, sources and paths alongside."""

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
    for name,data in [('report.json',result),('targets.json',result['targets']),('pagination.json',result['pagination']),('issue-history.json',history)]:
        (output/name).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    g=result['graph'];csv_file(output/'edges.csv',g['edges'],['source','target','all_observed_links_nofollow','occurrences'])
    csv_file(output/'nodes.csv',list(g['nodes'].values()),['url','inventory_member','inbound_source_count','observed_inbound_sources','outgoing_observed','status'])
    paths=[{'seed_group':group,'url':url,**p} for group,rows in g['paths'].items() for url,p in rows.items()]
    csv_file(output/'paths.csv',paths,['seed_group','url','depth','path'])
    csv_file(output/'orphan-candidates.csv',[{'url':u,'classification':'no_observed_inbound_candidate','full_site_orphan_proven':False} for u in result['orphan_candidates']],['url','classification','full_site_orphan_proven'])
    csv_file(output/'findings.csv',result['findings'],['issue_id','url','rule','classification','source_urls','recommendation','retest','link_occurrences','evidence'])
    csv_file(output/'issue-history.csv',history,['issue_id','first_seen','last_seen','status','sightings','payload'])
    def short(value,limit=700):
        text=value if isinstance(value,str) else json.dumps(value,ensure_ascii=False,sort_keys=True)
        return md(text[:limit]+'…（完整数据见JSON/CSV）' if len(text)>limit else text)
    c=result['coverage'];lines=['# '+site_host()+' 009：内链与发现路径审查','',f"审查时点：{md(result['at'])}",'',
        f"资产清单 {c['inventory_assets']} 个URL；观察源页面 {c['observed_source_pages']} 个；唯一有向边 {c['unique_edges']} 条，原始出现位置 {c['raw_edge_occurrences']} 条。",'',
        '本报告表示所提供证据形成的观察图；不证明全站完整、搜索引擎已发现或已收录。深度阈值是排查线索，不是排名红线。','',
        '[全部链接及来源](edges.csv) · [节点与入链](nodes.csv) · [分入口最短路径](paths.csv) · [目标响应](targets.json) · [分页证据](pagination.json) · [完整报告](report.json)','',
        '## 发现与修复','',f"共 {len(result['findings'])} 条审查记录；含候选、HTTP观察与待审项，不等于相同数量的确定SEO故障。",'']
    groups={}
    for f in result['findings']:groups.setdefault(f['rule'],[]).append(f)
    for rule,items in groups.items():
        lines += [f"### {md(rule)}",'',f"{len(items)} 条；以下最多3条，完整条目见findings.csv。",'']
        for f in items[:3]:
            lines += [f"- {md(f['url'])}；ID：{md(f['issue_id'])}",f"  - 已观察来源：{short(f['source_urls'])}",f"  - 建议：{short(f['recommendation'])}",f"  - 复测：{short(f['retest'])}",f"  - 证据：{short(f['evidence'] or f['link_occurrences'])}"]
        lines.append('')
    lines += ['## 孤立候选与覆盖','',f"资产清单内 {len(result['orphan_candidates'])} 个URL在本轮图中未观察到其他页面入链，见[候选表](orphan-candidates.csv)。需扩展源页面采集并与独立发布清单核对，不能据此称为全站绝对孤立。HTTP重定向不计作A元素边，跳转落地页的候选还须结合目标响应链判断。",'',
        f"点击后才出现的快照 {c['excluded_interaction_captures']} 份、条件noscript链接 {c['excluded_conditional_links']} 条未混入普通初始发现图。",'',
        '入口建议需结合节点路径、真实分类/语言/实体关系选择相关列表或正文，不给每个候选机械添加首页链接。','',
        '## 分页与目标说明','']
    for p in result['pagination']:lines.append('- '+short(p,1200))
    lines += ['', '目标状态为GET证据的观察。200不证明正文正确或可索引，403/429不是永久断链，重定向最终URL须先验证内容等价。nofollow为线索，不是“绝对不能发现”。','',
        '## 待审与证据缺口','',short(result['pending_reviews']),f"证据缺口 {len(result['gaps'])} 条，按原因汇总：",'']
    counts=Counter(str(x.get('reason')) for x in result['gaps']);lines += ['- '+md(reason)+f'：{count}' for reason,count in counts.most_common(20)]
    lines += ['', '问题历史按稳定ID累计；本轮未见不自动关闭。原始链接出现位置保留在edges.csv；语义、名称和语言判断需继续对照页面上下文。','',
        '依据：[Google链接实践](https://developers.google.com/search/docs/crawling-indexing/links-crawlable)、[分页实践](https://developers.google.com/search/docs/specialty/ecommerce/pagination-and-incremental-page-loading)。','']
    (output/'report.md').write_text('\n'.join(lines),encoding='utf-8')
