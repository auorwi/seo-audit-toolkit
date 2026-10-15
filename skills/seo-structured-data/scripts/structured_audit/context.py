"""Evidence-bound visible-content reviews and conservative numeric examples."""
import re
from .shared import fresh,url_id
from .rules import numeric

def review_context(capture,context,*,at,max_age_hours=168):
    result={'profile':None,'observations':[],'examples':[],'gaps':[],'pending':['type_applicability','visible_content_accuracy','engine_validation','actual_display']}
    try:
        if not context:raise ValueError('visible_context_not_observed')
        if capture.get('representation')!='rendered_html' or capture.get('readiness')!='ready' or not fresh(capture.get('captured_at'),at,max_age_hours):raise ValueError('current_ready_dom_required')
        if not context.get('source') or not fresh(context.get('checked_at'),at,max_age_hours):raise ValueError('context_provenance_or_time')
        if url_id(context['url'])!=url_id(capture['url']) or any(context.get(k)!=capture.get(k) for k in ['snapshot_id','document_sha256']):raise ValueError('context_document_binding')
        text=capture.get('visible_text')
        if not isinstance(text,str):raise ValueError('visible_text_not_captured')
        def quoted(value):return isinstance(value,str) and bool(value.strip()) and ' '.join(value.split()) in ' '.join(text.split())
        profile=context.get('profile')
        if profile:
            if profile.get('name') not in {'google_product_snippet','google_software_app','google_breadcrumb'} or not quoted(profile.get('quote')) or not profile.get('reason') or not isinstance(profile.get('applicable'),bool):raise ValueError('profile_applicability_evidence')
            if profile['applicable']:result['profile']=profile['name']
        for check in context.get('checks',[]):
            try:
                if not fresh(check.get('observed_at'),at,max_age_hours) or not check.get('selector') or not check.get('reason') or not quoted(check.get('visible_quote')):raise ValueError('field_visible_evidence')
                entities=[e for e in capture['entities'] if e.get('id')==check.get('entity_id') and (not check.get('entity_path') or e['path']==check['entity_path']) and ('script_index' not in check or e.get('script_index')==check['script_index'])]
                values=[e['data'][check['field']] for e in entities if check.get('field') in e['data']]
                if not values or any(v!=check.get('schema_value') for v in values):raise ValueError('schema_field_binding_or_ambiguity')
                if check.get('status') not in {'format_issue','mismatch','matches','unknown'}:raise ValueError('unknown_field_review_status')
                if check['status'] in {'unknown','matches'}:continue
                observed={'rule':'schema_visible_content_review','classification':'visible_content_review','entity_id':check['entity_id'],'field':check['field'],
                    'schema_value':check['schema_value'],'visible_quote':check['visible_quote'],'selector':check['selector'],'reason':check['reason'],'source':context['source'],
                    'snapshot_id':capture['snapshot_id'],'document_sha256':capture['document_sha256'],'script_index':check.get('script_index'),'entity_path':check.get('entity_path')}
                result['observations'].append(observed)
                proposed=check.get('recommended_value')
                if proposed is not None:
                    if check['field'] not in {'price','lowPrice','highPrice','ratingValue','ratingCount','reviewCount'} or not check.get('update_rule'):raise ValueError('example_requires_supported_numeric_field_and_update_rule')
                    raw=check['visible_quote'].strip()
                    # Only an unambiguous conventional numeric token is rewritten; never guess locale or fill blanks.
                    if not re.fullmatch(r'\$?(?:[0-9]+|[0-9]{1,3}(?:,[0-9]{3})+)(?:\.[0-9]+)?',raw):raise ValueError('visible_numeric_value_not_unambiguous')
                    value=numeric(raw.lstrip('$').replace(',',''))
                    if numeric(proposed) is None or numeric(proposed)!=value:raise ValueError('example_value_not_supported')
                    result['examples'].append({**observed,'recommended_value':proposed,'example_only':True,'update_rule':check['update_rule'],'limitations':'Captured-time numeric formatting example only; verify currency, product and freshness before deployment.'})
            except (ValueError,KeyError,TypeError,AttributeError) as error:result['gaps'].append(str(error))
    except (ValueError,KeyError,TypeError,AttributeError) as error:result['gaps'].append(str(error))
    return result
