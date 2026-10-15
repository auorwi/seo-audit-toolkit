"""Accept only hash-bound captures and explicitly attributed semantic reviews.

Hashes verify local integrity, not independent truth. A named review still owns the
semantic mapping; raw text and parsed numeric representations are checked here.
"""
import hashlib,json
from pathlib import Path
from .shared import url_id,moment,fresh
from .numbers import parse_quantity
from .market_reference import review_response
from crawlability.adapters import read_body

KINDS={'pair','forecast','calculator','claim'}

def bind_trial(payload, review, captures, actions):
    action=actions[payload['action_id']]
    if action.get('status')!='completed' or payload.get('interaction_status')!='completed':raise ValueError('actual_action_not_completed')
    before=captures[payload['before_evidence_id']];after=captures[payload['after_evidence_id']]
    if action['before_snapshot']!=before['snapshot_id'] or action['after_snapshot']!=after['snapshot_id'] or before['snapshot_id']==after['snapshot_id']:raise ValueError('trial_snapshot_binding')
    for c in [before,after]:
        if review['snapshot_bindings'].get(c['snapshot_id'])!=c['document_sha256'] or c['readiness']!='ready':raise ValueError('trial_review_binding')
    if not (moment(before['captured_at'])<=moment(action['started_at'])<=moment(after['captured_at'])<=moment(action['finished_at'])<=moment(review['reviewed_at'])):raise ValueError('trial_time_order_invalid')
    if payload.get('direction')!=action.get('direction') or str(payload['requested_input']['raw'])!=action.get('requested_input'):raise ValueError('trial_request_binding')
    def field(c,name,value=False):
        f=c['fields'][name]
        if f.get('present') is not True or f.get('visible') is not True or f.get('count')!=1:raise ValueError('trial_field_not_unique_visible')
        return f.get('value') if value else f.get('text')
    actual=field(after,'input',True)
    if actual!=action.get('applied_input') or actual!=str(payload['actual_input']['raw']):raise ValueError('trial_applied_input_binding')
    output_values=[field(after,'output'),field(after,'output',True)]
    if not any(isinstance(v,str) and str(payload['output']['raw']) in v for v in output_values) or str(payload['rate']['raw']) not in field(after,'rate'):raise ValueError('trial_numeric_field_binding')
    for name in ['input_unit','output_unit']:
        if payload.get(name)!=field(after,name).strip():raise ValueError('trial_unit_binding')
    changed=field(before,'rate')!=field(after,'rate')
    if payload.get('rate_changed') is not changed or payload.get('rate_evidence_id')!=after['snapshot_id']:raise ValueError('trial_rate_binding')

def numeric_nodes(value):
    if isinstance(value,dict):
        if {'raw','status','value','quantum'}<=value.keys():yield value
        else:
            for item in value.values():yield from numeric_nodes(item)
    elif isinstance(value,list):
        for item in value:yield from numeric_nodes(item)

def observation_times(value):
    if isinstance(value,dict):
        if 'observed_at' in value:yield value['observed_at']
        for item in value.values():yield from observation_times(item)
    elif isinstance(value,list):
        for item in value:yield from observation_times(item)

def statement_snapshots(value):
    if isinstance(value,dict):
        if value.get('temporal_kind')=='same_snapshot_assertions':yield value.get('snapshot_id')
        for item in value.values():yield from statement_snapshots(item)
    elif isinstance(value,list):
        for item in value:yield from statement_snapshots(item)

def load_manifest(path, *, at, max_age_hours=24):
    moment(at);path=Path(path).resolve();data=json.loads(path.read_text())
    if not isinstance(data,dict) or data.get('schema_version')!=1:raise ValueError('unsupported_manifest_version')
    result={'scope':data.get('scope',[]),'captures':{},'checks':[],'actions':{},'references':{},'gaps':[]}
    for key in ['scope','captures','reviews','actions','references']:
        if not isinstance(data.get(key,[]),list):raise ValueError(key+'_array_required')
    for row in result['scope']:
        url_id(row['url'])
        if not isinstance(row.get('kinds'),list) or not row['kinds'] or any(k not in KINDS for k in row['kinds']):raise ValueError('invalid_scope_kinds')
    def obj(proof):
        raw,error=read_body(proof,path.parent)
        if error:raise ValueError(error)
        value=json.loads(raw)
        if not isinstance(value,dict):raise ValueError('evidence_object_required')
        return value
    poisoned=set()
    for proof in data.get('captures',[]):
        try:
            c=obj(proof);url_id(c['url']);moment(c['captured_at'])
            if not c.get('source') or not c.get('snapshot_id') or not isinstance(c.get('fields'),dict):raise ValueError('capture_provenance_missing')
            if hashlib.sha256(c['html'].encode()).hexdigest()!=c['document_sha256']:raise ValueError('capture_document_hash_mismatch')
            old=result['captures'].get(c['snapshot_id'])
            if (old and old!=c) or c['snapshot_id'] in poisoned:
                poisoned.add(c['snapshot_id']);result['captures'].pop(c['snapshot_id'],None);raise ValueError('conflicting_snapshot_id')
            result['captures'][c['snapshot_id']]=c
        except (ValueError,KeyError,TypeError,AttributeError) as e:result['gaps'].append({'reason':str(e),'evidence':proof})
    for proof in data.get('actions',[]):
        try:
            a=obj(proof)
            for when in ['started_at','finished_at']:moment(a[when])
            for prefix in ['before','after']:
                c=result['captures'][a[prefix+'_snapshot']]
                if c['document_sha256']!=a[prefix+'_sha256']:raise ValueError('action_capture_hash_mismatch')
            if a.get('source') not in {'actual browser fill; no submit','actual browser forecast growth fill; no submit'} or not a.get('action_id'):raise ValueError('action_provenance_required')
            result['actions'][a['action_id']]=a
        except (ValueError,KeyError,TypeError) as e:result['gaps'].append({'reason':str(e),'evidence':proof})
    for proof in data.get('references',[]):
        try:
            reference=obj(proof);key=reference['reference_id']
            if not key or key in result['references']:raise ValueError('reference_identity_missing_or_duplicate')
            result['references'][key]={**reference,'input_evidence':proof}
        except (ValueError,KeyError,TypeError) as e:result['gaps'].append({'reason':str(e),'evidence':proof})
    accepted={};conflicting=set()
    for proof in data.get('reviews',[]):
        try:
            review=obj(proof);review_time=moment(review['reviewed_at'])
            if review_time>moment(at) or not review.get('reviewer') or review.get('method')!='semantic_review_of_bound_evidence':raise ValueError('review_provenance_invalid')
            for check in review['checks']:
                try:
                    if check.get('kind') not in KINDS or not check.get('check_id'):raise ValueError('unknown_check_type_or_identity')
                    url_id(check['url']);citations=check.get('citations')
                    if not isinstance(citations,list) or not citations:raise ValueError('citations_required')
                    quotes=[];capture_times=[];urls=[]
                    for cite in citations:
                        c=result['captures'][cite['snapshot_id']]
                        if review.get('snapshot_bindings',{}).get(c['snapshot_id'])!=c['document_sha256']:raise ValueError('review_capture_binding_mismatch')
                        if moment(c['captured_at'])>review_time or not fresh(c['captured_at'],at,max_age_hours):raise ValueError('review_capture_time_invalid')
                        if c.get('readiness')!='ready':raise ValueError('capture_not_ready')
                        field=c['fields'][cite['field']]
                        if not field.get('present') or not field.get('visible') or field.get('count')!=1:raise ValueError('field_not_unique_visible_evidence')
                        quote=cite['quote']
                        if not isinstance(quote,str) or not any(isinstance(v,str) and quote in v for v in [field.get('text'),field.get('value')]):raise ValueError('quote_not_in_captured_field')
                        quotes.append(quote);capture_times.append(c['captured_at']);urls.append(url_id(c['url']))
                    if url_id(check['url']) not in urls:raise ValueError('review_url_not_captured')
                    if any(t not in capture_times for t in observation_times(check['payload'])):raise ValueError('observation_time_not_bound_to_capture')
                    if any(s not in {c['snapshot_id'] for c in citations} for s in statement_snapshots(check['payload'])):raise ValueError('statement_snapshot_not_cited')
                    if check['kind']=='claim':
                        if check['payload'].get('reviewed') is not True:raise ValueError('claim_semantics_unreviewed')
                        if check['payload'].get('reference_scope')=='official_api':
                            p=check['payload'];reference=result['references'][p['reference_id']]
                            state=review_response(reference,symbol=p['reference_symbol'],at=at,max_age_hours=max_age_hours)
                            if state['state']=='unknown' or p.get('reference_state')!=state['state'] or p.get('reference_market')!='spot' or p.get('reference_status')!='ok' or p.get('reference_at')!=reference.get('captured_at'):raise ValueError('official_reference_state_not_supported_by_response')
                            if moment(reference['captured_at'])>review_time:raise ValueError('reference_after_review')
                        if check['payload'].get('kind')=='numeric_display' and not any(str(check['payload'].get('raw')) in q for q in quotes):raise ValueError('numeric_display_raw_not_cited')
                    for number in numeric_nodes(check['payload']):
                        parsed=parse_quantity(number['raw'],decimal_mark=number.get('decimal_mark','.'),group_mark=number.get('group_mark',','),exact=number.get('exact',False))
                        if any(parsed.get(k)!=number.get(k) for k in ['status','value','quantum']):raise ValueError('numeric_representation_not_from_raw')
                        if number['raw'] is not None and str(number['raw']).strip() and not any(str(number['raw']) in quote for quote in quotes):raise ValueError('numeric_raw_not_cited')
                    if check['kind']=='calculator':bind_trial(check['payload'],review,result['captures'],result['actions'])
                    entry={**check,'reviewer':review['reviewer'],'reviewed_at':review['reviewed_at'],'review_evidence':proof,'capture_times':capture_times}
                    key=(url_id(check['url']),check['kind'],check['check_id'])
                    if key in accepted and accepted[key]!=entry:conflicting.add(key);raise ValueError('conflicting_check_identity')
                    accepted[key]=entry
                except (ValueError,KeyError,TypeError,AttributeError) as e:result['gaps'].append({'check_id':check.get('check_id'),'url':check.get('url'),'reason':str(e)})
        except (ValueError,KeyError,TypeError) as e:result['gaps'].append({'reason':str(e),'evidence':proof})
    result['checks']=[v for k,v in accepted.items() if k not in conflicting]
    return result
