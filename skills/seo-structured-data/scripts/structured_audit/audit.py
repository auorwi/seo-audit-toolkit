"""Scope, current capture selection and four-layer structured-data evidence."""

import sys as _site_sys
from pathlib import Path as _SitePath
_site_dependency=_SitePath(__file__).resolve().parents[3]/'seo-crawlability/scripts'
if str(_site_dependency) not in _site_sys.path:_site_sys.path.insert(0,str(_site_dependency))
from crawlability.site import get_profile,site_host,site_origin,allowed_hosts,in_scope,require_url,brand_name,business_profile
import hashlib,json,math
from urllib.parse import urlsplit
from .shared import moment,fresh,url_id
from .embedded import normalize_extruct
from .rules import audit_entities
from .vocabulary import review_terms
from .context import review_context
from .compare import compare_snapshots
from .engine import assess_engine_evidence

def audit(captures,targets,*,at,max_age_hours=168,vocabulary=None,engine_reports=None):
    moment(at)
    if not math.isfinite(max_age_hours) or max_age_hours<=0:raise ValueError('invalid_freshness_window')
    scope={}
    for target in targets:
        target={'url':target,'entries':['direct','internal']} if isinstance(target,str) else target
        url=url_id(target['url']);host=urlsplit(url).hostname
        if not in_scope(url):raise ValueError('configured_site_scope_required')
        entries=target.get('entries',['direct','internal'])
        if not isinstance(entries,list) or not entries or not set(entries)<={'direct','internal','history_return'}:raise ValueError('invalid_entry_scope')
        if url in scope and scope[url]!=entries:raise ValueError('conflicting_entry_scope')
        scope[url]=entries
    if not scope:raise ValueError('explicit_nonempty_url_scope_required')
    seen={}
    for c in captures:
        if c['snapshot_id'] in seen and seen[c['snapshot_id']]!=c:raise ValueError('conflicting_capture_identity')
        seen[c['snapshot_id']]=c
    result={'schema_version':1,'configured_site':site_host(),'skill':'008','at':at,'scope':list(scope),'entry_scope':scope,'rows':[],'findings':[],'comparisons':[],
        'gaps':[],'pending_reviews':[],'examples':[],'engine_results':[],'entity_inventory':[],'graph_edges':[],'vocabulary_source':{k:v for k,v in (vocabulary or {}).items() if k!='terms'},
        'coverage':{'requested_urls':len(scope),'ready_documents':0,'complete_extractions':0,'full_site':False,'full_schema_certification':False}}
    vocab_valid=vocabulary and fresh(vocabulary.get('retrieved_at'),at,max_age_hours) and vocabulary.get('terms')
    if not vocab_valid:result['gaps'].append({'reason':'current_vocabulary_snapshot_not_available'})
    def gap(url,reason,**kw):result['gaps'].append({'url':url,'reason':reason,**kw})
    def add(c,observation,layer=None):
        rule=observation['rule'];field=observation.get('field',observation.get('property',observation.get('key','@type' if 'type' in observation else '')))
        anchor=observation.get('entity_id') or observation.get('entity_path') or observation.get('path','$')
        key=site_host()+'|008|'+url_id(c['url'])+'|'+rule+'|'+str(anchor)+'|'+str(field)
        evidence={'snapshot_id':c.get('snapshot_id'),'document_sha256':c.get('document_sha256'),'captured_at':c.get('captured_at'),'representation':c.get('representation'),'entry_mode':c.get('entry_mode'),'source':c.get('source'),'observation':observation}
        result['findings'].append({'issue_id':'structured-'+hashlib.sha256(key.encode()).hexdigest()[:24],'url':url_id(c['url']),'rule':rule,'field':field,'entity':anchor,'owner_skill':'008','observed_at':at,
            'classification':observation.get('classification','syntax_observation' if layer=='syntax' else 'review'),'layer':layer or observation.get('layer','schema_semantics'),
            'value':observation.get('value',observation.get('values',observation.get('schema_value',observation.get('type')))),'source_url':observation.get('source_url'),
            'recommendation':observation.get('recommendation','核对该实体/字段的原始声明与当前可见内容，按对应规则修正；不猜测实际展示或补造评分。'),
            'retest':'复测同URL和进入方式的初始HTML、稳定DOM及适用引擎测试，保存新证据；页面未见不自动关闭平台历史。','evidence':[evidence]})
    for url,entries in scope.items():
        available=[c for c in seen.values() if url_id(c['url'])==url];selected=[]
        for entry in dict.fromkeys(entries):
            for representation in ['initial_html','rendered_html']:
                options=[c for c in available if c.get('representation')==representation and c.get('entry_mode','direct')==entry]
                if options:selected.append(max(options,key=lambda c:moment(c['captured_at'])))
                else:gap(url,representation+'_not_observed',entry_mode=entry)
        assessed=[]
        for c in selected:
            row={'url':url,'snapshot_id':c['snapshot_id'],'entry_mode':c.get('entry_mode','direct'),'representation':c['representation'],'status':'evidence_gap',
                'layers':{'syntax':'not_checked','schema_semantics':'not_checked','engine_eligibility':'unverified','actual_display':'unverified'}};result['rows'].append(row)
            ready=c.get('representation')!='rendered_html' or c.get('readiness')=='ready'
            if c.get('state','completed')!='completed' or not ready or not fresh(c.get('captured_at'),at,max_age_hours):gap(url,'latest_capture_not_current_complete_or_ready',snapshot_id=c['snapshot_id']);continue
            if c['representation']=='rendered_html':result['coverage']['ready_documents']+=1
            parsed=c['jsonld'];entities=[{**e,'syntax':'json-ld'} for e in parsed['entities']]
            for error in parsed['errors']:add(c,error,'syntax')
            for error in parsed['gaps']:gap(url,error,snapshot_id=c['snapshot_id'])
            embedded=None
            if c.get('extruct'):
                embedded=normalize_extruct(c['extruct'],url=url,document_sha256=c['document_sha256'],at=at,max_age_hours=max_age_hours);entities+=embedded['entities']
                for error in embedded['gaps']:gap(url,error,snapshot_id=c['snapshot_id'])
            else:gap(url,'extruct_microdata_rdfa_not_observed',snapshot_id=c['snapshot_id'])
            complete=bool(embedded and embedded['status']=='usable' and not parsed['errors'] and not parsed['gaps'])
            if complete:result['coverage']['complete_extractions']+=1
            for entity in entities:
                result['entity_inventory'].append({'url':url,'snapshot_id':c['snapshot_id'],'document_sha256':c['document_sha256'],**entity})
            references=[{**ref,'syntax':'json-ld'} for ref in parsed.get('references',[])]+(embedded['references'] if embedded else [])
            defined={e.get('id') for e in entities if e.get('id')}
            for ref in references:
                parents=[e for e in entities if e.get('syntax','json-ld')==ref.get('syntax','json-ld') and e.get('script_index',0)==ref.get('script_index',0) and ref['path'].startswith(e['path'])]
                parent=max(parents,key=lambda e:len(e['path'])) if parents else None
                result['graph_edges'].append({'url':url,'snapshot_id':c['snapshot_id'],'syntax':ref['syntax'],'from_entity':(parent.get('id') or parent['path']) if parent else None,'to_entity':ref['id'],'reference_path':ref['path'],'relationship':'declared_reference'})
                local=ref['id'].startswith('_:') or (bool(urlsplit(ref['id']).fragment) and url_id(ref['id'])==url_id(url))
                if complete and local and ref['id'] not in defined:add(c,{'rule':'unresolved_local_reference_review','classification':'reference_review','entity_path':ref['path'],'field':'@id','value':ref['id']})
            enriched={**c,'entities':entities,'extraction_complete':complete}
            context=review_context(enriched,c.get('context'),at=at,max_age_hours=max_age_hours) if c['representation']=='rendered_html' else {'profile':None,'observations':[],'examples':[],'gaps':[],'pending':[]}
            field_result=audit_entities(entities,profile=context['profile'])
            observations=list(field_result['observations'])
            if vocab_valid:
                for e in entities:
                    v=review_terms(e,vocabulary['terms'])
                    observations += [{**o,'entity_id':e.get('id'),'entity_path':e['path'],'source_url':vocabulary['source']} for o in v['observations']]
                    for error in v['gaps']:gap(url,error,snapshot_id=c['snapshot_id'])
            for o in observations:add(c,o)
            for o in context['observations']:add(c,o,'visible_content')
            result['examples']+=[{**example,'url':url} for example in context['examples']]
            for error in field_result['gaps']+context['gaps']:gap(url,error,snapshot_id=c['snapshot_id'])
            if context['pending']:result['pending_reviews'].append({'url':url,'snapshot_id':c['snapshot_id'],'topics':context['pending']})
            row.update(status='observed',entities=len(entities),extraction_complete=complete,profile=context['profile'])
            row['layers'].update(syntax='errors_observed' if parsed['errors'] else 'no_json_syntax_errors_observed' if parsed['scripts'] else 'no_jsonld_observed',schema_semantics='partial_rules_only')
            checked={o['rule'] for o in field_result['observations']}
            for e in entities:
                if not e.get('schema_context_known'):continue
                if any(k in e['data'] for k in ['price','lowPrice','highPrice']):checked.add('price_format_review')
                if set(e['types'])&{'Rating','AggregateRating'} and 'ratingValue' in e['data']:checked.update(['rating_number_review','rating_bounds_review'])
            enriched['checked_rules']=sorted(checked);enriched['observations']=observations;enriched['ready']=c['representation']=='rendered_html' and c.get('readiness')=='ready'
            assessed.append(enriched)
        for i,before in enumerate(assessed):
            for after in assessed[i+1:]:
                same_entry=before.get('entry_mode','direct')==after.get('entry_mode','direct')
                stage_pair=same_entry and before['representation']=='initial_html' and after['representation']=='rendered_html'
                entry_pair=not same_entry and before['representation']==after['representation']=='rendered_html'
                if not (stage_pair or entry_pair):continue
                comparison=compare_snapshots(before,after,at=at,max_age_hours=max_age_hours)
                result['comparisons'].append({'url':url,'before':before['snapshot_id'],'after':after['snapshot_id'],**comparison})
                for o in comparison['observations']:add(after,o,'capture_comparison')
                for error in comparison['gaps']:gap(url,error)
        attempts=[c for c in selected if c['representation']=='rendered_html']
        latest=max(attempts,key=lambda c:moment(c['captured_at'])) if attempts else None
        current=next((c for c in assessed if latest and c['snapshot_id']==latest['snapshot_id']),{'url':url,'ready':False,'extraction_complete':False,'checked_rules':[],'observations':[]})
        engine=assess_engine_evidence([r for r in engine_reports or [] if url_id(r['url'])==url],current,at=at,max_age_hours=max_age_hours)
        result['engine_results'].append({'url':url,**engine})
        for error in engine['gaps']:gap(url,error)
        for row in result['rows']:
            if row['url']==url and row['snapshot_id']==current.get('snapshot_id'):row['layers'].update(engine_eligibility=engine['engine_validation'],actual_display=engine['actual_display'])
    grouped={}
    for f in result['findings']:
        id=f['issue_id']
        if id not in grouped:grouped[id]=f
        else:
            for e in f['evidence']:
                if e not in grouped[id]['evidence']:grouped[id]['evidence'].append(e)
    result['findings']=list(grouped.values())
    return result
