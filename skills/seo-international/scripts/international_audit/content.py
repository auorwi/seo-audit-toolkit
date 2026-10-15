"""Language assertions require reviewed quotations from the captured visible main."""
from .clusters import current_captures
from .shared import fresh,url_id,moment
from .locale import validate_locale

def primary(value):
    r=validate_locale(value)
    return r['language'] if r['bcp_status']=='registered_subset' else None

def review_content(captures,reviews,assets,*,at,max_age_hours=168):
    cs,gaps=current_captures(captures,at,max_age_hours);ids={c['snapshot_id']:c for c in cs};accepted=[];observations=[]
    maps={url_id(a['url']):a for a in assets}
    def add(rule,c,detail):observations.append({'url':c['url'],'rule':rule,'classification':'evidence_supported_review','detail':detail,'snapshot_id':c['snapshot_id']})
    for r in reviews:
        c=ids.get(r.get('snapshot_id'));reason=None
        if not c or any(c.get(k)!=r.get(k) for k in ['url','document_sha256']):reason='body_review_binding'
        elif not fresh(r.get('reviewed_at'),at,max_age_hours) or moment(r['reviewed_at'])<moment(c['captured_at']):reason='body_review_not_fresh'
        elif not r.get('source') or r.get('method') not in {'human_review','llm_review'} or r.get('confidence')!='high':reason='body_review_confidence_or_method'
        elif not primary(r.get('body_language')):reason='body_language_unresolved'
        elif not c.get('visible_main') or not isinstance(r.get('quotes'),list) or not r['quotes'] or any(not isinstance(q,str) or not q.strip() or q not in c['visible_main'] for q in r['quotes']):reason='body_quote_not_in_visible_main'
        if reason:gaps.append({'url':r.get('url'),'reason':reason,'snapshot_id':r.get('snapshot_id')});continue
        accepted.append(r);lang=primary(r['body_language'])
        for declared in c.get('html_langs',[]):
            if not primary(declared):add('html_lang_code_review',c,{'html_lang':declared,'review':r})
            left_script=validate_locale(declared)['script'];right_script=validate_locale(r['body_language'])['script']
            if left_script and right_script and left_script!=right_script:add('html_body_script_mismatch',c,{'html_lang':declared,'review':r})
            if primary(declared) and primary(declared)!=lang:add('html_body_language_mismatch',c,{'html_lang':declared,'review':r})
        for declared in c.get('schema_languages',[]):
            if primary(declared.get('value')) and primary(declared['value'])!=lang:add('schema_body_language_review',c,{'declaration':declared,'review':r,'limitation':'Check the Schema entity scope; quoted or embedded content may legitimately use another language.'})
        asset=maps.get(url_id(c.get('requested_url') or c['url'])) or maps.get(url_id(c['url']),{})
        if primary(asset.get('locale')) and primary(asset['locale'])!=lang:add('route_body_language_mismatch',c,{'expected_mapping':asset,'review':r,'requested_url':c.get('requested_url')})
    by_url={}
    for r in accepted:by_url.setdefault(r['url'],[]).append(r)
    for url,variants in list(by_url.items()):
        if len({(primary(r['body_language']),validate_locale(r['body_language'])['script'],r.get('entity_id')) for r in variants})>1:
            gaps.append({'url':url,'reason':'body_review_variants_conflict','reviews':variants});by_url[url]=None
        else:by_url[url]=variants[-1]
    for c in cs:
        asset=maps.get(url_id(c.get('requested_url') or c['url'])) or maps.get(url_id(c['url']),{})
        for field in asset.get('required_fields',[]):
            seen=c.get('visible_fields',{}).get(field)
            if seen is False:add('localized_required_field_missing',c,{'field':field,'requirement_mapping':asset})
            elif seen is not True:gaps.append({'url':c['url'],'reason':'required_field_unobserved','field':field})
        source=next((r for r in accepted if r['snapshot_id']==c['snapshot_id']),None)
        for canonical in c.get('canonicals',[]):
            target=canonical.get('target_url')
            if not target or target==c['url']:continue
            peer=by_url.get(target)
            if not source or not peer:gaps.append({'url':c['url'],'reason':'canonical_body_comparison_unobserved','target_url':target});continue
            if source.get('entity_id') and peer.get('entity_id') and source['entity_id']!=peer['entity_id']:add('canonical_entity_review',c,{'canonical':canonical,'source_review':source,'target_review':peer})
            elif primary(source['body_language'])!=primary(peer['body_language']):add('translated_body_cross_language_canonical',c,{'canonical':canonical,'source_review':source,'target_review':peer,'policy':asset.get('canonical_policy'),'limitation':'Confirm substantive translation, entity equivalence and canonical policy; this does not prove the engine selected the target.'})
        if c['representation']=='rendered_html' and c['url'] not in by_url:gaps.append({'url':c['url'],'reason':'body_language_review_missing'})
    return {'body_reviews':accepted,'observations':observations,'gaps':gaps}
