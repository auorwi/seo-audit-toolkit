"""Reviewable actions, evidence and explicit audit coverage."""

import sys as _site_sys
from pathlib import Path as _SitePath
_site_dependency=_SitePath(__file__).resolve().parents[3]/'seo-crawlability/scripts'
if str(_site_dependency) not in _site_sys.path:_site_sys.path.insert(0,str(_site_dependency))
from crawlability.site import get_profile,site_host,site_origin,allowed_hosts,in_scope,require_url,brand_name,business_profile
import csv
import io
import json
import os
from collections import Counter
from pathlib import Path

CATEGORIES={'add':'应新增','remove':'应移除／先确认退役','retarget':'需改目标／先核验目标','repair':'需修文件或生成规则','confirm':'需确认意图或补证据'}

def csv_text(rows,fields):
    stream=io.StringIO(newline='');stream.write('\ufeff')
    writer=csv.DictWriter(stream,fieldnames=fields,extrasaction='ignore');writer.writeheader()
    for row in rows:
        values={}
        for key in fields:
            value=row.get(key)
            if isinstance(value,(dict,list)):value=json.dumps(value,ensure_ascii=False,sort_keys=True)
            if isinstance(value,str) and value.lstrip().startswith(('=','+','-','@')):value="'"+value
            values[key]=value
        writer.writerow(values)
    return stream.getvalue()

def write_report(result,history,output):
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    def write(name,content):
        temp=output/(name+'.tmp');temp.write_text(content,encoding='utf-8');os.replace(temp,output/name)
    write('report.json',json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    write('issue-history.json',json.dumps(history,ensure_ascii=False,indent=2)+'\n')
    fields=['id','rule','url','related_url','category','certainty','severity','engine','observed_at','sitemaps','recommendation','evidence']
    write('findings.csv',csv_text(result['findings'],fields))
    for category in CATEGORIES:
        write(category+'.csv',csv_text([r for r in result['findings'] if r['category']==category],fields))
    coverage=result['coverage']
    pending=[{'url':u,'kind':'sitemap','reason':'unread_or_unusable_file'} for u in coverage['unread_sitemaps']]
    pending += [{'url':u,'kind':'page','reason':'no_fresh_verified_response'} for u in coverage['unverified_page_urls']]
    write('pending.csv',csv_text(pending,['url','kind','reason']))
    write('files.csv',csv_text([{**r,'entry_count':len(r['entries']),'finding_count':len(r['findings'])} for r in result['files']],['url','kind','parsed_complete','uncompressed_bytes','entry_count','finding_count','checked_at','evidence']))
    write('memberships.csv',csv_text([e for entries in result['memberships'].values() for e in entries],['url','raw_url','sitemap','position','lastmod']))
    counts=Counter(r['category'] for r in result['findings'])
    lines=['# '+site_host()+' · 002 Sitemap 检查报告','',f"审查时间：{result['at']}；运行：`{result['ledger']['run_id']}`；覆盖状态：`{result['status']}`。",'',
        '这是指定 Sitemap 集合的审查，不是全站无问题或已收录的证明。文件解析与页面访问数量分别统计。','',
        '| 范围 | 结果 |','|---|---|',f"| 已取得文件 / 已解析文件 | {coverage['acquired_sitemaps']} / {coverage['parsed_sitemaps']} |",
        f"| 指定入口的可达文件是否读齐 | {coverage['sitemap_set_read_complete']} |",
        f"| 未读或不可用文件 | {len(coverage['unread_sitemaps'])} |",f"| 已解析文件中不同页面 URL | {coverage['listed_page_urls']} |",
        f"| 有新鲜且证据完整响应的页面 | {coverage['fresh_page_checks']} |",f"| 页面待核验 | {len(coverage['unverified_page_urls'])} |",
        f"| 独立预期可索引 URL 数 | {coverage['expected_indexable_urls'] if coverage['expected_indexable_urls'] is not None else '未知'} |",
        f"| 独立预期集合在指定 Sitemap 中出现数 | {coverage['expected_present_urls'] if coverage['expected_present_urls'] is not None else '未知'} |",'| 全站真实 URL 总量 | 未知 |','',
        '## 修复清单','', '| 类别 | 当前发现数 |','|---|---|']
    lines += [f'| {label} | {counts[key]} |' for key,label in CATEGORIES.items()]
    lines += ['',f"本轮新增问题 ID：{result['ledger']['new_issues']}；历史问题保留 {len(history)} 条。没有再次观察到的问题不会自动关闭。",'',
        '## 当前问题与处理方法','']
    for row in result['findings'][:50]:
        lines += [f"### {row['rule']} · {row['id']}",'',f"对象：{row['url']}",f"结论等级：{row['certainty']}；适用引擎：{row['engine']}。",'',row['recommendation'],'',
            '```json',json.dumps(row['evidence'],ensure_ascii=False,indent=2),'```','']
    if len(result['findings'])>50:lines += ['摘要展示前 50 项，完整问题及证据见 findings.csv 和 report.json。','']
    lines += ['## 使用与限制','',
        '- add/remove/retarget/repair/confirm.csv 是建议清单，不会改动线上 Sitemap。移除与目标替换须结合对应条目的业务条件。',
        '- pending.csv 保留文件与页面待查范围；文件未读齐或独立范围不一致时，不将缺失候选写成已确认全站遗漏。',
        '- lastmod 旧不等于过期；不会根据老日期批量建议删除。',
        '- 普通 HTTP、noindex 与 canonical 声明均不等于搜索引擎已索引状态。错误正文需要明确的内容核验证据。',
        '- 历史账本保留首次/最后报告时间、每次证据和本轮是否再次观察；关闭由后续修复验收技能处理。','',
        '规则来源：[Sitemap 协议](https://www.sitemaps.org/protocol.html)、[Google 构建 Sitemap](https://developers.google.com/search/docs/crawling-indexing/sitemaps/build-sitemap)、[索引规则](https://developers.google.com/search/docs/crawling-indexing/sitemaps/large-sitemaps)、[GSC 文件错误说明](https://support.google.com/webmasters/answer/7451001?hl=en)。','']
    write('report.md','\n'.join(lines))
    return str(output.resolve())
