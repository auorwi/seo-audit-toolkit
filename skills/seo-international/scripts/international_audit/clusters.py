"""Observed multilingual declarations, not an assertion of global index coverage."""
from collections import defaultdict
from .shared import url_id,moment,fresh
from .locale import validate_locale

def current_captures(captures,at,max_age_hours=168):
    latest={};gaps=[];accepted=[]
    for c in captures:
        key=(url_id(c['url']),c['representation'],c.get('entry_mode','direct'),c.get('channel_scope',''))
        if key not in latest or moment(c['captured_at'])>=moment(latest[key]['captured_at']):latest[key]=c
    for c in latest.values():
        reason=None
        if not fresh(c['captured_at'],at,max_age_hours):reason='capture_not_fresh'
        elif c.get('state')!='completed':reason='latest_capture_failed'
        elif c['representation']=='rendered_html' and c.get('readiness')!='ready':reason='latest_rendered_not_ready'
        if reason:gaps.append({'url':c['url'],'reason':reason,'snapshot_id':c['snapshot_id']})
        else:accepted.append(c)
    return accepted,gaps

def review_clusters(captures,assets,*,at,max_age_hours=168):
    cs,gaps=current_captures(captures,at,max_age_hours);rows=[];observations=[];edges=[];by_source=defaultdict(list)
    mapping={url_id(a['url']):a for a in assets};observed={url_id(c['url']) for c in cs}
    def add(rule,url,detail,classification='review_candidate'):
        observations.append({'rule':rule,'url':url,'classification':classification,'detail':detail})
    for c in cs:
        for a in c.get('alternates',[]):
            row={**a,'snapshot_id':c['snapshot_id'],'document_sha256':c.get('document_sha256'),'captured_at':c['captured_at'],'representation':c['representation'],'entry_mode':c.get('entry_mode','direct')}
            code=validate_locale(a.get('locale'));row['locale_validation']=code;rows.append(row)
            source=url_id(a['source_url']);by_source[source].append(row)
            if not a.get('eligible'):add('hreflang_declaration_ineligible',source,row,'declaration_problem');continue
            if code['google_status'] not in {'supported','fallback'}:
                add('hreflang_code_unsupported' if code['google_status']=='unsupported' else 'hreflang_code_review',source,row,'declaration_problem' if code['google_status']=='unsupported' else 'review_candidate');continue
            edges.append(row)
    edge_sources=defaultdict(list)
    for e in edges:edge_sources[e['source_url']].append(e)
    for source,declarations in by_source.items():
        valid=edge_sources[source];locales=defaultdict(set)
        for r in valid:locales[r['locale_validation']['normalized']].add(r['target_url'])
        for locale,targets in locales.items():
            if len(targets)>1:add('hreflang_locale_conflict',source,{'locale':locale,'targets':sorted(targets),'declarations':[d for d in valid if d['locale_validation']['normalized']==locale]},'observed_conflict')
        if valid and not any(r['target_url']==source for r in valid):add('hreflang_self_not_observed',source,{'observed_channels':sorted({d['channel'] for d in declarations})})
    seen=set()
    for e in edges:
        source,target=e['source_url'],e['target_url'];key=(source,target)
        if key in seen or source==target:continue
        seen.add(key)
        if target not in observed:gaps.append({'url':target,'source_url':source,'reason':'target_declarations_unobserved'})
        elif not any(back['target_url']==source for back in edge_sources[target]):add('hreflang_return_not_observed',source,{'target_url':target,'declaration':e,'limitation':'Only supplied declaration channels checked; uncollected HTTP/Sitemap may differ.'})
        left,right=mapping.get(source),mapping.get(target)
        if left and right and left.get('entity_id') and right.get('entity_id') and left['entity_id']!=right['entity_id']:add('hreflang_entity_mapping_mismatch',source,{'target_url':target,'source_mapping':left,'target_mapping':right})
    for source in observed:
        asset=mapping.get(source)
        if not asset or asset.get('published') is not True or not asset.get('entity_id'):continue
        declared={e['target_url'] for e in edge_sources[source]}
        for target,other in mapping.items():
            if target!=source and other.get('published') is True and other.get('entity_id')==asset['entity_id'] and target not in declared:add('published_variant_not_declared',source,{'target_url':target,'mapping':other})
    return {'declarations':rows,'edges':edges,'observations':observations,'gaps':gaps,'observed_urls':sorted(observed)}
