"""Prepare separately captured HTTP baselines; never relabel them browser responses."""
import hashlib
import json
import math
from pathlib import Path
from .shared import moment,fresh,url_id
from crawlability.adapters import load_inventory

def prepare_inventory(inventory,bindings,output,*,at,max_age_hours=168):
    moment(at)
    if not bindings:raise ValueError('explicit_bindings_required')
    if not math.isfinite(max_age_hours) or max_age_hours<=0:raise ValueError('invalid_freshness_window')
    for b in bindings:
        url_id(b['url'])
        if not b.get('navigation_id') or b.get('entry_mode') not in {'direct','internal','back'}:raise ValueError('invalid_navigation_binding')
    output=Path(output)
    if output.exists() and any(output.iterdir()):raise ValueError('output_directory_not_empty')
    loaded=load_inventory(inventory,[b['url'] for b in bindings])
    result={'schema_version':1,'snapshots':[],'interactions':[],'gaps':[]}
    output.mkdir(parents=True,exist_ok=True)
    for binding in bindings:
        url=url_id(binding['url'])
        candidates=[r for r in loaded['records'] if url_id(r['url'])==url]
        latest=max(enumerate(candidates),key=lambda item:(moment(item[1]['checked_at']),item[0]))[1] if candidates else None
        reason=None
        if latest is None:reason='initial_http_not_observed'
        elif not fresh(latest['checked_at'],at,max_age_hours):reason='initial_http_not_current'
        elif latest.get('error') or latest.get('status')!=200:reason='initial_http_not_successful_document'
        elif not any(k=='content-type' and v.split(';')[0].strip().lower() in {'text/html','application/xhtml+xml'} for k,v in latest['headers']):reason='initial_http_not_html'
        elif 'body' not in latest:reason=latest.get('evidence_error','initial_body_missing')
        if reason:
            result['gaps'].append({'url':url,'reason':reason,'capture_id':latest.get('capture_id') if latest else None});continue
        body=latest['body'];digest=hashlib.sha256(body).hexdigest();name=digest+'.html'
        (output/name).write_bytes(body)
        identity='http-'+hashlib.sha256((latest['capture_id']+'|'+binding['navigation_id']+'|'+binding['entry_mode']).encode()).hexdigest()[:24]
        result['snapshots'].append({'id':identity,'url':url,'requested_url':url,'stage':'initial','kind':'initial_html',
            'entry_mode':binding['entry_mode'],'navigation_id':binding['navigation_id'],'source':'001 independent HTTP capture '+latest['capture_id'],
            'captured_at':latest['checked_at'],'http_status':latest['status'],'baseline_relation':'independent_http',
            'environment':latest.get('environment'),'evidence':{'path':name,'sha256':digest,'bytes':len(body)}})
    (output/'manifest.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return result
