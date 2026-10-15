"""Keep historical platform claims, current tests and observed SERP display distinct."""
import re
from .shared import moment,fresh,url_id

def assess_engine_evidence(reports,current,*,at,max_age_hours=168):
    result={'history':[],'tests':[],'display_observations':[],'gaps':[],'engine_validation':'unverified','actual_display':'unverified'}
    valid=[]
    for record in reports:
        try:
            if url_id(record['url'])!=url_id(current['url']):raise ValueError('engine_url_mismatch')
            if not record.get('source') or not record.get('tool') or record.get('engine')!='Google' or not re.fullmatch('[0-9a-f]{64}',record.get('artifact_sha256','')):raise ValueError('engine_provenance_required')
            if moment(record['checked_at'])>moment(at):raise ValueError('engine_time_in_future')
            valid.append(record)
        except (ValueError,KeyError,TypeError) as error:result['gaps'].append(str(error))
    for record in valid:
        if record.get('kind')!='historical_issue':continue
        status='not_verified'
        bound_entities=[e for e in current.get('entities',[]) if (not record.get('entity_id') or e.get('id')==record['entity_id']) and (not record.get('field') or record['field'] in e.get('data',{}))]
        bound_scope=not (record.get('entity_id') or record.get('field')) or bool(bound_entities)
        if record.get('result')=='error' and bound_scope and current.get('ready') and current.get('extraction_complete') and fresh(current.get('captured_at'),at,max_age_hours) and record.get('rule') in current.get('checked_rules',[]):
            observations=[o for o in current.get('observations',[]) if o.get('rule')==record['rule']]
            for key in ['entity_id','field']:
                if record.get(key):observations=[o for o in observations if o.get(key)==record[key]]
            status='reproduced' if observations else 'not_reproduced_in_current_scope'
        result['history'].append({**record,'status':status,'auto_close':False,'comparison_scope':'URL + mapped rule'+(' + supplied entity/field' if record.get('entity_id') or record.get('field') else ''),'limitation':'Current local checks do not close platform issues or prove engine recrawl.'})
    selected={}
    for record in valid:
        kind=record.get('kind')
        if kind=='historical_issue':continue
        if kind not in {'code_test','url_test','serp_observation'}:result['gaps'].append('unsupported_engine_evidence_kind');continue
        key=(kind,record['tool'])
        if key not in selected or moment(record['checked_at'])>moment(selected[key]['checked_at']):selected[key]=record
    for record in selected.values():
        if not fresh(record['checked_at'],at,max_age_hours):result['gaps'].append('engine_evidence_stale');continue
        kind=record['kind']
        if kind=='serp_observation':
            if record.get('result')=='observed' and all(record.get(k) for k in ['query','device','locale','feature']):
                result['display_observations'].append(record);result['actual_display']='observed_at_recorded_time'
            else:result['gaps'].append('serp_observation_context_required')
            continue
        result['tests'].append(record)
        if record.get('result') not in {'valid','invalid'}:result['gaps'].append('engine_test_not_completed');continue
        if kind=='url_test':
            if not result['engine_validation'].startswith('observed_'):result['engine_validation']='remote_url_result_observed'
            result['gaps'].append('engine_remote_snapshot_not_bound_to_local_html');continue
        if record.get('document_sha256')!=current.get('document_sha256') or not current.get('ready') or not fresh(current.get('captured_at'),at,max_age_hours):result['gaps'].append('engine_code_test_document_mismatch_or_stale');continue
        result['engine_validation']='observed_'+record['result']
    return result
