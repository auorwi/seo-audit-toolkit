"""Canonical graph and evidence-backed routing review; no asset merging."""
import hashlib
import math
from urllib.parse import urlsplit,parse_qsl
from .shared import site_host,require_url,url_id,header_pairs,moment,fresh
from .declarations import parse
from crawlability.responses import latest_records,trace,evaluate_response
from crawlability.directives import parse_directives

AGENTS=['Googlebot','Bingbot','YandexBot']
LOCALES={'en','fr','de','es','it','pt','pt-br','ru','ja','ko','zh-cn','zh-tw','zh-tc','id','vi','th','tr','ar','uk','pl','nl'}

def compact(record):
    return {k:record[k] for k in ('url','status','checked_at','error','evidence','environment','request_id','capture_id') if k in record}

def trusted_observation(row,at,hours):
    return bool(row.get('source') and row.get('evidence') and fresh(row.get('checked_at'),at,hours))

def document(record):
    types=[v.split(';')[0].strip().lower() for k,v in header_pairs(record.get('headers',[])) if k=='content-type']
    return record.get('body',b'').decode('utf-8',errors='replace') if types and types[-1] in {'text/html','application/xhtml+xml'} else ''

def locale(url):
    first=urlsplit(url).path.lstrip('/').split('/')[0].lower()
    return first if first in LOCALES else None

def query_values(url):
    values={}
    for key,value in parse_qsl(urlsplit(url).query,keep_blank_values=True):values.setdefault(key,[]).append(value)
    return values

def policy_valid(target,at,hours):
    return bool(target.get('policy_source') and fresh(target.get('policy_at'),at,hours))

def audit(records,targets,*,at,max_age_hours=168,rendered=None,facts=None,navigation=None,engine_observations=None,equivalences=None):
    moment(at)
    if not math.isfinite(max_age_hours) or max_age_hours<=0:raise ValueError('invalid_freshness_window')
    scope={}
    for target in targets:
        target={'url':target} if isinstance(target,str) else target
        url=url_id(require_url(target['url']))
        if url in scope and scope[url]!=target:raise ValueError('conflicting_target_policy')
        scope[url]=target
    if not scope:raise ValueError('explicit_nonempty_url_scope_required')
    latest=latest_records(records);doms=latest_records(rendered or [])
    fact_map={}
    for row in facts or []:
        if trusted_observation(row,at,max_age_hours):
            key=url_id(row['url'])
            if key not in fact_map or moment(row['checked_at'])>=moment(fact_map[key]['checked_at']):fact_map[key]=row
    parsed={}
    for url,row in latest.items():
        if row.get('error') or type(row.get('status')) is not int or not 200<=row['status']<300 or not isinstance(row.get('body'),bytes) or not fresh(row.get('checked_at'),at,max_age_hours):continue
        parsed[url]=parse(document(row),row.get('headers',[]),url)
    relations=[];rows=[];findings=[]
    for source,data in parsed.items():
        for declaration in data['declarations']:
            if declaration['usable'] and declaration['target']:
                relations.append({'source':source,'target':declaration['target'],'relation':'canonical','mode':'raw','declaration':declaration,'evidence':compact(latest[source])})
        for refresh in data['refreshes']:
            relations.append({'source':source,'target':refresh['target'],'relation':'refresh_declaration','mode':'raw','declaration':refresh,'evidence':compact(latest[source])})
    for url,target_policy in scope.items():
        walked=trace(records,url,at,max_age_hours);page={k:v for k,v in walked.items() if k!='record'}
        current=walked['final_url'];raw=parsed.get(current) if walked['reason']=='complete' else None
        dom=doms.get(current);rendered_parsed=None
        if dom and dom.get('mode')=='rendered' and not dom.get('error') and type(dom.get('status')) is int and 200<=dom['status']<300 and isinstance(dom.get('body'),bytes) and fresh(dom.get('checked_at'),at,max_age_hours):
            rendered_parsed=parse(document(dom),dom.get('headers',[]),current)
        policy=target_policy if policy_valid(target_policy,at,max_age_hours) else {}
        observed_fact=fact_map.get(current,{})
        observations=[dict(o) for o in engine_observations or [] if url_id(o['url'])==url]
        row={'url':url,'page':page,'raw':raw,'rendered':rendered_parsed,'canonical_path':[current],
            'parameter_changes':[],'target_checks':[],'content_equivalence':'unknown',
            'engine_selected_canonical':'unknown','engine_observations':observations,
            'suggested_target':None,'policy_applied':bool(policy),'page_facts':observed_fact,'equivalence_assessments':[]}
        rows.append(row)
        def add(rule,classification,recommendation,evidence=None):
            identity=site_host()+'|004|'+rule+'|'+url
            findings.append({'issue_id':'routing-'+hashlib.sha256(identity.encode()).hexdigest()[:24],
                'rule':rule,'url':url,'classification':classification,'observed_at':at,
                'recommendation':recommendation,'evidence':evidence or page['chain'] or [{'reason':page['reason']}]})
        for left,right in zip(page['chain'],page['chain'][1:]):
            relations.append({'source':left['url'],'target':right['url'],'relation':'http_redirect','status':left['status'],'evidence':left})
        if policy.get('expected_role')=='public' and current!=url:
            if set(urlsplit(current).path.lower().split('/')).intersection({'login','sign-in','account','accounts','favorites','favourites','watchlist'}):
                add('public_route_to_restricted_candidate','http_observation','公开路由跳往登录/账户/收藏候选地址；核对业务访问策略和入口条件。',page)
        if policy.get('expected_role')=='public' and observed_fact.get('role') in {'login','private','favorites','account'}:
            add('public_route_role_mismatch','evidence_backed_review','页面观察的用途与公开栏目策略不符；核查实体接口、默认页和登录状态下的路由回退。',{'policy':policy,'observed_fact':observed_fact})
        if raw is None:
            add('source_evidence_gap','evidence_gap','补齐源页面最新响应、正文与跳转证据；不能用旧成功替代当前失败。')
        else:
            captured=latest[current].get('captured_header_names') or []
            if not {'link','refresh'}<=set(captured):
                add('canonical_header_evidence_gap','evidence_gap','旧证据未证明已采集 Link/Refresh；使用001 v1.0.3或明确头采集范围的独立证据补齐。')
            if raw['conflict']:add('canonical_conflict','confirmed_declaration_conflict','统一同页的规范目标；保留原始、HTTP 与渲染声明，先核实等价性。',raw['declarations'])
            if raw['warnings']:add('canonical_declaration_review','review_needed','按具体警告检查声明位置、相对路径、片段和重复元素。',{'warnings':raw['warnings'],'declarations':raw['declarations']})
            all_targets=list(dict.fromkeys(raw['targets']+(rendered_parsed or {}).get('targets',[])))
            for canonical in all_targets:
                target_trace=trace(records,canonical,at,max_age_hours)
                check={k:v for k,v in target_trace.items() if k!='record'};check['url']=canonical
                terminal=target_trace['record'] if target_trace['reason']=='complete' else None
                row['target_checks'].append(check)
                if not terminal:
                    add('canonical_target_evidence_gap','evidence_gap','采集声明目标及其跳转链；无法判断目标是否正常或等价。',check)
                elif terminal['status']>=400:
                    add('canonical_target_http_error','http_observation','目标返回错误状态；核查资源生命周期与路由后确定正确规范目标。',check)
                elif 200<=terminal['status']<300:
                    if not isinstance(terminal.get('body'),bytes):
                        add('canonical_target_evidence_gap','evidence_gap','补齐目标正文和索引指令，不用状态码代替内容检查。',check)
                    else:
                        check['index_directives']={agent:parse_directives(document(terminal),terminal.get('headers',[]),agent,at) for agent in AGENTS}
                        if any(v['noindex'] or v['expired'] is True for v in check['index_directives'].values()):
                            add('canonical_target_noindex','configuration_interaction','规范目标包含排除指令；先确认是否应公开索引，再统一 canonical 和 noindex。',check)
                    check['robots']={agent:evaluate_response(records,target_trace['final_url'],agent,at,max_age_hours) for agent in AGENTS}
                    if any(v['allowed'] is False for v in check['robots'].values()):
                        add('canonical_target_robots_block','configuration_interaction','核实目标的业务索引策略与禁抓规则，不能直接宣称引擎已选定此 canonical。',check)
                    if any(v['allowed'] is None for v in check['robots'].values()):
                        add('canonical_target_robots_gap','evidence_gap','补充目标 origin 的 robots 证据或引擎检查。',check)
                if len(check['chain'])>1:add('canonical_target_redirects','review_needed','核对最终等价目标，确认后直接声明稳定目标以减少信号冲突。',check)
                before=query_values(url);after=query_values(canonical)
                for key in sorted(before.keys()|after.keys()):
                    if before.get(key,[])==after.get(key,[]):continue
                    category='entity_by_policy' if key in policy.get('entity_parameters',[]) else 'tracking_by_policy' if key in policy.get('tracking_parameters',[]) else 'unknown'
                    change={'target':canonical,'parameter':key,'source_values':before.get(key,[]),'target_values':after.get(key,[]),'category':category}
                    row['parameter_changes'].append(change)
                    if category=='entity_by_policy':add('entity_parameter_changed','policy_conflict','保留决定业务实体的参数，或采用已证明等价的新路由；不要机械去参数。',{'change':change,'policy':policy})
                    elif category=='unknown':add('query_change_needs_equivalence','review_needed','确认参数是否改变实体、语言、分页或产品；没有证据不合并 URL。',change)
                if locale(url) and locale(canonical) and locale(url)!=locale(canonical):
                    add('cross_locale_canonical_candidate','review_needed','检查正文语言与翻译关系，不能只按路径把其他语言规范到英语。',{'source':url,'target':canonical})
                target_fact=fact_map.get(canonical,{})
                if observed_fact.get('language') and target_fact.get('language') and observed_fact['language']!=target_fact['language']:
                    add('content_language_mismatch','evidence_backed_review','正文语言观察不同；核对是否存在同语言规范版本或已批准的替代策略。',{'source_fact':observed_fact,'target_fact':target_fact})
                assessments=[]
                for assessment in equivalences or []:
                    if not trusted_observation(assessment,at,max_age_hours):continue
                    if url_id(assessment['source_url'])!=current or url_id(assessment['target_url'])!=canonical:continue
                    source_hash=latest.get(current,{}).get('evidence',{}).get('sha256')
                    target_hash=latest.get(canonical,{}).get('evidence',{}).get('sha256')
                    if not source_hash or not target_hash:continue
                    if source_hash!=assessment.get('source_sha256') or target_hash!=assessment.get('target_sha256'):continue
                    assessments.append(assessment)
                if assessments:
                    assessment=max(assessments,key=lambda a:moment(a['checked_at']))
                    row['equivalence_assessments'].append(assessment)
                    if assessment['result']=='different':
                        row['content_equivalence']='different_by_assessment'
                        add('canonical_content_not_equivalent','evidence_backed_review','当前证据下内容不等价；核对实体/用途后改正规范关系，不机械合并。',assessment)
                    elif assessment['result']=='equivalent':
                        row['content_equivalence']='equivalent_by_assessment'
                        index_checks=check.get('index_directives',{})
                        robots_checks=check.get('robots',{})
                        all_directives_known=len(index_checks)==3 and all(not v['noindex'] and v['expired'] is False and not v['warnings'] for v in index_checks.values())
                        all_robots_allow=len(robots_checks)==3 and all(v['allowed'] is True for v in robots_checks.values())
                        target_headers_known=terminal is not None and terminal.get('header_capture_complete',True) and bool(document(terminal))
                        language_compatible=not (observed_fact.get('language') and target_fact.get('language') and observed_fact['language']!=target_fact['language'])
                        if policy.get('preferred_canonical')==canonical and len(all_targets)==1 and len(check['chain'])==1 and all_directives_known and all_robots_allow and target_headers_known and language_compatible:
                            row['suggested_target']=canonical
            for refresh in raw['refreshes']:
                if raw['targets'] and refresh['target'] not in raw['targets']:
                    add('refresh_canonical_difference','review_needed','Refresh 声明与规范目标不一致；核实实际跳转、页面用途和稳定目标。',{'refresh':refresh,'canonicals':raw['targets']})
            # Follow only unambiguous, current declarations. Self-reference is a terminal node.
            node=current;seen={node}
            for _ in range(30):
                candidates=parsed.get(node,{}).get('targets',[])
                if len(candidates)!=1 or candidates[0]==node:break
                next_url=candidates[0];row['canonical_path'].append(next_url)
                if next_url in seen:
                    add('canonical_cycle','confirmed_declaration_conflict','解除 canonical 循环，选择经状态、索引和内容等价性核验的稳定目标。',row['canonical_path']);break
                seen.add(next_url);node=next_url
            else:
                candidates=parsed.get(node,{}).get('targets',[])
                if candidates and candidates!=[node]:
                    add('canonical_graph_limit','evidence_gap','关系链达到30步检查上限；按明确范围继续核验，当前不声称已抵达终点。',row['canonical_path'])
            if len(row['canonical_path'])>2 and row['canonical_path'][-1]!=current:
                add('canonical_chain','review_needed','核实链末目标及内容等价性后简化声明；不靠链条自动合并资产。',row['canonical_path'])
        if len(row['equivalence_assessments'])>1:
            row['content_equivalence']='multiple_target_assessments';row['suggested_target']=None
        if rendered_parsed:
            for canonical in row['rendered']['targets']:
                relations.append({'source':current,'target':canonical,'relation':'canonical','mode':'rendered','evidence':compact(dom)})
            if raw and set(raw['targets'])!=set(row['rendered']['targets']):
                add('raw_rendered_canonical_conflict','review_needed','统一 SSR 与客户端的规范声明；分别检查直达和站内导航后的页面状态。',{'raw':raw,'rendered':row['rendered']})
        if policy.get('expected_entity') and observed_fact.get('entity') and policy['expected_entity']!=observed_fact['entity']:
            add('route_entity_mismatch','evidence_backed_review','核查路由参数、数据接口和页面主体实体；仅改标题不能修复错误产品页面。',{'policy':policy,'observed_fact':observed_fact})
        for nav in navigation or []:
            if url_id(nav['from_url'])!=url or not trusted_observation(nav,at,max_age_hours):continue
            destination=url_id(nav['to_url'])
            relations.append({'source':url,'target':destination,'relation':'client_navigation','entry_mode':nav.get('entry_mode'),'evidence':nav})
            segments=set(urlsplit(destination).path.lower().split('/'))
            if policy.get('expected_role')=='public' and segments.intersection({'login','sign-in','account','favorites','favourites','watchlist'}):
                add('public_route_to_restricted_candidate','evidence_backed_review','复核公开栏目是否误入登录/收藏；对比直达、站内进入与登录状态，确认业务策略。',nav)
        for observation in observations:
            if raw and trusted_observation(observation,at,max_age_hours) and observation.get('canonical') and url_id(observation['canonical']) not in raw['targets']:
                add('declared_engine_canonical_difference','platform_observation','核对平台快照日期与当前声明、等价性和内链；声明是信号，不代表引擎必须采用。',observation)
    # Several changed parameters can exhibit one rule on one URL; keep a single issue with all evidence.
    grouped={}
    for finding in findings:
        key=finding['issue_id']
        if key not in grouped:grouped[key]={**finding,'evidence':[finding['evidence']]}
        else:grouped[key]['evidence'].append(finding['evidence'])
    return {'schema_version':1,'configured_site':site_host(),'skill':'004','at':at,'scope':list(scope),
        'coverage':{'requested_urls':len(scope),'full_site':False},'rows':rows,
        'relations':relations,'findings':list(grouped.values())}
