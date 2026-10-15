
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
    for name,data in [('report.json',result),('issue-history.json',history),('targets.json',result['targets']),('switches.json',result['switches'])]:(output/name).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    csv_file(output/'language-matrix.csv',result['clusters']['declarations'],['source_url','locale','target_url','channel','representation','entry_mode','eligible','problems','snapshot_id','document_sha256','locator'])
    csv_file(output/'findings.csv',result['findings'],['issue_id','url','rule','classification','recommendation','retest','evidence'])
    csv_file(output/'body-reviews.csv',result['content']['body_reviews'],['url','snapshot_id','document_sha256','body_language','entity_id','source','method','confidence','quotes'])
    csv_file(output/'issue-history.csv',history,['issue_id','first_seen','last_seen','status','sightings','payload'])
    c=result['coverage'];lines=['# '+site_host()+' 010：技术国际化审查','',f"审查时点：{md(result['at'])}",'',f"观察 {c['observed_urls']} 个URL、{c['declarations']} 条语言声明、{c['body_reviews']} 份绑定正文复核、{c['switch_actions']} 次语言切换。",'',
        '本报告的覆盖范围是已提供的实际证据；不证明全站语言版本完整、搜索引擎已采纳hreflang或页面已收录。候选问题须结合真实实体与发布策略确认。','',
        '[语言声明矩阵](language-matrix.csv) · [正文证据](body-reviews.csv) · [目标响应](targets.json) · [切换记录](switches.json) · [完整问题](findings.csv) · [历史](issue-history.json)','',
        '## 发现与修复','']
    groups={}
    for f in result['findings']:groups.setdefault(f['rule'],[]).append(f)
    for rule,items in groups.items():
        lines += [f'### {md(rule)}','',f'{len(items)} 条审查记录；以下最多列3条，完整证据见JSON与CSV。','']
        for f in items[:3]:
            evidence=json.dumps(f['evidence'],ensure_ascii=False)
            lines += [f"- {md(f['url'])}；{md(f['classification'])}；ID {f['issue_id']}",f"  - 建议：{md(f['recommendation'])}",f"  - 复测：{md(f['retest'])}",f"  - 证据：{md(evidence[:1500])}"+('…' if len(evidence)>1500 else '')]
        lines.append('')
    lines+=['## 覆盖与待核实','',f"{len(result['gaps'])} 条证据缺口。缺少目标正文、某声明渠道或实际语言切换时，保留未知，不写成验证通过。",'']
    for reason,count in Counter(str(g.get('reason')) for g in result['gaps']).most_common():lines.append('- '+md(reason)+f'：{count}')
    lines+=['']+['- '+md(x) for x in result['pending_reviews']]+['','同一稳定问题ID累计首次/最近观察；本轮未出现不自动关闭。语种、地区、脚本和实体是不同维度：正文语言与HTML/Schema声明分开核对；区域性同语言canonical不机械判错；未发布的翻译不虚构为漏页。','',
        '规范依据：[Google本地化版本](https://developers.google.com/search/docs/specialty/international/localized-versions)、[多语言/多地区网站](https://developers.google.com/search/docs/specialty/international/managing-multi-regional-sites)、[IANA语言子标签注册表](https://www.iana.org/assignments/language-subtag-registry/language-subtag-registry)。','']
    (output/'report.md').write_text('\n'.join(lines),encoding='utf-8')
