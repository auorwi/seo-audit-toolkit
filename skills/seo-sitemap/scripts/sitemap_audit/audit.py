"""Sitemap membership, evidence freshness and independent intent reconciliation."""

import sys as _site_sys
from pathlib import Path as _SitePath
_site_dependency=_SitePath(__file__).resolve().parents[3]/'seo-crawlability/scripts'
if str(_site_dependency) not in _site_sys.path:_site_sys.path.insert(0,str(_site_dependency))
from crawlability.site import get_profile,site_host,site_origin,allowed_hosts,in_scope,require_url,brand_name,business_profile
import hashlib
import json
import re
import math
from collections import defaultdict
from urllib.parse import urljoin, urlsplit
from .xmlrules import date, identity, inspect_xml, safe_url

RECOMMENDATIONS = {
 'sitemap_nested_index':'Google 不支持索引再引用索引。将该层改为叶子 Sitemap 列表，或分别提交各独立索引；先核对平台读取状态。',
 'sitemap_cycle':'删除循环引用，保留有向且不回到祖先的 Sitemap 文件关系。',
 'sitemap_http_missing':'该条目当前返回 404/410。若业务确认退役则从 Sitemap 移除；若应当上线，先恢复页面再复测。',
 'sitemap_redirect':'核验每一跳与最终页面、内容等价性和索引意图，再把 Sitemap 条目更新为确认的规范目标。',
 'sitemap_access_unverified':'复测访问限制或服务异常，结合平台和日志判断；不要仅凭本次响应删除页面。',
 'sitemap_noindex_conflict':'确认索引意图。若有意 noindex 则移出 Sitemap；若应索引则先修正指令并复测。',
 'sitemap_canonical_conflict':'核对声明目标的状态、语言、实体和业务意图；不要机械替换为另一语言或未验证页面。',
 'sitemap_expected_missing':'核对独立发布清单与 Sitemap 范围，将确认发布且应该索引的规范 URL 加入对应模板/语言文件。',
 'sitemap_retired_entry':'独立业务清单确认退役；核对替代页面和退役策略后从 Sitemap 移除。',
 'lastmod_behind_known_change':'将 lastmod 同步到权威来源记录的重要内容变更时间，避免统一刷新所有页面时间。',
 'sitemap_error_content':'检查已记录的错误内容及业务预期；修复页面输出，或经退役确认后移除条目。',
 'sitemap_cross_site_unverified':'确认跨站提交的所有权和配置；未取得配置证据前，不把不同主机直接判成非法 URL。',
 'sitemap_unread':'补采尚未读取的文件，保留取数范围；未读齐时只能输出遗漏候选。',
 'sitemap_stale':'重新采集文件；旧文件可以保存为历史证据，但不能作为本轮现状。',
 'sitemap_fetch_unverified':'补采并记录失败类型、时间和平台结果，不把工具或网络失败当成页面已删除。',
 'sitemap_http_error':'修正或恢复 Sitemap 文件响应，再重新获取并验证 XML。',
 'sitemap_cross_file_duplicate':'核对是否为有意分组；重复收录本身不代表索引故障，必要时减少重复维护。',
 'expected_source_not_independent':'提供独立 CMS/路由发布清单；不能使用 Sitemap 自身或其派生导出证明 Sitemap 完整。',
 'expected_intent_unknown':'补充已发布、是否应索引和规范 URL 等明确业务意图，不根据 HTTP 200 自动推断。',
 'sitemap_roots_unknown':'明确此次检查的入口 Sitemap；未提供入口时无法证明文件集合已读完整。',
 'sitemap_index_path_scope':'该索引指向上层目录文件；按 Google 的索引路径要求调整文件位置或入口组织，核对已验证的跨站提交配置。',
 'page_evidence_unverified':'重新采集页面证据；当前记录的校验或取数失败属于审查数据缺口，不是页面内容故障。',
 'expected_modified_in_future':'核对业务清单的修改时间和时区；未来的重要变更不能用来判断当前 Sitemap 已落后。',
 'sitemap_empty':'文件可解析但没有条目。确认是否有意为空以及发布范围，不把空文件与取数失败混为一谈。',
}

class Findings:
    def __init__(self):
        self.rows={}

    def add(self, rule, url, *, category='repair', certainty='confirmed', evidence=None, related='', engine='all', sitemaps=None, observed_at=None):
        key=hashlib.sha256(json.dumps([site_host(),rule,url,related,engine],ensure_ascii=False).encode()).hexdigest()[:24]
        row=self.rows.setdefault(key,{'id':key,'rule':rule,'url':safe_url(url), 'related_url':safe_url(related) if related else '',
            'category':category,'certainty':certainty,'engine':engine,'severity':'P2' if certainty=='confirmed' else 'P3',
            'recommendation':RECOMMENDATIONS.get(rule,'依据记录的文件、条目位置和实际值修正 Sitemap 生成规则，并重跑本专项核验。'),
            'evidence':[],'sitemaps':[], 'observed_at':observed_at})
        if evidence is not None and evidence not in row['evidence']:
            row['evidence'].append(evidence)
        for source in sitemaps or []:
            if source not in row['sitemaps']: row['sitemaps'].append(source)
        return row

def _fresh(value, at, hours):
    try:
        delta=(date(at)-date(value)).total_seconds()
        return 0<=delta<=hours*3600
    except (ValueError,TypeError):
        return False

def _noindex_engines(details):
    engines=set()
    if details.get('noindex_observed'): engines.add('all')
    for engine,words in details.get('robots_directives',{}).items():
        if {'noindex','none'} & {v.lower() for v in words}:
            engines.add('all' if engine=='robots' else engine)
    header=details.get('headers',{}).get('x-robots-tag','')
    current='all'
    for part in header.lower().split(','):
        part=part.strip()
        if ':' in part:
            current,part=[v.strip() for v in part.split(':',1)]
        if {'noindex','none'} & set(part.split()): engines.add(current)
    return engines

def audit(documents, pages, roots, at, expected=None, max_age_hours=168, cross_site_hosts=None):
    date(at)
    if not math.isfinite(max_age_hours) or max_age_hours<=0: raise ValueError('max_age_hours_must_be_positive_finite')
    roots=list(dict.fromkeys(identity(require_url(u)) for u in roots))
    allowed_cross=set(cross_site_hosts or [])
    findings=Findings()
    latest={}
    for source in documents:
        url=identity(source['url'])
        date(source['checked_at'])
        if url not in latest or date(source['checked_at'])>=date(latest[url]['checked_at']):
            latest[url]=source
    parsed={}
    for url,source in latest.items():
        ev={k:source[k] for k in ('checked_at','status','error','evidence') if k in source}
        if not _fresh(source.get('checked_at'),at,max_age_hours):
            findings.add('sitemap_stale',url,category='confirm',certainty='unknown',evidence=ev,observed_at=source['checked_at'])
            continue
        if source.get('error') or source.get('status') is None:
            findings.add('sitemap_fetch_unverified',url,category='confirm',certainty='unknown',evidence=ev,observed_at=source['checked_at'])
            continue
        if source['status']!=200:
            findings.add('sitemap_http_error',url,evidence=ev,observed_at=source['checked_at'])
            continue
        result=inspect_xml(source['body'],url,at)
        result['checked_at']=source['checked_at']
        result['evidence']=source.get('evidence')
        parsed[url]=result
        for item in result['findings']:
            options={'category':'confirm','certainty':'candidate'} if item['rule']=='sitemap_empty' else {}
            findings.add(item['rule'],url,evidence={**ev,**item},observed_at=source['checked_at'],**options)
    graph={u:[e['url'] for e in p['entries']] if p['kind']=='index' else [] for u,p in parsed.items()}
    for parent,children in graph.items():
        for child in children:
            parent_parts=urlsplit(parent);child_parts=urlsplit(child)
            directory=parent_parts.path.rsplit('/',1)[0]+'/'
            if parent_parts.netloc==child_parts.netloc and not child_parts.path.startswith(directory):
                findings.add('sitemap_index_path_scope',parent,related=child,engine='google',evidence={'child':child,'parent_directory':directory},observed_at=latest[parent]['checked_at'])
            if child in parsed and parsed[child]['kind']=='index':
                findings.add('sitemap_nested_index',parent,related=child,engine='google',evidence={'child':child},observed_at=latest[parent]['checked_at'])
    color={}
    for start in graph:
        if color.get(start): continue
        stack=[(start,iter(graph[start]))]; color[start]=1
        while stack:
            node,it=stack[-1]
            child=next(it,None)
            if child is None:
                color[node]=2; stack.pop(); continue
            if color.get(child)==1:
                findings.add('sitemap_cycle',node,related=child,evidence={'cycle_edge':[node,child]},observed_at=latest[node]['checked_at'])
            elif child in graph and not color.get(child):
                color[child]=1; stack.append((child,iter(graph[child])))
    reachable=set(); todo=list(roots)
    while todo:
        url=todo.pop()
        if url in reachable: continue
        reachable.add(url); todo.extend(graph.get(url,[]))
    unread=sorted(u for u in reachable if u not in parsed or not parsed[u]['parsed_complete'])
    for url in unread:
        if url not in latest:
            findings.add('sitemap_unread',url,category='confirm',certainty='unknown',evidence={'referenced_by':[p for p,c in graph.items() if url in c]})
    if not roots:
        findings.add('sitemap_roots_unknown',site_origin()+'/',category='confirm',certainty='unknown')
    members=defaultdict(list)
    for file,document in parsed.items():
        if document['kind']=='urlset':
            for entry in document['entries']:
                members[entry['url']].append({'sitemap':file,**entry})
        for entry in document['entries']:
            host=urlsplit(entry['url']).hostname
            if host!=urlsplit(file).hostname and host not in allowed_cross:
                findings.add('sitemap_cross_site_unverified',entry['url'],category='confirm',certainty='candidate',evidence={'sitemap':file},sitemaps=[file],observed_at=latest[file]['checked_at'])
    fresh_checked=[]; unverified=[]
    for url,occurrences in members.items():
        files=sorted({o['sitemap'] for o in occurrences})
        if len(files)>1:
            findings.add('sitemap_cross_file_duplicate',url,category='confirm',certainty='candidate',evidence={'files':files},sitemaps=files)
        source=pages.get(url)
        if not source or not _fresh(source.get('checked_at'),at,max_age_hours) or source.get('status') is None or source.get('error'):
            if source and source.get('error'):
                findings.add('page_evidence_unverified',url,category='confirm',certainty='unknown',evidence={'error':source['error'],'checked_at':source.get('checked_at')},sitemaps=files,observed_at=source.get('checked_at'))
            unverified.append(url); continue
        fresh_checked.append(url)
        details=source.get('details',{})
        ev={k:source[k] for k in ('checked_at','status','evidence') if k in source}
        ev['details']=details
        args={'evidence':ev,'sitemaps':files,'observed_at':source['checked_at']}
        status=source['status']
        if status in (404,410):
            findings.add('sitemap_http_missing',url,category='remove',**args)
        elif status in (301,302,303,307,308):
            location=details.get('headers',{}).get('location','')
            ev['proposed_target']=safe_url(urljoin(url,location)) if location else None
            findings.add('sitemap_redirect',url,category='retarget',certainty='candidate',**args)
        elif status!=200:
            findings.add('sitemap_access_unverified',url,category='confirm',certainty='unknown',**args)
        if status!=200: continue
        for engine in _noindex_engines(details):
            findings.add('sitemap_noindex_conflict',url,category='confirm',engine=engine,**args)
        canonicals=details.get('canonicals',[])
        try:
            if canonicals and (len(canonicals)>1 or any(identity(urljoin(url,u))!=url for u in canonicals)):
                findings.add('sitemap_canonical_conflict',url,category='confirm',certainty='candidate',**args)
        except (ValueError,TypeError):
            findings.add('sitemap_canonical_invalid',url,category='confirm',**args)
        verdict=details.get('content_verdict',{})
        if verdict.get('state')=='error_content' and verdict.get('evidence') and _fresh(verdict.get('reviewed_at'),at,max_age_hours):
            findings.add('sitemap_error_content',url,category='confirm',**args)
    complete=bool(roots) and not unread
    expected_count=None; expected_present=None
    if expected:
        independent=expected.get('kind') in {'cms','routes','business'} and expected.get('source_id') and _fresh(expected.get('captured_at'),at,max_age_hours)
        if not independent:
            findings.add('expected_source_not_independent',site_origin()+'/',category='confirm',certainty='unknown',evidence={k:expected.get(k) for k in ('kind','source_id','captured_at')})
        else:
            eligible=set()
            expected_scope=set(expected.get('scope_roots',[]))==set(roots) and bool(roots)
            scoped_members={u for u,items in members.items() if any(e['sitemap'] in reachable for e in items)}
            for item in expected['rows']:
                url=identity(item['url']); occurrences=members.get(url,[])
                files=sorted({e['sitemap'] for e in occurrences})
                ev={'source_id':expected['source_id'],'captured_at':expected['captured_at'],'record':item}
                args={'evidence':ev,'sitemaps':files,'observed_at':expected['captured_at']}
                if item.get('retired') is True and occurrences:
                    findings.add('sitemap_retired_entry',url,category='remove',**args)
                if item.get('published') is True and item.get('should_index') is True and item.get('canonical_url')==url:
                    eligible.add(url)
                    if url not in scoped_members:
                        confirmed=complete and expected_scope
                        findings.add('sitemap_expected_missing',url,category='add' if confirmed else 'confirm',certainty='confirmed' if confirmed else 'candidate',**args)
                elif item.get('retired') is not True and not (item.get('published') is False or item.get('should_index') is False):
                    findings.add('expected_intent_unknown',url,category='confirm',certainty='unknown',**args)
                if item.get('modification_kind')=='significant' and item.get('modified_at'):
                    if date(item['modified_at'])>date(at):
                        findings.add('expected_modified_in_future',url,category='confirm',certainty='unknown',**args)
                        continue
                    for entry in occurrences:
                        try:
                            before=bool(entry['lastmod']) and (date(entry['lastmod']).date()<date(item['modified_at']).date() if len(entry['lastmod'])==10 or len(item['modified_at'])==10 else date(entry['lastmod'])<date(item['modified_at']))
                            if before:
                                findings.add('lastmod_behind_known_change',url,evidence={**ev,'entry':entry},sitemaps=files,observed_at=expected['captured_at'])
                        except ValueError: pass
            if expected.get('coverage')=='complete' and expected_scope:
                expected_count=len(eligible); expected_present=len(eligible & scoped_members)
    return {'schema_version':1,'configured_site':site_host(),'skill':'002-sitemap','at':at,'findings':list(findings.rows.values()),'files':list(parsed.values()),
        'coverage':{'roots':roots,'acquired_sitemaps':len(latest),'parsed_sitemaps':len(parsed),'sitemap_set_read_complete':complete,
            'unread_sitemaps':unread,'listed_page_urls':len(members),'fresh_page_checks':len(fresh_checked),'unverified_page_urls':sorted(unverified),
            'expected_indexable_urls':expected_count,'expected_present_urls':expected_present,'whole_site_total':None},
        'memberships':dict(members)}
