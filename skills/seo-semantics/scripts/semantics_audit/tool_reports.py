"""Normalize actual checker outputs while keeping manual review and evidence gaps."""
import copy
import re
from .shared import moment,fresh,url_id

def normalize_tool_report(record,*,at,max_age_hours=168):
    moment(at)
    result={'status':'evidence_gap','observations':[],'gaps':[],'coverage':{
        'full_accessibility_certification':False,'manual_review_required':True,'passed_rules':0,'inapplicable_rules':0}}
    try:
        tool=record['tool']
        if tool not in {'axe','nu'}:raise ValueError('unsupported_checker')
        for key in ('source','capture_id','checker_version'):
            if not isinstance(record.get(key),str) or not record[key].strip():raise ValueError('checker_provenance_missing')
        url=url_id(record['url'])
        if not fresh(record.get('checked_at'),at,max_age_hours):raise ValueError('checker_evidence_not_current')
        if record.get('state')!='completed':raise ValueError('checker_not_completed')
        digest=record.get('document_sha256')
        if not isinstance(digest,str) or not re.fullmatch('[0-9a-f]{64}',digest) or digest!=record.get('input_sha256'):
            raise ValueError('checker_document_binding_mismatch')
        if 'after_sha256' in record and record['after_sha256']!=digest:
            raise ValueError('document_changed_during_checker')
        payload=record['payload']
        if not isinstance(payload,dict):raise ValueError('checker_payload_invalid')
        provenance={k:record[k] for k in ('source','capture_id','checker_version','document_sha256','checked_at','representation') if k in record}
        observations=[]
        if tool=='axe':
            if record.get('representation')!='rendered_dom' or record.get('readiness')!='ready':raise ValueError('stable_browser_dom_required')
            if url_id(payload['url'])!=url:raise ValueError('checker_url_mismatch')
            engine=payload.get('testEngine',{})
            if engine.get('name')!='axe-core' or engine.get('version')!=record['checker_version']:raise ValueError('checker_version_mismatch')
            for group in ('violations','incomplete','passes','inapplicable'):
                if not isinstance(payload.get(group),list):raise ValueError('checker_result_group_missing')
                for rule in payload[group]:
                    if not isinstance(rule,dict) or not isinstance(rule.get('id'),str) or not isinstance(rule.get('nodes'),list):raise ValueError('checker_rule_invalid')
                    tags=rule.get('tags',[])
                    if not isinstance(tags,list) or not all(isinstance(t,str) for t in tags):raise ValueError('checker_tags_invalid')
                    if group not in {'violations','incomplete'}:continue
                    if not rule['nodes']:raise ValueError('checker_affected_nodes_missing')
                    for node in rule['nodes']:
                        if not isinstance(node,dict) or not isinstance(node.get('target'),list) or not node['target']:raise ValueError('checker_node_target_missing')
                        category='manual_review' if group=='incomplete' else 'accessibility_best_practice' if 'best-practice' in tags and not any(t.startswith('wcag') for t in tags) else 'accessibility_violation'
                        owner='013' if rule['id'] in {'image-alt','image-redundant-alt'} else '006'
                        observations.append({'tool':'axe','rule':rule['id'],'url':url,'category':category,'owner_skill':owner,'handoff':owner!='006',
                            'impact':rule.get('impact'),'tags':copy.deepcopy(tags),'target':copy.deepcopy(node['target']),
                            'html':node.get('html'),'message':node.get('failureSummary') or rule.get('description'),
                            'help':rule.get('help'),'help_url':rule.get('helpUrl'),'checks':{k:copy.deepcopy(node.get(k,[])) for k in ('any','all','none')},'provenance':dict(provenance)})
            result['coverage'].update({'passed_rules':len(payload['passes']),'inapplicable_rules':len(payload['inapplicable']),
                'incomplete_rules':len(payload['incomplete']),'violation_rules':len(payload['violations'])})
        else:
            messages=payload.get('messages')
            if not isinstance(messages,list):raise ValueError('checker_messages_missing')
            for message in messages:
                if not isinstance(message,dict) or not isinstance(message.get('message'),str):raise ValueError('checker_message_invalid')
                kind=message.get('type')
                if kind not in {'error','info'}:raise ValueError('checker_non_document_error')
                category='html_conformance_error' if kind=='error' else 'html_conformance_warning' if message.get('subType')=='warning' else 'html_conformance_info'
                observations.append({'tool':'nu','rule':'nu-message','url':url,'category':category,'owner_skill':'006','handoff':False,
                    'message':message['message'],'html':message.get('extract'),'location':{k:message[k] for k in ('firstLine','lastLine','firstColumn','lastColumn','hiliteStart','hiliteLength') if k in message},
                    'provenance':dict(provenance)})
            result['coverage']['document_messages']=len(messages)
        result['coverage'].update({'tool':tool,'checker_version':record['checker_version'],'representation':record.get('representation')})
        result.update({'status':'usable','observations':observations})
    except (ValueError,KeyError,TypeError,AttributeError) as error:
        result['gaps'].append(str(error))
    return result
