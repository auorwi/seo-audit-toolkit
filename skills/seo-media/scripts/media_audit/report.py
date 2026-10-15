
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
    for name,value in [('report.json',result),('checks.json',result['checks']),('issue-history.json',history),('referrals.json',result['referrals'])]:
        (output/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
    csv_file(output/'findings.csv',result['findings'],['issue_id','url','slot','rule','classification','recommendation','retest','evidence'])
    csv_file(output/'issue-history.csv',history,['issue_id','first_seen','last_seen','status','sightings','payload'])
    c=result['coverage'];lines=['# '+site_host()+' 013 图片与视频审查','',f"审查时点：{md(result['at'])}",'',
      f"已采集声明的 URL × 设备组合 {c['captured_declared_variants']}/{c['declared_variants']}；媒体观察 {c['observed_media_checks']} 条；去重问题 {len(result['findings'])} 条；缺口 {len(result['gaps'])} 条。",'',
      '采集覆盖不等于用途评审完成或所有资源正常。未触发的懒加载、未选择的 responsive 候选以及未知用途均不声称已验证。',
      '本报告不证明全站无问题、CWV 达标或视频已收录。','',
      '[逐项检查](checks.json) · [问题清单](findings.csv) · [历史记录](issue-history.csv) · [专业技能转交](referrals.json)','',
      '## 发现与修复','']
    for f in result['findings']:
        lines += [f"### {md(f['rule'])} — {md(f['classification'])}",'',f"URL：{md(f['url'])}",f"槽位：{md(f['slot'])}",f"问题 ID：{f['issue_id']}",'',
          f"修复方向：{md(f['recommendation'])}",'',f"复测：{md(f['retest'])}",'']
        for e in f['evidence']:lines.append(f"- {md(e['device'])} / {md(e['phase'])}；{md(e['captured_at'])}；快照 {md(e['snapshot_id'])}；资源 {md(e['resource'])}；{md(e['rule'])}")
        lines.append('')
    lines+=['## 缺口与分工','']
    for g in result['gaps']:lines.append('- '+md(json.dumps(g,ensure_ascii=False)[:2000]))
    lines+=['','可访问名称由 006 复核，加载性能由 011 复核，观看页结构化数据由 008 复核；013 仅转交证据，不重复创建其主责问题。','','## 判断边界','']
    lines+=['- '+md(x) for x in result['limitations']]
    lines+=['','相同问题与同一轮证据重复运行不会新增记录；首次发现、最近观察和每次证据进入历史，缺席不自动关闭。','']
    (output/'report.md').write_text('\n'.join(lines))
