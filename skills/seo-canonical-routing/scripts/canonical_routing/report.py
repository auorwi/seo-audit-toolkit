"""Human report plus inspectable canonical graph and parameter changes."""

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
    for name,value in [('report.json',result),('issue-history.json',history)]:
        (output/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    rows=[];parameters=[];pending=[]
    for row in result['rows']:
        rows.append({'url':row['url'],'final_url':row['page']['final_url'],'page_reason':row['page']['reason'],
            'raw_targets':(row['raw'] or {}).get('targets',[]),'rendered_targets':(row['rendered'] or {}).get('targets',[]),
            'canonical_path':row['canonical_path'],'content_equivalence':row['content_equivalence'],
            'suggested_target':row['suggested_target'],'engine_selected_canonical':row['engine_selected_canonical'],
            'policy_applied':row['policy_applied']})
        parameters.extend({'source_url':row['url'],**change} for change in row['parameter_changes'])
        if row['page']['reason']!='complete':pending.append({'source_url':row['url'],'url':row['page']['final_url'],'reason':row['page']['reason']})
        for check in row['target_checks']:
            if check['reason']!='complete':pending.append({'source_url':row['url'],'url':check['final_url'],'reason':check['reason']})
            for agent,robots in check.get('robots',{}).items():
                if robots['allowed'] is None:pending.append({'source_url':row['url'],'url':robots['robots_url'],'reason':agent+':'+robots['reason']})
    csv_file(output/'rows.csv',rows,['url','final_url','page_reason','raw_targets','rendered_targets','canonical_path','content_equivalence','suggested_target','engine_selected_canonical','policy_applied'])
    csv_file(output/'relations.csv',result['relations'],['source','target','relation','mode','status','entry_mode','declaration','evidence'])
    csv_file(output/'parameter-changes.csv',parameters,['source_url','target','parameter','source_values','target_values','category'])
    csv_file(output/'pending-targets.csv',pending,['source_url','url','reason'])
    csv_file(output/'findings.csv',result['findings'],['issue_id','url','rule','classification','observed_at','recommendation','evidence'])
    csv_file(output/'issue-history.csv',history,['issue_id','first_seen','last_seen','status','sightings','payload'])
    text=['# '+site_host()+' 004：Canonical 与路由审查','',f"审查时点：{md(result['at'])}",'',
        f"本次明确指定 {result['coverage']['requested_urls']} 个 URL，关系图包含已提供证据中的关联目标；未声明全站覆盖。",'',
        'canonical 是声明信号，不能据此确定引擎当前选定目标。原始 URL、HTTP 跳转、HTML/HTTP 声明、渲染声明和浏览器导航分别保留。','',
        '参数移除只有在业务策略或内容等价性证据支持时才可采用。内容事实与等价性评审保留来源、时间和证据；自动检查不保证语义判断正确。','',
        '## 逐 URL 结果','', '| URL | 原始 canonical | 渲染 canonical | 内容等价性 | 建议目标 |','|---|---|---|---|---|']
    for row in rows:text.append('| '+' | '.join(md(row[k]) for k in ['url','raw_targets','rendered_targets','content_equivalence','suggested_target'])+' |')
    text+=['','## 发现与修复方向','']
    for item in result['findings']:
        text += [f"### {md(item['rule'])}",'',f"URL：{md(item['url'])}",f"问题 ID：{md(item['issue_id'])}",f"分类：{md(item['classification'])}",'',md(item['recommendation']),'',f"证据：{md(item['evidence'])}",'']
    if not result['findings']:text+=['本次证据未产生规则发现，仍受范围与输入限制。','']
    text += ['## 未完成项','',md(result.get('input_gaps',[])),'',
        '补采目标及 robots 清单见 pending-targets.csv。缺少语义证据时 content_equivalence 保持 unknown；没有足够依据时建议目标留空。历史问题未在本次出现，不自动视为修复。','',
        '规则依据：[Google canonical 文档](https://developers.google.com/search/docs/crawling-indexing/consolidate-duplicate-urls)、[Google 重定向文档](https://developers.google.com/search/docs/crawling-indexing/301-redirects)。','']
    (output/'report.md').write_text('\n'.join(text),encoding='utf-8')
