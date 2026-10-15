"""Explicit locale expectations versus observed target html lang; no route guessing."""
from .shared import url_id,moment,fresh

def review_language(captures,expectations,*,at,max_age_hours=168,target_assessments=None):
    latest={};result={'observations':[],'gaps':[]}
    redirects={url_id(x['requested_url']):x for x in target_assessments or [] if x.get('kind')=='redirected_link'}
    for c in captures:
        if c.get('representation')!='rendered_html':continue
        url=url_id(c['url'])
        if url not in latest or moment(c['captured_at'])>moment(latest[url]['captured_at']):latest[url]=c
    def ready(c):return c and c.get('state','completed')=='completed' and c.get('readiness')=='ready' and fresh(c.get('captured_at'),at,max_age_hours)
    for expected in expectations:
        try:
            if not expected.get('source') or not fresh(expected.get('checked_at'),at,max_age_hours):raise ValueError('language_expectation_provenance')
            source=next((c for c in captures if c.get('snapshot_id')==expected.get('source_snapshot') and url_id(c['url'])==url_id(expected['source_url'])),None)
            if source:
                peers=[c for c in captures if url_id(c['url'])==url_id(source['url']) and c.get('representation')==source.get('representation') and c.get('entry_mode')==source.get('entry_mode')]
                if max(peers,key=lambda c:moment(c['captured_at']))['snapshot_id']!=source['snapshot_id']:raise ValueError('language_source_binding')
            requested=url_id(expected['target_url']);redirect=redirects.get(requested);final=url_id(redirect['final_url']) if redirect else requested;target=latest.get(final)
            if not ready(source) or not ready(target):raise ValueError('current_ready_source_and_target_required')
            if expected.get('source_snapshot')!=source['snapshot_id'] or expected.get('source_document_sha256')!=source['document_sha256']:raise ValueError('language_source_binding')
            links=[x for x in source.get('links',[]) if x.get('locator')==expected.get('locator') and x.get('target') and url_id(x['target'])==url_id(expected['target_url'])]
            if not links:raise ValueError('language_link_binding')
            if expected.get('purpose')=='language_switch':continue
            observed=target.get('html_lang');wanted=expected.get('expected_language')
            if not isinstance(observed,str) or not observed.strip() or not isinstance(wanted,str) or not wanted.strip():raise ValueError('language_declaration_or_expectation_missing')
            if observed.lower().split('-')[0]!=wanted.lower().split('-')[0]:result['observations'].append({'rule':'target_declared_language_mismatch','url':source['url'],'target_url':requested,'final_url':final,'redirect_assessment':redirect,'expected_language':wanted,'observed_language':observed,'classification':'review','handoff_skill':'010','expectation':expected,'target_snapshot':target['snapshot_id'],'target_document_sha256':target['document_sha256'],'limitation':'html lang declaration only; body language and locale-group correctness need 010 review.'})
        except (ValueError,KeyError,TypeError) as error:result['gaps'].append({'reason':str(error),'source_url':expected.get('source_url')})
    return result
