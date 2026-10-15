"""Assess explicit performance coverage and retain field/lab separation."""
import hashlib,math
from datetime import date
from .shared import site_host,require_url,url_id,moment,fresh
from .series import summarize_lab,compare_lab
from .metrics import assess_field,rating

def audit(inputs,*,at,max_age_hours=168,field_window_max_lag_days=35,baseline=None,lab_budgets=None):
    for cell in inputs.get('expected_cells',[]):require_url(cell['url'])
    now=moment(at)
    if not math.isfinite(max_age_hours) or max_age_hours<=0:raise ValueError('invalid_freshness_window')
    budgets=lab_budgets or {'LCP':2500,'CLS':0.1,'TBT':300};gaps=list(inputs['gaps']);runs=[]
    for r in inputs['lab_runs']:
        if r.get('page_review') and moment(r['page_review']['reviewed_at'])>now:
            r={**r,**r.get('before_page_review',{}),'page_content_validity':'review_not_yet_observed'};gaps.append({'reason':'page_review_after_audit_time','run_id':r.get('run_id')})
        if r.get('valid_measurement') and not fresh(r.get('fetched_at'),at,max_age_hours):r={**r,'valid_measurement':False,'exclusion':'measurement_not_fresh'};gaps.append({'reason':'measurement_not_fresh','run_id':r.get('run_id')})
        runs.append(r)
    laboratory=summarize_lab(runs);latest={}
    for r in inputs['field_records']:
        key=(r.get('source'),r.get('scope'),r.get('key'),r.get('device'))
        if key not in latest or moment(r['observed_at'])>=moment(latest[key]['observed_at']):latest[key]=r
    field=[]
    for r in latest.values():
        usable=r.get('status')=='observed' and fresh(r.get('observed_at'),at,max_age_hours);window=r.get('collection_period');reasons=list(r.get('gaps',[]))
        try:
            end=date.fromisoformat(window['last_date']);start=date.fromisoformat(window['first_date']);lag=(now.date()-end).days
            if (end-start).days+1!=28:usable=False;reasons.append('unexpected_field_window_length')
            if not 0<=lag<=field_window_max_lag_days:usable=False;reasons.append('collection_window_not_current')
        except (TypeError,KeyError,ValueError):usable=False;reasons.append('collection_period_missing')
        policy='psi' if r['source']=='psi_api' else 'strict';assessment=assess_field(r.get('metrics',{}),policy=policy)
        field.append({**r,'usable_for_current_assessment':bool(usable),'current_assessment':assessment['assessment'] if usable else 'unknown','assessment':assessment,'gaps':list(dict.fromkeys(reasons))})
    expected=list({(url_id(c['url']),c['device']):c for c in inputs['expected_cells']}.values());missing=[]
    for c in expected:
        if not any(g['requested_url']==url_id(c['url']) and g['device']==c['device'] and g['sufficient'] for g in laboratory['groups']):missing.append(c)
    devices={'mobile':'PHONE','desktop':'DESKTOP'}
    covered={(r['key'],r['device']) for r in field if r.get('scope')=='url' and r['usable_for_current_assessment'] and r['assessment']['all_three_observed']}
    coverage={'full_site_proven':False,'expected_cells':len(expected),'laboratory_scope_complete':bool(expected) and not missing,'missing_cells':missing,'field_scope_complete':bool(expected) and all((url_id(c['url']),devices[c['device']]) in covered for c in expected),'valid_lab_runs':sum(g['n'] for g in laboratory['groups'])}
    unreviewed=[{'run_id':r['run_id'],'url':r['requested_url'],'device':r['device'],'status':r.get('page_content_validity','unverified_by_metrics')} for g in laboratory['groups'] for r in g['runs'] if r.get('page_content_validity')!='reviewed_valid']
    coverage.update(business_page_scope_complete=coverage['laboratory_scope_complete'] and not unreviewed,unconfirmed_business_runs=unreviewed)
    limited=[{'url':g['requested_url'],'device':g['device'],'statuses':g['environment_statuses']} for g in laboratory['groups'] if not g['suitable_for_regression']]
    coverage.update(reliable_lab_scope_complete=coverage['laboratory_scope_complete'] and not limited,environment_limited_groups=limited)
    gaps += [{'reason':'host_environment_not_suitable_for_regression',**row} for row in limited]
    gaps += [{'reason':'business_page_not_confirmed',**row} for row in unreviewed]
    findings={}
    def add(rule,url,device,dimension,evidence,recommendation):
        key=site_host()+'|011|'+rule+'|'+url_id(url)+'|'+device+'|'+dimension;issue='cwv-'+hashlib.sha256(key.encode()).hexdigest()[:24]
        if issue not in findings:findings[issue]={'issue_id':issue,'url':url,'device':device,'owner_skill':'011','rule':rule,'metric_or_audit':dimension,'observed_at':at,'classification':'performance_evidence_review','evidence':[],
            'recommendation':recommendation,'retest':'保留同一工具/浏览器/设备/节流/入口/缓存环境，至少三次有效测量，复查原节点或资源；字段指标等待其实际统计窗口更新，不用一次实验室绿分关闭。'}
        if evidence not in findings[issue]['evidence']:findings[issue]['evidence'].append(evidence)
    for r in runs:
        if r.get('page_content_validity')=='reviewed_invalid' and fresh(r.get('fetched_at'),at,max_age_hours):add('business_page_mismatch',r['requested_url'],r['device'],'visible_content',{'run_id':r['run_id'],'page_review':r['page_review'],'page_review_evidence':r.get('page_review_evidence'),'lhr_evidence':r.get('evidence'),'manifest_path':r.get('manifest_path')},'截图中的业务状态与本次性能目标不符；先确认未登录直达、设备适配和业务预期，再对正确内容重新采集。保留空态/验证页原始证据，不以其分数宣称目标页面性能良好。')
    for g in laboratory['groups']:
        if not g['sufficient']:gaps.append({'url':g['requested_url'],'device':g['device'],'reason':'fewer_than_three_valid_comparable_runs'});continue
        for metric,budget in budgets.items():
            item=g['metrics'].get(metric,{})
            if item.get('sufficient') and item['median']>budget:add('laboratory_budget_exceeded',g['requested_url'],g['device'],metric,{'metric':metric,'budget':budget,'statistics':item,'environment_key':g['environment_key'],'runs':[{'run_id':r['run_id'],'evidence':r.get('evidence'),'manifest_path':r.get('manifest_path')} for r in g['runs']]},'这是本轮实验室工程预算超出；依据同组LHR的实际LCP节点、偏移元素、长任务/资源定位改动。TBT不替代真实用户INP，不从分数推断排名或流量损失。')
        for r in g['runs']:
            for o in r.get('diagnostics',{}).get('opportunities',[]):add('laboratory_optimization_candidate',g['requested_url'],g['device'],o['audit_id'],{'run_id':r['run_id'],'evidence':r.get('evidence'),'diagnostic':o},o['recommendation'])
    for f in findings.values():
        if f['rule'].startswith('laboratory_') and any(g['url']==f['url'] and g['device']==f['device'] for g in limited):
            f['classification']='provisional_observation_environment_limited';f['environment_limit']='Host load is high or not evidenced; inspect nodes/resources, but do not adopt these timings as a clean regression baseline.'
    for r in field:
        if not r['usable_for_current_assessment']:gaps.append({'url':r.get('key'),'source':r['source'],'reason':'field_current_assessment_unavailable'});continue
        for metric,value in r.get('metrics',{}).items():
            if metric in {'LCP','INP','CLS'} and rating(metric,value) in {'needs_improvement','poor'}:add('field_p75_not_good',r['key'],r['device'],r['scope']+'|'+metric,{'field_record':r,'metric':metric,'p75':value},'按实际URL或origin范围与设备确认受影响体验；用相应模板的实验室/交互证据寻找原因。origin值不能归因到每个URL，28日窗口会保留发布前体验。')
    comparison=compare_lab(baseline.get('laboratory',baseline),laboratory) if baseline else {'comparisons':[],'gaps':[{'reason':'baseline_not_supplied'}]}
    for c in comparison['comparisons']:
        for metric,result in c['metrics'].items():
            if result['status']=='regressed':add('laboratory_regression',c['requested_url'],c['device'],metric,{'comparison':c},'对照同环境前后具体资源/模板变更与原始LHR，排除测量噪声后修复；估算收益不能相加保证。')
    gaps+=comparison['gaps'];gaps += [{'url':c['url'],'device':c['device'],'reason':'expected_lab_cell_incomplete'} for c in missing]
    if not coverage['field_scope_complete']:gaps.append({'reason':'url_field_scope_incomplete'})
    return {'schema_version':1,'configured_site':site_host(),'skill':'011','at':at,'findings':list(findings.values()),'laboratory':laboratory,'field_assessments':field,'field_attempts':inputs.get('field_attempts',[]),'collection_events':inputs.get('collection_events',[]),'comparison':comparison,'coverage':coverage,'lab_budgets':budgets,'gaps':gaps,
        'pending_reviews':['页面业务内容与实际指标须结合LHR截图/节点确认；分数不认证正确实体。','导航实验室未测真实用户INP；代码级根因与复杂交互需额外trace或源码。','本机锁只隔离本工具；用户其他程序和外部网络活动仍可能影响测量。']}
