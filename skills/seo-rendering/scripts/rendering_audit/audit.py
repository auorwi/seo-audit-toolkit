"""Compare scoped rendering phases and observed, read-only public interactions."""
import hashlib
import json
import math
from collections import Counter
from .shared import site_host,require_url,moment,fresh,url_id
from .readiness import evaluate

COMPARE_FIELDS=('title','titles','descriptions','canonical','h1','main_text','identity','schema','links')
ENTRY_MODES={'direct','internal','back'}
PUBLIC_ACTIONS={'paginate','filter','open_internal_link','back'}

def proof(snapshot):
    return {k:snapshot[k] for k in ('id','url','requested_url','captured_at','source','stage','entry_mode','navigation_id','phase_id','evidence','representation') if k in snapshot}

def nonempty(value):
    if isinstance(value,list):return any(nonempty(v) for v in value)
    return bool(value.strip()) if isinstance(value,str) else bool(value)

def audit(snapshots,targets,*,at,max_age_hours=168,interactions=None):
    moment(at)
    if not math.isfinite(max_age_hours) or max_age_hours<=0:raise ValueError('invalid_freshness_window')
    scope={}
    for target in targets:
        target={'url':target} if isinstance(target,str) else target
        url=url_id(require_url(target['url']))
        if url in scope and scope[url]!=target:raise ValueError('conflicting_target_scope')
        scope[url]=target
    if not scope:raise ValueError('explicit_nonempty_url_scope_required')
    ids={}
    for snapshot in snapshots:
        moment(snapshot['captured_at']);url_id(snapshot['url'])
        if snapshot['id'] in ids and ids[snapshot['id']]!=snapshot:raise ValueError('conflicting_snapshot_id')
        ids[snapshot['id']]=snapshot
    current=[s for s in ids.values() if fresh(s['captured_at'],at,max_age_hours)]
    rows=[];findings=[];changes=[];missing=[];interaction_rows=[]
    def add(url,rule,classification,recommendation,evidence,entry_mode=None):
        key=site_host()+'|005|'+rule+'|'+url+'|'+str(entry_mode or '')
        findings.append({'issue_id':'render-'+hashlib.sha256(key.encode()).hexdigest()[:24],
            'url':url,'rule':rule,'entry_mode':entry_mode,'classification':classification,'observed_at':at,
            'recommendation':recommendation,'evidence':evidence})
    for url,target in scope.items():
        modes=target.get('expected_entry_modes',['direct','internal','back'])
        if not isinstance(modes,list) or not modes or not set(modes)<=ENTRY_MODES:raise ValueError('invalid_entry_modes')
        selected=[s for s in current if url_id(s.get('requested_url',s['url']))==url]
        present={s.get('entry_mode') for s in selected if s.get('stage') in {'dom','interaction'}}
        absent=[m for m in modes if m not in present]
        if absent:
            missing.append({'url':url,'modes':absent})
            add(url,'entry_path_evidence_gap','evidence_gap','补充未观察的直达、站内进入或返回路径；各路径不能互相代替。',{'missing_entry_modes':absent})
        for mode in dict.fromkeys(modes):
            path=[s for s in selected if s.get('entry_mode')==mode]
            latest=max(path,key=lambda s:moment(s['captured_at'])) if path else None
            navigation=[s for s in path if s.get('navigation_id')==latest.get('navigation_id')] if latest else []
            navigation.sort(key=lambda s:moment(s['captured_at']))
            browser=[s for s in navigation if s.get('stage') in {'dom','interaction'}]
            initial=[s for s in navigation if s.get('stage')=='initial']
            before=initial[-1] if initial else None;after=browser[-1] if browser else None
            started=latest.get('navigation_started_at',navigation[0]['captured_at']) if latest else at
            readiness=evaluate(browser,target.get('readiness',{}),started_at=started)
            row={'url':url,'entry_mode':mode,'navigation_id':latest.get('navigation_id') if latest else None,
                'readiness':readiness,'initial':proof(before) if before else None,'rendered':proof(after) if after else None,
                'baseline_relation':before.get('baseline_relation','unspecified') if before else None,
                'comparison_fields':[],'unchecked_fields':[]}
            rows.append(row)
            if after is None:
                add(url,'rendered_evidence_gap','evidence_gap','取得实际浏览器快照；初始HTTP或过期观察不能证明当前渲染。',{'entry_mode':mode},mode);continue
            if readiness['state']=='page_error':
                add(url,'visible_page_error','ui_observation','复核用户可见错误与对应接口/路由，保留时间和环境；不要把普通控制台警告等同页面失败。',{'snapshot':proof(after),'errors':readiness['page_errors']},mode)
            elif readiness['state']!='ready':
                add(url,'render_readiness_gap','evidence_gap','按主体实体、占位消失和关键字段稳定继续观察；到达预算后保持未知，不猜永久缺失。',readiness,mode)
            if not before:
                add(url,'initial_evidence_gap','evidence_gap','补采同一导航对应的初始HTML，不能拿其他页面的原始响应作比较。',proof(after),mode);continue
            if row['baseline_relation']!='same_navigation':
                add(url,'initial_navigation_context_gap','evidence_gap','原始HTML为独立请求或导航关系未知；只比较采集结果差异，不将其归因为同一次导航的渲染变化。',{'baseline_relation':row['baseline_relation'],'initial':proof(before),'browser':proof(after)},mode)
            if readiness['state']!='ready':continue
            for field in COMPARE_FIELDS:
                if before.get('coverage',{}).get(field)!='complete' or after.get('coverage',{}).get(field)!='complete':
                    row['unchecked_fields'].append(field);continue
                old=before.get(field);new=after.get(field);row['comparison_fields'].append(field)
                if old==new:continue
                kind=field+'_populated' if not nonempty(old) and nonempty(new) else field+'_changed'
                change={'url':url,'entry_mode':mode,'field':field,'change':kind,'baseline_relation':row['baseline_relation'],'before':old,'after':new,'evidence':[proof(before),proof(after)]}
                changes.append(change)
                if field=='canonical':add(url,'canonical_changed_after_render','declaration_observation','核对SSR与客户端规范目标；交给004检查目标、参数和内容等价性。',change,mode)
                if field=='h1' and nonempty(old) and not nonempty(new):add(url,'heading_disappeared','rendering_review','原始标题在就绪DOM中消失；核查可见性与组件替换，不用初始占位推断永久缺失。',change,mode)
                if field=='main_text' and nonempty(old) and not nonempty(new):add(url,'main_content_disappeared','rendering_review','核实主体选择器、可见性和渲染替换，确认是否丢失有用内容。',change,mode)
                if field in {'titles','descriptions','canonical'} and isinstance(new,list) and len(new)>1 and len(new)>len(old or []):
                    add(url,'metadata_nodes_increased','rendering_review','对照组件生命周期，避免同一导航重复插入元信息；不要把H1数量当收录硬规则。',change,mode)
                if field=='schema':
                    def counts(blocks):return Counter(json.dumps(b.get('parsed'),sort_keys=True,ensure_ascii=False) for b in blocks or [] if b.get('parsed') is not None)
                    old_counts=counts(old);new_counts=counts(new)
                    if any(n>1 and n>old_counts.get(k,0) for k,n in new_counts.items()):
                        add(url,'repeated_schema_block_after_render','rendering_review','检查同内容schema是否被重复注入；同@id的不同属性引用不自动判重复。',change,mode)
            if row['unchecked_fields']:
                add(url,'comparison_coverage_gap','evidence_gap','补充未知或截断字段；部分摘录不能证明某项内容已消失。',{'fields':row['unchecked_fields']},mode)
    for url in scope:
        ready_rows=[row for row in rows if row['url']==url and row['readiness']['state']=='ready']
        for index,left in enumerate(ready_rows):
            for right in ready_rows[index+1:]:
                a=ids[left['rendered']['id']];b=ids[right['rendered']['id']]
                if a.get('environment')!=b.get('environment') or url_id(a['url'])!=url_id(b['url']):continue
                differences={field:{'before':a.get(field),'after':b.get(field)} for field in ('title','descriptions','canonical','h1','identity')
                    if all(s.get('coverage',{}).get(field)=='complete' for s in (a,b)) and a.get(field)!=b.get(field)}
                if differences:add(url,'entry_path_content_mismatch','rendering_review','同URL在不同进入路径产生不同稳定内容；核查首屏数据、SEO元信息更新时机和路由缓存。',
                    {'paths':[left['entry_mode'],right['entry_mode']],'differences':differences,'snapshots':[proof(a),proof(b)]})
    for event in interactions or []:
        url=url_id(event['url'])
        if url not in scope:continue
        observation={**event,'verification':'unverified'};interaction_rows.append(observation)
        if event.get('kind') not in PUBLIC_ACTIONS:
            add(url,'unsupported_interaction','scope_exclusion','仅记录公开阅读、分页、筛选、内链和返回；本技能不执行账户/交易写操作。',event);continue
        before=ids.get(event.get('before_id'));after=ids.get(event.get('after_id'))
        if not event.get('source') or not event.get('evidence') or not fresh(event.get('checked_at'),at,max_age_hours) or not before or not after or not fresh(before.get('captured_at'),at,max_age_hours) or not fresh(after.get('captured_at'),at,max_age_hours):
            add(url,'interaction_evidence_gap','evidence_gap','补齐实际操作前后快照和事件来源；点击尝试不等于交互完成。',event);continue
        same_environment=before.get('environment')==after.get('environment')
        ordered=moment(before['captured_at'])<moment(after['captured_at'])<=moment(event['checked_at'])
        if not same_environment or not ordered or any(s.get('stage') not in {'dom','interaction'} for s in (before,after)):
            add(url,'interaction_evidence_gap','evidence_gap','交互必须关联同一环境下时间顺序正确的实际浏览器快照。',event);continue
        observation['comparison']={field:{'before':before.get(field),'after':after.get(field)} for field in ('url',*COMPARE_FIELDS)
            if field=='url' or all(s.get('coverage',{}).get(field)=='complete' for s in (before,after))}
        if event['kind']!='paginate':
            if event['kind'] in {'back','open_internal_link'}:
                if not event.get('expected_url') or not event.get('expected_identity'):
                    add(url,'interaction_expectation_gap','evidence_gap','先从实际链接或返回历史记录期望URL及实体，不能用操作结果反推预期。',event);continue
                if url_id(after['url'])!=url_id(event['expected_url']):
                    add(url,'interaction_destination_mismatch','interaction_review','目标URL与操作前记录的目标不一致；检查跳转链和路由，不自行判定重定向必定错误。',event);continue
            elif event['kind']=='filter':
                if url_id(before.get('requested_url',before['url']))!=url or url_id(after.get('requested_url',after['url']))!=url or any(event.get(key) is None or event[key]!=capture.get('visible_items') for key,capture in [('before_items',before),('after_items',after)]):
                    add(url,'interaction_evidence_gap','evidence_gap','筛选前后的可见条目必须与实际快照一致。',event);continue
                if event['before_items']==event['after_items']:
                    add(url,'interaction_effect_not_observed','evidence_gap','未观察到筛选数据变化；保留未确认状态并核对筛选值、等待条件和请求结果。',event);continue
            post=[s for s in current if s.get('stage') in {'dom','interaction'} and s.get('navigation_id')==after.get('navigation_id')
                and s.get('phase_id',s.get('stage'))==after.get('phase_id',after.get('stage'))
                and moment(before['captured_at'])<moment(s['captured_at'])<=moment(after['captured_at'])]
            post.sort(key=lambda s:moment(s['captured_at']))
            policy={**scope[url].get('readiness',{})};policy.pop('required_identity',None)
            ready=evaluate(post,policy,started_at=before['captured_at']);observation['readiness']=ready
            if ready['state']!='ready':
                add(url,'interaction_readiness_gap','evidence_gap','交互后的主体、占位和关键字段尚未确认稳定；不能用点击成功代替完成。',ready);continue
            expected=event.get('expected_identity')
            if expected and (not isinstance(after.get('identity'),str) or after['identity'].strip().casefold()!=expected.strip().casefold()):
                add(url,'interaction_identity_mismatch','interaction_review','稳定页面实体与预期不符；核对旧组件状态、路由参数和返回缓存。',event);continue
            observation['verification']='observed_stable_transition'
        if event['kind']=='paginate':
            same_scope=all(url_id(s.get('requested_url',s['url']))==url for s in (before,after))
            same_environment=before.get('environment')==after.get('environment')
            ordered=moment(before['captured_at'])<moment(after['captured_at'])<=moment(event['checked_at'])
            if not same_scope or not same_environment or not ordered:
                add(url,'interaction_evidence_gap','evidence_gap','操作前后证据必须属于同一检查页面与环境，且时间顺序正确。',event);continue
            expected=[('before_page',before,'page_indicator'),('after_page',after,'page_indicator'),('before_items',before,'visible_items'),('after_items',after,'visible_items')]
            if any(key not in event or event[key]!=capture.get(field) for key,capture,field in expected):
                add(url,'interaction_evidence_gap','evidence_gap','分页声明必须与前后实际页码和可见条目一致，不用手工描述代替页面观察。',event);continue
            changed=event['before_page']!=event['after_page'] or event['before_items']!=event['after_items']
            observation['verification']='observed_data_change' if changed else 'effect_not_observed'
            if changed and url_id(before['url'])==url_id(after['url']):
                policy=scope[url]
                explicit=bool(policy.get('policy_source') and fresh(policy.get('policy_at'),at,max_age_hours) and policy.get('pagination_requires_url_change') is True)
                add(url,'pagination_route_policy_conflict' if explicit else 'pagination_url_unchanged_candidate',
                    'policy_conflict' if explicit else 'interaction_review',
                    '核对列表是否需要可分享/可抓取分页URL；比较页码、数据、地址、canonical与内链，不能只因按钮可点就视为完成。',event)
    grouped={}
    for finding in findings:
        key=finding['issue_id']
        if key not in grouped:grouped[key]={**finding,'evidence':[finding['evidence']]}
        else:grouped[key]['evidence'].append(finding['evidence'])
    return {'schema_version':1,'configured_site':site_host(),'skill':'005','at':at,'scope':list(scope),'rows':rows,'changes':changes,
        'interactions':interaction_rows,'findings':list(grouped.values()),
        'coverage':{'requested_urls':len(scope),'full_site':False,'missing_entry_modes':missing,
            'all_requested_paths_observed':not missing,'ready_paths':sum(r['readiness']['state']=='ready' for r in rows)}}
