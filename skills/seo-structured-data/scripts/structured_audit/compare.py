"""Compare complete current captures; changes are observations, not ranking errors."""
import json
from collections import Counter
from .shared import fresh,url_id

def compare_snapshots(before,after,*,at,max_age_hours=168):
    result={'observations':[],'gaps':[]}
    if url_id(before['url'])!=url_id(after['url']):result['gaps'].append('different_url_comparison');return result
    for capture in [before,after]:
        if not fresh(capture.get('captured_at'),at,max_age_hours) or not capture.get('extraction_complete') or (capture.get('representation')=='rendered_html' and capture.get('readiness')!='ready'):
            result['gaps'].append({'snapshot_id':capture.get('snapshot_id'),'reason':'current_complete_capture_required'})
    if result['gaps']:return result
    def fingerprint(entity):return json.dumps({k:v for k,v in entity['data'].items() if k!='@context'},ensure_ascii=False,sort_keys=True,separators=(',',':'))
    def key(entity):
        id=entity.get('id')
        return id if id and not id.startswith('_:') else str(entity.get('syntax','json-ld'))+'|'+str(entity.get('script_index',0))+'|'+entity['path']+'|'+','.join(sorted(entity['types']))
    def emit(rule,classification,**kw):result['observations'].append({'rule':rule,'classification':classification,'before_snapshot':before['snapshot_id'],'after_snapshot':after['snapshot_id'],'before_document_sha256':before['document_sha256'],'after_document_sha256':after['document_sha256'],**kw})
    left=Counter(fingerprint(e) for e in before['entities']);right=Counter(fingerprint(e) for e in after['entities'])
    for signature,count in right.items():
        if count>1 and count>left[signature]:emit('repeated_definition_increase','duplicate_candidate',definition=json.loads(signature),before_count=left[signature],after_count=count)
    if left!=right:
        same_stage=before.get('representation')==after.get('representation')=='rendered_html'
        entry_difference=same_stage and before.get('entry_mode')!=after.get('entry_mode') and all(c.get('entry_mode') for c in [before,after])
        emit('entry_path_schema_difference' if entry_difference else 'schema_changed_between_stages','entry_path_review' if entry_difference else 'stage_observation',
            added=[{'definition':json.loads(s),'count':n} for s,n in (right-left).items()],removed=[{'definition':json.loads(s),'count':n} for s,n in (left-right).items()])
    removed={key(e) for e in before['entities']}-{key(e) for e in after['entities']}
    for identity in sorted(removed):emit('schema_entity_removed','stage_observation',entity_identity=identity)
    return result
