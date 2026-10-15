"""Select latest scoped evidence and cluster all eligible extracted metadata."""

import sys as _site_sys
from pathlib import Path as _SitePath
_site_dependency=_SitePath(__file__).resolve().parents[3]/'seo-crawlability/scripts'
if str(_site_dependency) not in _site_sys.path:_site_sys.path.insert(0,str(_site_dependency))
from crawlability.site import get_profile,site_host,site_origin,allowed_hosts,in_scope,require_url,brand_name,business_profile
import hashlib,json,math
from urllib.parse import urlsplit
from .shared import moment,fresh,url_id
from .context import normalized,validate_context
from .rules import audit_page
from .reviews import review_drafts

def audit(captures,urls,*,at,max_age_hours=168):
    moment(at)
    if not math.isfinite(max_age_hours) or max_age_hours<=0:raise ValueError('invalid_freshness_window')
    scope=list(dict.fromkeys(url_id(u) for u in urls))
    if not scope:raise ValueError('explicit_nonempty_url_scope_required')
    if any(not in_scope(u) for u in scope):raise ValueError('configured_site_scope_required')
    seen={}
    for c in captures:
        id=c['snapshot_id']
        if id in seen and c!=seen[id]:raise ValueError('conflicting_capture_identity')
        seen[id]=c
    result={'schema_version':1,'configured_site':site_host(),'skill':'007','at':at,'scope':scope,'rows':[],'findings':[],'handoffs':[],'gaps':[],
        'pending_reviews':[],'drafts':[],'withheld_drafts':[],'duplicate_clusters':[],'coverage':{'requested_urls':len(scope),'ready_pages':0,'source_only_pages':0,'cluster_eligible_pages':0,'full_site':False}}
    buckets={}
    for url in scope:
        cs=[c for c in seen.values() if url_id(c['url'])==url]
        rendered=[c for c in cs if c.get('representation')=='rendered_html']
        selected=max(rendered or cs,key=lambda c:moment(c['captured_at'])) if cs else None
        row={'url':url,'snapshot_id':selected.get('snapshot_id') if selected else None,'status':'evidence_gap'};result['rows'].append(row)
        if selected is None or selected.get('state','completed')!='completed':
            result['gaps'].append({'url':url,'reason':'latest_capture_failed_or_missing','state':selected.get('state') if selected else None});continue
        assessed=audit_page(selected,selected.get('context'),at=at,max_age_hours=max_age_hours)
        result['findings']+=assessed['findings'];result['handoffs']+=assessed['handoffs']
        result['gaps'] += [{'url':url,'reason':g} for g in assessed['gaps']]
        valid=fresh(selected.get('captured_at'),at,max_age_hours) and (selected['representation']=='initial_html' or selected.get('readiness')=='ready')
        row.update({'status':'observed' if valid else 'evidence_gap','representation':selected['representation'],'lengths':assessed['lengths'],'keywords_inventory':assessed['keywords_inventory'],'rewrite_blocked':assessed['rewrite_blocked']})
        if not valid:continue
        result['coverage']['ready_pages' if selected['representation']=='rendered_html' else 'source_only_pages']+=1
        review=review_drafts(selected,validate_context(selected,selected.get('context'),at=at,max_age_hours=max_age_hours),rewrite_blocked=assessed['rewrite_blocked'],at=at,max_age_hours=max_age_hours)
        result['drafts']+=review['drafts'];result['withheld_drafts']+=review['withheld'];result['gaps'] += [{'url':url,'reason':g} for g in review['gaps']]
        result['pending_reviews'].append({'url':url,'topics':sorted(set(assessed['pending_reviews']+review['pending']))})
        fields=selected['fields']
        if not fields.get('coverage',{}).get('closed_head'):continue
        result['coverage']['cluster_eligible_pages']+=1
        language=normalized(fields.get('html_lang')) or 'unknown'
        for field,key in [('title','titles'),('description','descriptions')]:
            for value in {normalized(n.get('value')) for n in fields.get(key,[]) if normalized(n.get('value'))}:
                buckets.setdefault((field,language,value),[]).append({'url':url,'snapshot_id':selected['snapshot_id'],'document_sha256':selected['document_sha256'],'original':[n.get('value') for n in fields[key] if normalized(n.get('value'))==value],'representation':selected['representation']})
    for (field,language,value),members in buckets.items():
        if len(members)>1:
            key=site_host()+'|007|duplicate|'+field+'|'+language+'|'+value
            result['duplicate_clusters'].append({'cluster_id':'tdk-cluster-'+hashlib.sha256(key.encode()).hexdigest()[:24],'field':field,'language':language,'normalized_value':value,'classification':'duplicate_candidate','members':members,
                'recommendation':'核实同模板不同实体是否应有区别；语言、参数和规范URL关系未确认前不删除或合并页面。'})
    for cluster in result['duplicate_clusters']:
        result['findings'].append({'issue_id':cluster['cluster_id'],'url':sorted(m['url'] for m in cluster['members'])[0],
            'rule':'duplicate_metadata_cluster','field':cluster['field'],'owner_skill':'007','observed_at':at,
            'classification':'duplicate_candidate','original':cluster['normalized_value'],'language':cluster['language'],
            'recommendation':cluster['recommendation'],'retest':'重新提取全部指定URL的对应元信息，并复核模板、语言及规范关系。',
            'evidence':{'members':cluster['members']}})
    grouped={}
    for f in result['findings']:
        id=f['issue_id']
        if id not in grouped:grouped[id]={**f,'evidence':[f['evidence']]}
        elif f['evidence'] not in grouped[id]['evidence']:grouped[id]['evidence'].append(f['evidence'])
    result['findings']=list(grouped.values())
    return result
