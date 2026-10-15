"""Per-URL evidence audit. Decisions are configuration models, not indexing proof."""
import hashlib
import math
from .site import require_url,site_host
from .common import moment, fresh, header_pairs, url_id
from .directives import parse_directives, ALIASES
from .responses import trace, evaluate_response, latest_records

DEFAULT_AGENTS = ['Googlebot', 'Bingbot', 'YandexBot']
EVENT_KEYS = ('url','status','checked_at','error','evidence','environment','request_id','capture_id','run_id')

def compact(record):
    return {k:record[k] for k in EVENT_KEYS if k in record}

def directives(record, agent, at):
    headers=header_pairs(record.get('headers',[]))
    types=[v.lower().split(';')[0].strip() for k,v in headers if k=='content-type']
    html=record.get('body',b'').decode('utf-8',errors='replace') if types and types[-1] in {'text/html','application/xhtml+xml'} else ''
    return parse_directives(html,headers,agent,at)

def pattern(history):
    if len(history)<2:return 'single_observation' if history else 'not_observed'
    environments={row.get('environment') for row in history}
    if None in environments or len(environments)!=1:return 'noncomparable_observations'
    outcomes={(row.get('status'),row.get('error')) for row in history}
    return 'mixed_observations' if len(outcomes)>1 else 'repeated_observations'

def audit(records,targets,*,at,agents=None,max_age_hours=168,rendered=None,observations=None):
    moment(at)
    if not math.isfinite(max_age_hours) or max_age_hours<=0:raise ValueError('invalid_freshness_window')
    agents=list(dict.fromkeys(agents if agents is not None else DEFAULT_AGENTS))
    if not agents or any(a.lower() not in ALIASES for a in agents):raise ValueError('unsupported_agent_profile')
    scope={}
    for target in targets:
        if isinstance(target,str):target={'url':target}
        key=url_id(require_url(target['url']))
        if key in scope and scope[key]!=target:raise ValueError('conflicting_target_policy')
        scope[key]=target
    if not scope:raise ValueError('explicit_nonempty_url_scope_required')
    rendered=rendered or [];observations=observations or []
    latest_records(records);rendered_latest=latest_records(rendered)
    rows=[];findings=[]
    for url,target in scope.items():
        intent=target.get('index_intent','unknown')
        if intent not in {'indexable','excluded','unknown'}:raise ValueError('invalid_index_intent')
        if not target.get('intent_source') or not fresh(target.get('intent_at'),at,max_age_hours):intent='unknown'
        walked=trace(records,url,at,max_age_hours)
        page={k:v for k,v in walked.items() if k!='record'}
        terminal=walked['record'] if walked['reason']=='complete' else None
        history=sorted([compact(r) for r in records if url_id(r['url'])==url],key=lambda r:moment(r['checked_at']))
        observed=[dict(o) for o in observations if url_id(o['url'])==url]
        for agent in agents:
            robots=evaluate_response(records,url,agent,at,max_age_hours)
            terminal_robots=evaluate_response(records,walked['final_url'],agent,at,max_age_hours)
            raw=None;render=None;render_status='not_checked'
            if terminal and 200<=terminal['status']<300 and isinstance(terminal.get('body'),bytes):
                raw=directives(terminal,agent,at)
            dom=rendered_latest.get(walked['final_url'])
            if dom:
                render_status='unverified_or_stale'
                if dom.get('mode')=='rendered' and type(dom.get('status')) is int and 200<=dom['status']<300 and not dom.get('error') and fresh(dom.get('checked_at'),at,max_age_hours) and isinstance(dom.get('body'),bytes):
                    render=directives(dom,agent,at);render_status='observed'
            header_complete=terminal is not None and terminal.get('header_capture_complete',True)
            content_type_known=terminal is not None and any(k=='content-type' and v.strip() for k,v in header_pairs(terminal.get('headers',[])))
            restriction=bool(raw and (raw['noindex'] or raw['expired'] is True))
            status='restriction_observed' if restriction else 'no_restriction_observed' if raw and header_complete and content_type_known and not raw['warnings'] else 'incomplete_evidence'
            chain_robots=[evaluate_response(records,r['url'],agent,at,max_age_hours) for r in page['chain']]
            decisions=[r['allowed'] for r in chain_robots]+[robots['allowed'],terminal_robots['allowed']]
            readable=False if False in decisions else True if all(v is True for v in decisions) else None
            row={'url':url,'agent':agent,'index_intent':intent,'intent_source':target.get('intent_source'),
                'robots':robots,'terminal_robots':terminal_robots,'chain_robots':chain_robots,'page':page,'raw_directives':raw,
                'rendered_directives':render,'rendered_status':render_status,
                'noindex_readable_under_rules':readable if restriction else None,
                'directive_status':status,'index_status':'unknown','actual_bot_access':'unknown',
                'request_history':history,'http_pattern':pattern(history),'platform_observations':observed}
            rows.append(row)
            def add(rule,classification,recommendation,evidence=None):
                identity=site_host()+'|003|'+rule+'|'+url+'|'+agent.lower()
                findings.append({'issue_id':'crawl-'+hashlib.sha256(identity.encode()).hexdigest()[:24],
                    'rule':rule,'url':url,'agent':agent,'classification':classification,
                    'observed_at':at,'evidence':evidence or page['chain'] or robots['chain'] or [{'reason':page['reason']}],
                    'recommendation':recommendation})
            if robots['allowed'] is None:
                add('robots_evidence_gap','evidence_gap','补采此 origin 的 robots 与完整跳转链；无法据此确认实际爬虫访问。',robots)
            if walked['final_url']!=url and terminal_robots['allowed'] is None:
                add('terminal_robots_evidence_gap','evidence_gap','补采跳转目标 origin 的 robots；不要沿用起始页面权限。',terminal_robots)
            if robots['warnings']:
                add('robots_parse_warning','review_needed','检查 robots 的响应类型、编码及规则行，按引擎限制复核。',robots)
            if intent=='indexable' and robots['allowed'] is False:
                add('unexpected_robots_block','confirmed_configuration','确认公开页面需被抓取后，调整命中规则；保留私有路径限制。',robots)
            if walked['reason']!='complete' or (terminal and 200<=terminal['status']<300 and raw is None):
                add('page_evidence_gap','evidence_gap','补采缺失、过期或失败的页面响应；工具请求失败不等于网站故障。')
            if terminal and terminal['status']>=400:
                add('http_access_failure','http_observation','依据时间、请求 ID 和网络环境复核 CDN/WAF/源站；单次状态不证明持续故障。')
            if terminal and not header_complete:
                add('header_capture_gap','evidence_gap','旧采集可能折叠重复响应头；使用新版 001 重新采集再确认是否缺少索引指令。')
            if raw and not content_type_known:
                add('content_type_evidence_gap','evidence_gap','补采 Content-Type；未确认 HTML 类型时不能断言不存在 meta 指令。')
            if restriction and intent=='indexable':
                add('unexpected_noindex','confirmed_configuration','依据已确认的可索引意图移除对应 noindex 或过期指令；修改后重新抓取并等待引擎处理。',{'response':compact(terminal),'directives':raw['sources']})
            if restriction and readable is False:
                add('robots_blocks_noindex','configuration_interaction','若目标是让引擎读取 noindex，需要允许相关 URL 抓取；先确认访问控制和业务排除策略。',{'robots':robots,'chain_robots':chain_robots,'terminal_robots':terminal_robots,'directives':raw['sources']})
            if intent=='unknown' and (restriction or robots['allowed'] is False):
                add('intent_confirmation_needed','review_needed','补充路由发布与索引策略；排除规则可能符合业务要求，不直接删除。')
            if raw and (raw['index_conflict'] or raw['follow_conflict']):
                add('directive_conflict','configuration_interaction','统一 HTML 与 HTTP 指令；更严格的指令仍会生效。',raw['sources'])
            if raw and raw['warnings']:
                add('directive_parse_warning','review_needed','核对指令位置、日期格式、时区及引擎支持范围；未确认的行为保持未知。',{'warnings':raw['warnings'],'sources':raw['sources']})
            if render and raw and any(render[k]!=raw[k] for k in ('noindex','nofollow','expired')):
                add('raw_rendered_directive_difference','review_needed','对照 SSR 与客户端变更；原始 noindex 不能靠渲染后 index 保证撤销。',{'raw':raw['sources'],'rendered':render['sources'],'rendered_response':compact(dom)})
    return {'schema_version':1,'configured_site':site_host(),'skill':'003','at':at,'scope':list(scope),'agents':agents,
        'coverage':{'requested_urls':len(scope),'engine_rows':len(rows),'full_site':False,
                    'rendered_rows_observed':sum(r['rendered_status']=='observed' for r in rows)},
        'rows':rows,'findings':findings}
