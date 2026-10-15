
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
    for name,value in [('report.json',result),('checks.json',result['checks']),('issue-history.json',history)]:
        (output/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
    csv_file(output/'findings.csv',result['findings'],['issue_id','url','rule','classification','recommendation','retest','evidence'])
    csv_file(output/'issue-history.csv',history,['issue_id','first_seen','last_seen','status','sightings','payload'])
    c=result['coverage'];lines=['# '+site_host()+' 012 内容与数据一致性审查','',f"审查时点：{md(result['at'])}",'',
      f"完成已声明检查 {c['performed_declared_checks']}/{c['declared_checks']} 项；发现 {len(result['findings'])} 条，证据缺口 {len(result['gaps'])} 条。",'',
      '本报告不证明全站没有问题，也不验证市场价格真实或预测会实现。已确认的内部矛盾与待核实候选分开记录。','',
      '[逐项核验](checks.json) · [问题清单](findings.csv) · [持久问题历史](issue-history.csv)','',
      '## 发现、修复方向与复测','']
    for f in result['findings']:
        lines += [f"### {md(f['rule'])} — {md(f['classification'])}",'',f"URL：{md(f['url'])}",f"问题 ID：{f['issue_id']}",'',
          f"修复方向：{md(f['recommendation'])}",'',f"复测：{md(f['retest'])}",'']
        for e in f['evidence']:
            lines.append(f"- 检查：{md(e['check']['check_id'])}；复核：{md(e['check']['reviewer'])}；{md(e['check']['reviewed_at'])}")
            for cite in e['check']['citations']:lines.append(f"- 原文：{md(cite['quote'])}；字段：{md(cite['field'])}；快照：{md(cite['snapshot_id'])}")
        lines.append('')
    lines+=['## 未完成与证据缺口','']
    for g in result['gaps']:lines.append('- '+md(json.dumps(g,ensure_ascii=False)[:1600]))
    lines+=['','## 判断边界与历史','',*['- '+md(x) for x in result['limitations']],'','首次发现、最近观察和每次证据保存在问题历史；同一问题复跑不重复新增，本轮未出现不自动关闭。','']
    (output/'report.md').write_text('\n'.join(lines))
