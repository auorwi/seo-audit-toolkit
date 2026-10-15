"""Compare evidence-bound pagination interactions and separate direct-load behavior."""
from urllib.parse import urljoin
from .shared import url_id,moment,fresh

def review_pagination(before,after,action,*,direct=None,at,max_age_hours=168):
    result={'observations':[],'gaps':[],'transition':'unverified','direct_result':'unverified','all_items_unindexable_proven':False}
    def usable(p):return p and p.get('source') and p.get('readiness')=='ready' and fresh(p.get('captured_at'),at,max_age_hours) and isinstance(p.get('item_keys'),list) and bool(p['item_keys']) and all(isinstance(x,str) and x for x in p['item_keys'])
    try:
        if not usable(before) or not usable(after):raise ValueError('pagination_current_ready_items_required')
        if not action.get('source') or not action.get('selector'):raise ValueError('pagination_action_provenance_required')
        for label,p in [('before',before),('after',after)]:
            if action.get(label+'_snapshot')!=p.get('snapshot_id') or action.get(label+'_document_sha256')!=p.get('document_sha256'):raise ValueError('pagination_document_binding')
        if not moment(before['captured_at'])<=moment(action['clicked_at'])<=moment(after['captured_at']):raise ValueError('pagination_action_time_sequence')
        control=action['control']
        if control.get('disabled') is True:result['transition']='disabled_control';return result
        if set(before['item_keys'])==set(after['item_keys']):result['transition']='items_unchanged';result['gaps'].append('pagination_transition_not_demonstrated');return result
        result['transition']='different_items_observed'
        proof={'before_snapshot':before['snapshot_id'],'after_snapshot':after['snapshot_id'],'before_document_sha256':before['document_sha256'],'after_document_sha256':after['document_sha256'],'before_url':before['url'],'after_url':after['url'],'selector':action['selector'],'clicked_at':action['clicked_at']}
        def emit(rule,**kw):result['observations'].append({'rule':rule,'classification':'pagination_review','evidence':proof,**kw})
        same=url_id(before['url'])==url_id(after['url'])
        if same:emit('pagination_same_document_address',reason='Changed observed item identities share a document URL; check addressability and alternate discovery routes.')
        hrefs={url_id(x['target']) for x in before.get('links',[]) if x.get('http_link') and x.get('target') and not x.get('conditional_noscript') and url_id(x['target'])!=url_id(before['url'])}
        declared=None
        if str(control.get('tag','')).lower()=='a' and control.get('href'):
            try:
                candidate=url_id(urljoin(before['url'],control['href']))
                if candidate in hrefs:declared=candidate
            except ValueError:pass
        if declared is None and not same and url_id(after['url']) in hrefs:declared=url_id(after['url'])
        result['declared_target_url']=declared
        if declared is None:emit('pagination_href_not_observed',reason='No distinct HTTP anchor destination for this next-page state was observed in the supplied before snapshot.')
        direct_expected=declared or url_id(after['url'])
        if not usable(direct) or url_id(direct.get('requested_url',direct['url']))!=direct_expected:result['gaps'].append('pagination_matching_ready_direct_load_not_observed')
        elif set(direct['item_keys'])==set(after['item_keys']):result['direct_result']='same_items_observed'
        else:
            result['direct_result']='different_items_observed';emit('pagination_direct_content_difference',direct_snapshot=direct['snapshot_id'],direct_document_sha256=direct['document_sha256'],reason='Direct load and clicked state expose different item identities; assess time-dependent ordering before assigning a route defect.')
    except (ValueError,KeyError,TypeError,AttributeError) as error:result['gaps'].append(str(error))
    return result
