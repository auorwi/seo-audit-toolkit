"""Portable audit exports with explicit coverage and evidence gaps."""

import sys as _site_sys
from pathlib import Path as _SitePath
_site_dependency=_SitePath(__file__).resolve().parents[3]/'seo-crawlability/scripts'
if str(_site_dependency) not in _site_sys.path:_site_sys.path.insert(0,str(_site_dependency))
from crawlability.site import get_profile,site_host,site_origin,allowed_hosts,in_scope,require_url,brand_name,business_profile
import csv
import html
import json
from pathlib import Path

def scalar(value):
    if value is None:return ''
    if isinstance(value,(list,dict)):return json.dumps(value,ensure_ascii=False,sort_keys=True)
    return str(value)

def csv_file(path,rows,columns):
    with path.open('w',newline='',encoding='utf-8-sig') as stream:
        writer=csv.DictWriter(stream,fieldnames=columns,extrasaction='ignore');writer.writeheader()
        for row in rows:
            clean={}
            for key in columns:
                value=scalar(row.get(key))
                clean[key]="'"+value if value.lstrip().startswith(('=','+','-','@','\t','\r')) else value
            writer.writerow(clean)

def md(value):return html.escape(scalar(value)).replace('|','\\|').replace('\n','<br>').replace('`','&#96;')

def write_report(output,result,history):
    output=Path(output)
    if output.exists() and any(output.iterdir()):raise ValueError('output_directory_not_empty')
    output.mkdir(parents=True,exist_ok=True)
    for name,data in [('report.json',result),('issue-history.json',history)]:
        (output/name).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    flat=[];events={}
    for row in result['rows']:
        flat.append({'url':row['url'],'agent':row['agent'],'index_intent':row['index_intent'],
            'robots_allowed':row['robots']['allowed'],'robots_reason':row['robots']['reason'],
            'page_reason':row['page']['reason'],'final_url':row['page']['final_url'],
            'directive_status':row['directive_status'],'rendered_status':row['rendered_status'],
            'actual_bot_access':row['actual_bot_access'],'index_status':row['index_status'],
            'http_pattern':row['http_pattern'],'raw_directives':row['raw_directives'],
            'rendered_directives':row['rendered_directives']})
        for event in row['request_history']:events[json.dumps(event,sort_keys=True)]=event
    csv_file(output/'rows.csv',flat,['url','agent','index_intent','robots_allowed','robots_reason','page_reason','final_url','directive_status','rendered_status','actual_bot_access','index_status','http_pattern','raw_directives','rendered_directives'])
    csv_file(output/'findings.csv',result['findings'],['issue_id','rule','url','agent','classification','observed_at','recommendation','evidence'])
    csv_file(output/'request-history.csv',list(events.values()),['url','status','checked_at','error','environment','request_id','capture_id','run_id','evidence'])
    csv_file(output/'issue-history.csv',history,['issue_id','first_seen','last_seen','status','sightings','payload'])
    coverage=result['coverage']
    text=['# '+site_host()+' 003：可抓取性与索引指令审查','',f"审查时点：{md(result['at'])}",'',
        f"本次范围：{coverage['requested_urls']} 个明确指定 URL，{coverage['engine_rows']} 个引擎评估；渲染证据 {coverage['rendered_rows_observed']} 行。",'',
        '这是指定范围的配置与访问证据审查。允许抓取、HTTP 200、未观察到 noindex，均不等于搜索引擎已收录或实际爬虫已访问。','',
        '未提供业务索引策略的页面标记为 unknown。未采集渲染结果的页面标记为 not_checked。旧 HTTP 事件保留；历史问题不因本次未出现而自动关闭。','',
        '## 逐 URL 核验','', '| URL | 引擎 | robots 允许 | 页面证据 | 索引指令 | 渲染证据 |','|---|---|---|---|---|---|']
    for row in flat:text.append('| '+' | '.join(md(row[k]) for k in ['url','agent','robots_allowed','page_reason','directive_status','rendered_status'])+' |')
    text+=['','## 发现与建议','']
    if not result['findings']:text+=['本次范围未产生规则发现；仍受上述证据与覆盖限制。','']
    for item in result['findings']:
        text += [f"### {md(item['rule'])} · {md(item['agent'])}",'',
            f"URL：{md(item['url'])}",f"问题 ID：{md(item['issue_id'])}",f"分类：{md(item['classification'])}",'',
            md(item['recommendation']),'',f"证据：{md(item.get('evidence'))}",'']
    text += ['## 输入证据缺口','',md(result.get('input_gaps',[])),'','## 规则依据','',
        '- [Google robots 规范](https://developers.google.com/crawling/docs/robots-txt/robots-txt-spec)',
        '- [Google robots meta / HTTP 指令](https://developers.google.com/search/docs/crawling-indexing/robots-meta-tag)',
        '- [RFC 9309](https://www.rfc-editor.org/rfc/rfc9309.html)',
        '- [Bing robots 指令](https://www.bing.com/webmasters/help/robots-meta-tags-and-attributes-that-bing-supports-5198d240)',
        '- [Yandex User-agent](https://yandex.com/support/webmaster/en/robot-workings/user-agent)','',
        '引擎特殊行为无法核实的部分保留 unknown。平台导出、URL Inspection 或日志观察保留独立时间与来源，不用本地模拟 User-Agent 代替真实引擎证据。','']
    (output/'report.md').write_text('\n'.join(text),encoding='utf-8')
