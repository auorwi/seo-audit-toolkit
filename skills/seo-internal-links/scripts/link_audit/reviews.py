"""Join observed links and target evidence into reviewable, stable issue records."""
import hashlib
from urllib.parse import urlsplit,urlunsplit,parse_qsl
from .shared import site_host,url_id,fresh
SOURCE='https://developers.google.com/search/docs/crawling-indexing/links-crawlable'
def review_links(captures,graph,target_results,*,at,max_age_hours=168,parameter_variant_hint=100,expected_parameters=None):
    if not isinstance(parameter_variant_hint,int) or isinstance(parameter_variant_hint,bool) or parameter_variant_hint<2:raise ValueError('invalid_parameter_hint')
    result={'findings':[],'orphan_candidates':sorted(u for u,n in graph['nodes'].items() if n['inventory_member'] and n['status']=='no_observed_inbound_candidate'),'pending_reviews':['anchor_context_relevance','locale_expectations','target_content_equivalence','graph_coverage']}
    findings={};by_target={}
    for edge in graph['edges']:by_target.setdefault(edge['target'],[]).append(edge)
    def emit(rule,url,*,identity='',occurrences=None,**kw):
        key=site_host()+'|009|'+rule+'|'+url_id(url)+'|'+identity;issue='links-'+hashlib.sha256(key.encode()).hexdigest()[:24]
        f=findings.setdefault(issue,{'issue_id':issue,'url':url_id(url),'rule':rule,'owner_skill':'009','observed_at':at,'classification':'review','source_url':SOURCE,'source_urls':[],
            'link_occurrences':[],'evidence':[],'recommendation':'检查原始来源节点、目标直达结果和模板上下文后修改；保留语义等价的真实href，不根据候选直接批量替换。','retest':'复测来源页初始HTML与稳定DOM、目标GET和进入路径，确认本轮图与直达证据。',**kw})
        for occurrence in occurrences or []:
            if occurrence not in f['link_occurrences']:f['link_occurrences'].append(occurrence)
        return f
    for target in target_results['targets']:
        url=target['requested_url'];edges=by_target.get(url,[])
        if not edges or target['kind'] not in {'broken_http_target','redirected_link','server_error','access_limited','redirect_loop_observed','http_response_review'}:continue
        f=emit(target['kind'],url,target_equivalence_required=target['kind']=='redirected_link',target_assessment=target,occurrences=[o for e in edges for o in e['occurrences']]);f['source_urls']=sorted(e['source'] for e in edges);f['evidence']=[target]
    selected=set(graph['selected_snapshots'])
    for c in captures:
        if c['snapshot_id'] not in selected or c.get('state','completed')!='completed' or not fresh(c.get('captured_at'),at,max_age_hours) or (c['representation']=='rendered_html' and c.get('readiness')!='ready'):continue
        url=url_id(c['url'])
        for link in c.get('links',[]):
            proof={'source_url':url,'snapshot_id':c['snapshot_id'],'document_sha256':c.get('document_sha256'),'captured_at':c['captured_at'],**link}
            identity=link.get('target') or link.get('href') or 'no-href'
            if link.get('http_link') and link.get('internal'):
                if link.get('seo_text_candidate')=='':emit('empty_anchor_text_candidate',url,identity=identity,accessible_name_failure_proven=False,occurrences=[proof])
                if 'nofollow' in link.get('rel',[]):emit('internal_nofollow_review',url,identity=identity,discovery_block_proven=False,occurrences=[proof])
            if link.get('kind') in {'missing_href','empty_href','invalid_href'} or (link.get('href') or '').strip().lower().startswith('javascript:'):
                emit('anchor_http_destination_missing',url,identity=identity,occurrences=[proof])
    for hint in graph['depth_hints']:emit('observed_depth_review',hint['url'],identity=hint['seed_group'],classification='review_hint',depth_evidence=hint)
    families={};expected=set(expected_parameters or [])
    for url in graph['nodes']:
        p=urlsplit(url);pairs=parse_qsl(p.query,keep_blank_values=True);unknown={k for k,v in pairs}-expected
        if not unknown:continue
        base=urlunsplit((p.scheme,p.netloc,p.path,'',''));families.setdefault((base,tuple(sorted(unknown))),set()).add(url)
    for (base,parameters),members in families.items():
        if len(members)>=parameter_variant_hint:emit('parameter_growth_review',base,identity='|'.join(parameters),parameters=list(parameters),variant_count=len(members),examples=sorted(members)[:5],infinite_trap_proven=False)
    result['findings']=list(findings.values());return result
