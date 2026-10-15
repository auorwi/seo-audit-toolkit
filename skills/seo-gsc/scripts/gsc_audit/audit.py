"""Relate GSC observations to exact URL/device live observations, without claiming repairs."""
import hashlib,json
from .contracts import site_host,moment,fresh,url_id,belongs

OWNERS={'server_error':'003','robots_blocked':'003','noindex':'003','not_found':'003','access_denied':'003','redirect_error':'004','redirect':'004',
        'google_selected_other_url':'004','google_canonical_disagreement':'004','alternate_canonical':'004','duplicate':'004','soft_404':'005','crawled_not_indexed':'005','discovered_not_indexed':'009'}
REPORT_OWNER={'rich_results':'008','cwv':'011','sitemaps':'002','video_indexing':'013','https':'003'}
FETCH={'SERVER_ERROR':'server_error','BLOCKED_ROBOTS_TXT':'robots_blocked','NOT_FOUND':'not_found','ACCESS_DENIED':'access_denied','ACCESS_FORBIDDEN':'access_denied','BLOCKED_4XX':'access_denied','REDIRECT_ERROR':'redirect_error','SOFT_404':'soft_404'}
ERROR_FETCH=set(FETCH)-{'BLOCKED_ROBOTS_TXT'}
RECOMMENDATIONS={
 '003':'将该 URL 的抓取历史与当前 HTTP、robots、meta/X-Robots-Tag 证据交给 003；区分访问限制、历史故障及预期排除，修复后等待 Google 重新抓取验证。',
 '004':'交给 004 检查完整跳转链、声明与 Google 选择的 canonical、语言和业务实体等价性；不根据 URL 相似就认定 canonical 错误。',
 '005':'交给 005 对照原始 HTML 和渲染页面，再由内容专项检查；未收录本身不证明内容质量或渲染失败。',
 '008':'交给 008 按具体类型与错误字段复核当前页面；区分无效项目数量和页面数量，不伪造价格、评分、运费等数据。',
 '011':'交给 011 检查相同设备的现场指标和可复现性能证据；GSC 分组数据不等于该 URL 的实测值。',
 '002':'交给 002 检查实际文件、格式、URL 状态与发布清单；提交计数不代表 Google 索引数量。',
 '013':'交给 013 核实视频用途、可访问性与观看页条件；附属视频未索引不自动视为页面故障。',
 '009':'交给 009 结合重要页面的站内链接和发现路径检查，不能仅凭发现未索引直接断言抓取预算不足。',
 '014':'核实当前平台状态、报告范围和业务预期；证据不足时保留待核验，不以正常排除或验证通过代替索引结果。'}

def latest(rows):
    if not rows:return []
    t=max(moment(x['captured_at']) for x in rows)
    return [x for x in rows if moment(x['captured_at'])==t]

def audit(inputs,*,at,max_age_hours=24):
    moment(at);fresh(at,at,max_age_hours);run_kind=inputs.get('run_kind','audit');prop=inputs['property'];scope=inputs['scope'];gaps=list(inputs.get('gaps',[]));observations=[]
    for o in inputs['observations']:
        if o['property']!=prop or not fresh(o['captured_at'],at,max_age_hours):gaps.append({'evidence_id':o['id'],'reason':'stale_or_mismatched_observation'});continue
        observations.append(o)
        for g in o['data'].get('gaps',[]):gaps.append({'evidence_id':o['id'],'reason':g})
    findings={};referrals={};reports=[];inspections=[];lives=[]
    def add(o,url,rule,classification,report='page_indexing'):
        owner=REPORT_OWNER.get(report,OWNERS.get(rule,'014'));identity=('gsc-fixture-' if run_kind=='controlled_fixture' else 'gsc-')+hashlib.sha256(json.dumps([site_host(),prop,report,url,rule],ensure_ascii=False,separators=(',',':')).encode()).hexdigest()[:24]
        e={'evidence_id':o['id'],'captured_at':o['captured_at'],'proof':o['proof'],'kind':o['kind'],'observation_mode':classification,'observation':o['data']}
        if identity not in findings:
            findings[identity]={'issue_id':identity,'owner_skill':'014','property':prop,'url':url,'report':report,'rule':rule,'classification':classification,
              'observation_modes':[],'underlying_defect_confirmed':False,'recommendation':RECOMMENDATIONS[owner],'retest':'先同 URL、设备与范围复测当前页面，再读取更新后的 GSC 报告和最后抓取时间；本轮未出现、Live test 可用或验证 Passed 都不自动关闭历史问题。','evidence':[]}
        modes=findings[identity]['observation_modes']
        if classification not in modes:modes.append(classification);modes.sort()
        findings[identity]['classification']=modes[0] if len(modes)==1 else 'mixed_platform_observation'
        if not any(x['evidence_id']==o['id'] for x in findings[identity]['evidence']):findings[identity]['evidence'].append(e)
        if owner!='014' and url:
            key=(owner,url,rule)
            if key not in referrals:referrals[key]={'owner_skill':owner,'url':url,'reason':rule,'source_issue_id':identity,'instruction':RECOMMENDATIONS[owner],'not_a_second_defect':True}
    for o in observations:
        d=o['data']
        if o['kind']=='gsc_ui':
            reports.append({'evidence_id':o['id'],**d})
            for row in d['rows']:
                rule=row['reason_key'];u=row.get('url')
                if rule in {'available','no_issues_detected','validation_passed','valid','indexed'}:continue
                report='rich_results' if rule=='rich_result_error' and d['report'] in {'live_test','url_inspection'} else d['report']
                classification='live_test_observation' if d['report']=='live_test' else ('requires_intent_review' if rule in {'noindex','alternate_canonical','redirect','duplicate','not_watch_page'} else 'engine_observation')
                add(o,u,rule,classification,report)
        is_ui_inspection=o['kind']=='gsc_ui' and d.get('inspection') is not None
        if is_ui_inspection:
            o={**o,'data':d['inspection']};d=o['data']
        if o['kind']=='inspection_api' or is_ui_inspection:
            inspections.append(o);idx=d['index'];v=idx['verdict'];u=d['url'];fetch=idx['pageFetchState'];rule=None
            if fetch in FETCH:rule=FETCH[fetch]
            elif idx['indexingState'] in {'BLOCKED_BY_META_TAG','BLOCKED_BY_HTTP_HEADER'}:rule='noindex'
            elif idx['robotsTxtState']=='DISALLOWED':rule='robots_blocked'
            elif v in {'FAIL','NEUTRAL'}:rule='index_status_requires_review'
            if rule:add(o,u,rule,'requires_intent_review' if v=='NEUTRAL' else 'engine_observation')
            if idx['googleCanonical'] and idx['userCanonical'] and url_id(idx['googleCanonical'])!=url_id(idx['userCanonical']):add(o,u,'google_canonical_disagreement','requires_intent_review')
            if idx['googleCanonical'] and not idx['userCanonical'] and url_id(idx['googleCanonical'])!=u:add(o,u,'google_selected_other_url','requires_intent_review')
            rich=d['rich_results']
            if rich and (rich.get('verdict')=='FAIL' or any(i.get('severity')=='ERROR' for g in rich.get('detectedItems',[]) for item in g.get('items',[]) for i in item.get('issues',[]))):add(o,u,'rich_result_error','engine_observation','rich_results')
        elif o['kind']=='live_http':lives.append(o)
        elif o['kind']=='sitemaps_api':
            reports.append({'evidence_id':o['id'],**d})
            for s in d['entries']:
                if s.get('errors') and belongs(prop,s['path']):add(o,s['path'],'submitted_sitemap_error','engine_observation','sitemaps')
        elif o['kind']=='analytics_api':reports.append({'evidence_id':o['id'],**d})
    checks=[];paired=0;inspected=set();captured=set()
    for s in scope:
        u=url_id(s['url']);device=s['device'];eng=[o for o in inspections if o['data']['url']==u];cur=latest([o for o in lives if o['data']['url']==u and o['data']['device']==device]);matched=latest([o for o in eng if o['data']['index']['crawledAs']==device])
        if eng:inspected.add(u)
        if cur:captured.add((u,device))
        check={'url':u,'device':device,'engine_evidence':[o['id'] for o in matched or latest(eng)],'live_evidence':[o['id'] for o in cur],
               'google_fixed':False,'googlebot_live_verified':False,'current_content_verified':False,'comparison':None}
        if not eng:status='platform_url_not_inspected'
        elif not matched:status='engine_device_unmatched'
        elif len({json.dumps(o['data']['index'],sort_keys=True) for o in matched})>1:status='conflicting_engine_snapshots'
        elif not cur:status='live_url_not_checked'
        elif len({json.dumps(o['data'],sort_keys=True) for o in cur})>1:status='conflicting_live_observations'
        else:
            idx=matched[0]['data']['index'];now=cur[0]['data'];code=now['status'];paired+=1
            check['last_google_crawl']=idx['lastCrawlTime'];check['google_fetch_state']=idx['pageFetchState'];check['live_http_status']=code;check['live_captured_at']=cur[0]['captured_at']
            if now['final_url']!=u:status='different_landing_unverified'
            elif code in {401,403,429}:status='current_access_limited'
            elif idx['pageFetchState']=='SERVER_ERROR' and code>=500:status='failure_reproduced_at_http_layer'
            elif idx['pageFetchState']=='NOT_FOUND' and code in {404,410}:status='failure_reproduced_at_http_layer'
            elif idx['pageFetchState'] in ERROR_FETCH and 200<=code<300:status='historical_error_not_reproduced'
            else:status='observations_available_requires_specialist_review'
        check['comparison']=status;checks.append(check)
        if status not in {'historical_error_not_reproduced','failure_reproduced_at_http_layer','observations_available_requires_specialist_review'}:gaps.append({'url':u,'device':device,'reason':status})
    performance=[]
    byid={o['id']:o for o in observations}
    from .performance import compare
    for pair in inputs.get('comparisons',[]):
        try:
            a=byid.get(pair['before']);b=byid.get(pair['after'])
            if not a or not b or a['kind']!='analytics_api' or b['kind']!='analytics_api':raise ValueError('performance_comparison_missing_evidence')
            performance.append({'before_evidence':a['id'],'after_evidence':b['id'],'result':compare(a['data'],b['data'])})
        except (ValueError,KeyError,TypeError) as e:gaps.append({'comparison':pair,'reason':str(e)})
    urls={url_id(s['url']) for s in scope};reportedurls={r.get('url') for o in observations if o['kind']=='gsc_ui' for r in o['data']['rows'] if r.get('url')}
    return {'schema_version':1,'configured_site':site_host(),'skill':'014','run_kind':run_kind,'at':at,'property':prop,'scope':scope,'findings':list(findings.values()),'checks':checks,'referrals':list(referrals.values()),
            'platform_reports':reports,'performance_comparisons':performance,'observations':observations,'gaps':gaps,'manifest_sha256':inputs.get('manifest_sha256'),
            'coverage':{'declared_variants':len(scope),'declared_urls':len(urls),'indexed_url_observations':len({o['data']['url'] for o in inspections}),
             'declared_urls_inspected':len(inspected),'live_declared_variants':len(captured),'paired_variants':paired,'ui_example_urls':len(reportedurls),
             'declared_checks_complete':bool(scope) and paired==len(scope) and not gaps,'all_reported_urls_verified':False,'full_site_proven':False,'affected_page_total':None,'cwv_live_verified':False},
            'limitations':['GSC 抓取/索引快照与当前 HTTP 观察属于不同时间和客户端；HTTP 200 不证明收录、内容正常或历史问题已修复。',
              '报表样例与 Search Analytics 均不构成全量 URL 清单；项目、分组、页面数量不相加。',
              '平台问题与底层缺陷分开计数；专业技能转交项不是第二个已确认缺陷。本轮缺席不会关闭历史问题。']}
