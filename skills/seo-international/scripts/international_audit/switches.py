"""Verify actual language switch against bound body/entity reviews."""
from .shared import fresh,moment
from .content import review_content,primary

def review_switch(before,after,action,reviews,*,at,max_age_hours=168):
    out={'outcome':'unknown','observations':[],'gaps':[],'action':action}
    if not action.get('source') or not action.get('selector') or not fresh(action.get('clicked_at'),at,max_age_hours):out['gaps'].append('switch_action_provenance');return out
    for prefix,c in [('before',before),('after',after)]:
        if any(action.get(prefix+'_'+key)!=c.get(field) for key,field in [('snapshot','snapshot_id'),('sha256','document_sha256'),('url','url')]):out['gaps'].append('switch_snapshot_binding');return out
        if c.get('state')!='completed' or c.get('readiness')!='ready' or not fresh(c['captured_at'],at,max_age_hours):out['gaps'].append('switch_capture_not_ready');return out
    if not moment(before['captured_at'])<=moment(action['clicked_at'])<=moment(after['captured_at']):out['gaps'].append('switch_time_order');return out
    # Distinct snapshots from the same URL are deliberate before/after phases.
    verified=[]
    for c in [before,after]:
        result=review_content([c],[r for r in reviews if r.get('snapshot_id')==c['snapshot_id']],[],at=at,max_age_hours=max_age_hours)
        verified+=result['body_reviews']
    by_id={r['snapshot_id']:r for r in verified};left=by_id.get(before['snapshot_id']);right=by_id.get(after['snapshot_id'])
    if not left or not right or not left.get('entity_id') or not right.get('entity_id'):out['gaps'].append('switch_body_entity_review_missing');return out
    out['outcome']='entity_preserved' if left['entity_id']==right['entity_id'] else 'entity_changed'
    if out['outcome']=='entity_changed':out['observations'].append({'url':before['url'],'rule':'language_switch_entity_changed','classification':'evidence_supported_review','detail':{'before_review':left,'after_review':right,'action':action}})
    expected=primary(action.get('expected_locale'))
    if expected and expected!=primary(right['body_language']):out['observations'].append({'url':before['url'],'rule':'language_switch_body_language_mismatch','classification':'evidence_supported_review','detail':{'expected_locale':action['expected_locale'],'after_review':right,'action':action}})
    elif not expected:out['gaps'].append('switch_expected_locale_unresolved')
    return out
