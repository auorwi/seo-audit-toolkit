"""Join scoped source, browser, checker and semantic evidence for specialist 006."""
import hashlib
import json
import math
from .shared import require_url,site_host,moment,fresh,url_id
from .rules import audit_elements
from .tool_reports import normalize_tool_report

def audit(captures,tool_reports,targets,*,at,max_age_hours=168):
    moment(at)
    if not math.isfinite(max_age_hours) or max_age_hours<=0:raise ValueError('invalid_freshness_window')
    scope={}
    for target in targets:
        target={'url':target} if isinstance(target,str) else target
        url=url_id(require_url(target['url']));required=target.get('required_tools',['nu','axe'])
        if not isinstance(required,list) or not required or not set(required)<={'nu','axe'}:raise ValueError('invalid_required_tools')
        if url in scope and scope[url]!=target:raise ValueError('conflicting_url_scope')
        scope[url]=target
    if not scope:raise ValueError('explicit_nonempty_url_scope_required')
    def unique(records,keys):
        seen={}
        for record in records:
            identity=tuple(record[k] for k in keys)
            if identity in seen and seen[identity]!=record:raise ValueError('conflicting_capture_identity')
            seen[identity]=record
        return list(seen.values())
    captures=unique(captures,['snapshot_id']);tool_reports=unique(tool_reports,['tool','capture_id'])
    rows=[];findings=[];gaps=[];handoffs=[];pending=[];usable=0;ready=0
    def gap(url,reason,tool=None):gaps.append({'url':url,'reason':reason,**({'tool':tool} if tool else {})})
    def latest(records,key):return max(records,key=lambda r:moment(r[key])) if records else None
    for url,target in scope.items():
        selected=[c for c in captures if url_id(c['url'])==url]
        source=latest([c for c in selected if c.get('representation')=='source_elements'],'captured_at')
        rendered=latest([c for c in selected if c.get('representation')=='rendered_elements'],'captured_at')
        row={'url':url,'source_capture':source.get('snapshot_id') if source else None,'rendered_capture':rendered.get('snapshot_id') if rendered else None,'tools':[]}
        row['browser_state']=(rendered.get('readiness') or 'unknown') if rendered else 'not_checked'
        if rendered and not fresh(rendered.get('captured_at'),at,max_age_hours):row['browser_state']='stale'
        rows.append(row)
        if not rendered:gap(url,'rendered_elements_missing')
        else:
            assessed=audit_elements(rendered,at=at,max_age_hours=max_age_hours,purposes=rendered.get('purposes'))
            if rendered.get('readiness')=='ready' and fresh(rendered.get('captured_at'),at,max_age_hours):ready+=1
            findings.extend(assessed['findings']);handoffs.extend(assessed['handoffs'])
            pending.append({'url':url,'topics':assessed['pending_reviews'],'reviewed_topics':assessed['reviewed_topics']})
            for reason in assessed['gaps']:gap(url,reason)
        for tool in dict.fromkeys(target.get('required_tools',['nu','axe'])):
            chosen=latest([r for r in tool_reports if r.get('tool')==tool and url_id(r['url'])==url],'checked_at')
            document=source if tool=='nu' else rendered
            status={'tool':tool,'status':'evidence_gap'};row['tools'].append(status)
            if chosen is None:gap(url,'checker_not_observed',tool);continue
            status.update({k:chosen.get(k) for k in ('capture_id','checked_at','checker_version')})
            if document is None or not fresh(document.get('captured_at'),at,max_age_hours) or (tool=='axe' and document.get('readiness')!='ready') or chosen.get('document_sha256')!=document.get('document_sha256'):
                gap(url,'checker_not_current_document',tool);continue
            normalized=normalize_tool_report(chosen,at=at,max_age_hours=max_age_hours)
            status['status']=normalized['status'];status['coverage']=normalized['coverage']
            if normalized['status']!='usable':
                for reason in normalized['gaps']:gap(url,reason,tool)
                continue
            usable+=1
            for observation in normalized['observations']:
                if observation['owner_skill']!='006':handoffs.append(observation);continue
                anchor=observation['message'] if tool=='nu' else json.dumps(observation['target'],ensure_ascii=False,sort_keys=True)
                key=site_host()+'|006|'+url+'|'+tool+'|'+observation['rule']+'|'+anchor
                findings.append({'issue_id':'semantic-'+hashlib.sha256(key.encode()).hexdigest()[:24],'url':url,'rule':observation['rule'],'owner_skill':'006',
                    'classification':observation['category'],'impact_domain':'html_conformance' if tool=='nu' else 'accessibility','observed_at':at,
                    'recommendation':observation.get('help') or '按Nu给出的元素位置和约束复核HTML；不要把规范提示直接解释为排名或收录故障。',
                    'retest':'相同页面状态下重跑对应校验器，并人工确认语义用途及被覆盖的范围。','evidence':[observation]})
    grouped={}
    for finding in findings:
        key=finding['issue_id'];evidence=finding.get('evidence',[])
        if not isinstance(evidence,list):evidence=[evidence]
        if key not in grouped:grouped[key]={**finding,'evidence':list(evidence)}
        else:
            for item in evidence:
                if item not in grouped[key]['evidence']:grouped[key]['evidence'].append(item)
    unique_findings=list(grouped.values())
    return {'schema_version':1,'configured_site':site_host(),'skill':'006','at':at,'scope':list(scope),'rows':rows,'findings':unique_findings,'gaps':gaps,'handoffs':handoffs,'pending_reviews':pending,
        'coverage':{'requested_urls':len(scope),'requested_tools':{url:t.get('required_tools',['nu','axe']) for url,t in scope.items()},
            'usable_tool_runs':usable,'ready_documents':ready,'full_site':False,'full_accessibility_certification':False,
            'confirmed_accessibility_observations':sum(f['classification'] in {'accessibility_violation','accessibility_observation'} for f in unique_findings)}}
