"""Determine observed readiness from bounded snapshots, never from network-idle alone."""
import json
import math
from .shared import moment,url_id

FIELDS={'url','title','canonical','h1','identity'}

def evaluate(samples,policy,*,started_at):
    start=moment(started_at)
    budget=policy.get('max_wait_ms',30000);count=policy.get('min_stable_samples',2);window=policy.get('stable_window_ms',1000)
    fields=policy.get('stable_fields',['title','canonical','h1','identity'])
    if not isinstance(budget,(int,float)) or not math.isfinite(budget) or budget<=0:raise ValueError('invalid_wait_budget')
    if type(count) is not int or count<1:raise ValueError('invalid_stable_sample_count')
    if not isinstance(window,(int,float)) or not math.isfinite(window) or window<0:raise ValueError('invalid_stable_window')
    if not isinstance(fields,list) or not fields or not set(fields)<=FIELDS:raise ValueError('invalid_stable_fields')
    result={'state':'pending','snapshot_id':None,'unmet':[],'samples_used':[],'elapsed_ms':0}
    if not samples:result['unmet']=['browser_dom_not_observed'];return result
    latest=samples[-1];result['snapshot_id']=latest.get('id')
    try:
        times=[moment(s['captured_at']) for s in samples]
        if any(t<start for t in times) or times!=sorted(times):raise ValueError('invalid_capture_sequence')
        if any(not s.get('id') or not s.get('navigation_id') or not s.get('source') for s in samples):raise ValueError('snapshot_identity_required')
    except (ValueError,KeyError):
        result['state']='invalid_evidence';result['unmet']=['invalid_capture_sequence_or_identity'];return result
    result['elapsed_ms']=(times[-1]-start).total_seconds()*1000
    unmet=[]
    if latest.get('stage') not in {'dom','interaction'}:unmet.append('browser_dom_not_observed')
    if not isinstance(latest.get('main_text'),str) or not latest['main_text'].strip():unmet.append('main_content_missing')
    placeholders=latest.get('placeholder_count')
    if type(placeholders) is not int or placeholders<0:unmet.append('placeholder_state_unknown')
    elif placeholders:unmet.append('placeholders_present')
    wanted=policy.get('required_identity')
    if wanted is not None and str(latest.get('identity') or '').strip().casefold()!=str(wanted).strip().casefold():
        unmet.append('expected_identity_not_observed')
    if latest.get('page_errors'):
        result.update({'state':'page_error','unmet':unmet+['visible_page_error'],'page_errors':latest['page_errors']});return result
    def group(sample):
        return (url_id(sample['url']),sample['navigation_id'],sample.get('entry_mode'),sample.get('phase_id',sample.get('stage')),
            json.dumps(sample.get('environment'),sort_keys=True))
    def signature(sample):return json.dumps({k:sample.get(k) for k in fields},sort_keys=True,ensure_ascii=False)
    stable=[];seen=set()
    try:
        expected_group=group(latest);expected_signature=signature(latest)
        for sample in reversed(samples):
            if group(sample)!=expected_group or signature(sample)!=expected_signature:break
            if sample.get('stage') not in {'dom','interaction'} or sample.get('page_errors'):break
            if not isinstance(sample.get('main_text'),str) or not sample['main_text'].strip():break
            if type(sample.get('placeholder_count')) is not int or sample['placeholder_count']!=0:break
            if wanted is not None and str(sample.get('identity') or '').strip().casefold()!=str(wanted).strip().casefold():break
            if sample['id'] not in seen:stable.append(sample);seen.add(sample['id'])
    except (ValueError,KeyError,TypeError):
        result['state']='invalid_evidence';result['unmet']=['invalid_snapshot_fields'];return result
    span=(moment(stable[0]['captured_at'])-moment(stable[-1]['captured_at'])).total_seconds()*1000 if stable else 0
    result['samples_used']=[s['id'] for s in reversed(stable)]
    if len(stable)<count:unmet.append('stable_samples_missing')
    if span<window:unmet.append('stable_window_too_short')
    result['unmet']=unmet
    result['state']='ready' if not unmet else 'unknown_timeout' if result['elapsed_ms']>=budget else 'pending'
    return result
