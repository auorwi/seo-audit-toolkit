"""Metadata observations and explicit fact comparisons, not ranking predictions."""

import sys as _site_sys
from pathlib import Path as _SitePath
_site_dependency=_SitePath(__file__).resolve().parents[3]/'seo-crawlability/scripts'
if str(_site_dependency) not in _site_sys.path:_site_sys.path.insert(0,str(_site_dependency))
from crawlability.site import get_profile,site_host,site_origin,allowed_hosts,in_scope,require_url,brand_name,business_profile
import hashlib,re
from .shared import fresh,url_id
from .context import validate_context,normalized,contains

def audit_page(capture,context,*,at,max_age_hours=168):
    url=url_id(capture['url'])
    result={'url':url,'findings':[],'handoffs':[],'gaps':[],'pending_reviews':['search_intent','language_and_wording'],
            'rewrite_blocked':False,'facts':{},'lengths':{},'keywords_inventory':[]}
    if not fresh(capture.get('captured_at'),at,max_age_hours):result['gaps'].append('capture_not_current');return result
    rendered=capture.get('representation')=='rendered_html'
    if rendered and capture.get('readiness')!='ready':result['gaps'].append('rendered_page_not_ready');return result
    if not rendered:result['gaps'].append('current_rendered_metadata_not_observed')
    fields=capture['fields'];result['keywords_inventory']=fields.get('keywords',[])
    validated=validate_context(capture,context,at=at,max_age_hours=max_age_hours)
    result['facts']=validated['facts'];result['gaps']+=validated['gaps'];meta=validated['metadata'];facts=validated['facts']
    def finding(rule,field,classification='metadata_observation',recommendation=None,evidence=None):
        key=site_host()+'|007|'+url+'|'+rule+'|'+field
        result['findings'].append({'issue_id':'tdk-'+hashlib.sha256(key.encode()).hexdigest()[:24],'url':url,'rule':rule,'field':field,'owner_skill':'007','observed_at':at,
            'classification':classification if rendered else 'initial_html_observation','template':meta.get('template'),'language':meta.get('language'),
            'original':fields.get({'title':'titles','description':'descriptions'}.get(field,field)),
            'recommendation':recommendation or '核对当前页面内容与模板字段，补齐准确元信息后复测；不据此推断实际收录或排名。',
            'retest':'同一URL、语言和进入方式重新采集就绪DOM，核对原始与渲染元信息及实际主体。',
            'evidence':{'snapshot_id':capture['snapshot_id'],'document_sha256':capture['document_sha256'],'captured_at':capture['captured_at'],'source':capture['source'],'detail':evidence}})
    def handoff(rule,owners,evidence):
        result['rewrite_blocked']=True
        for owner in owners:result['handoffs'].append({'owner_skill':owner,'url':url,'rule':rule,'evidence':evidence,'recommendation':'先核验路由与实际内容/产品状态，不能只改标题隐藏错配。'})
    coverage=fields.get('coverage',{})
    if not coverage.get('head_seen') or not coverage.get('closed_head'):result['gaps'].append('metadata_head_not_complete')
    else:
        for field,key in [('title','titles'),('description','descriptions')]:
            nodes=fields.get(key,[]);values=[normalized(n.get('value')) for n in nodes]
            result['lengths'][field]=[len(n.get('value') or '') for n in nodes]
            if not nodes:finding('missing_'+field,field)
            if nodes and any(not v for v in values):finding('empty_'+field,field)
            if len(nodes)>1:finding('duplicate_'+field+'_nodes',field,evidence=nodes)
            for n in nodes:
                value=n.get('value') or ''
                if re.search(r'\{\{[^{}]+\}\}|\$\{[^{}]+\}|%s|(?<!\w)(?:undefined|null)(?!\w)',value,re.I):finding('unexpanded_placeholder',field,evidence=n);break
            keys=meta.get('translation_keys',[])
            if any(v in {normalized(x) for x in keys} for v in values if v):finding('translation_key',field,evidence=nodes)
            if meta.get('template') in {'buy_crypto','buy_crypto_country'} and any(re.search(r'\bin\s*(?:[|.,!?]|$)',n.get('value') or '',re.I) for n in nodes):finding('empty_country_slot',field,'template_review',evidence=nodes)
            if any(len(n.get('value') or '')>(80 if field=='title' else 220) for n in nodes):finding(field+'_length_review',field,'display_advisory','长度仅供显示与简洁性复核；并非搜索引擎硬性字数限制，需结合设备、语言和主题判断。')
        if any(re.fullmatch(r'[\s|:—–-]*'+re.escape(brand_name())+r'[\s|:—–-]*',n.get('value') or '',re.I) for n in fields.get('titles',[])):finding('half_empty_title','title','template_review')
    by_role={}
    for fact in facts.values():by_role.setdefault(fact['role'],[]).append(fact)
    def terms(fact):return {normalized(x) for x in [fact['value']]+fact.get('aliases',[])}
    for route_role,page_role in [('route_entity','page_entity'),('route_product','page_product')]:
        route=by_role.get(route_role,[]);page=by_role.get(page_role,[])
        if len(route)==1 and len(page)==1 and not terms(route[0])&terms(page[0]):
            handoff('route_content_mismatch',['004','012'],{'route':route[0],'page':page[0]})
        elif len(route)>1 or len(page)>1:result['gaps'].append('ambiguous_'+route_role+'_facts')
    all_metadata=' '.join(n.get('value') or '' for k in ['titles','descriptions'] for n in fields.get(k,[]))
    trading_claim=bool(re.search(r'\b(?:buy|trade|trading)\b',all_metadata,re.I))
    statuses=by_role.get('listing_status',[])
    if trading_claim:
        if len(statuses)==1 and statuses[0]['value'] in {'not_listed','delisted'}:
            finding('availability_claim_conflict','metadata','content_review','先按资产、产品、地区和时间核实可用状态；不要先改成另一条交易承诺。',statuses[0])
            handoff('availability_claim_conflict',['012'],statuses[0])
        elif len(statuses)!=1 or statuses[0]['value']=='unknown':result['pending_reviews'].append('product_availability')
    if not result['rewrite_blocked']:
        for requirement in meta.get('requirements',[]):
            field=requirement.get('field');fact=facts.get(requirement.get('fact_id'))
            if field not in {'title','description'} or fact is None:result['gaps'].append('required_fact_unavailable');continue
            nodes=fields.get('titles' if field=='title' else 'descriptions',[])
            if nodes and not any(contains(n.get('value'),term) for n in nodes for term in terms(fact)):
                finding('required_fact_missing',field,'template_review','在确认该字段适用于此模板后，补充已核实的实体或地区；不得猜测。',fact)
        dynamic=meta.get('dynamic_title',{})
        if dynamic.get('enabled'):
            for id in dynamic.get('stable_fact_ids',[]):
                fact=facts.get(id)
                if not fact:result['gaps'].append('dynamic_stable_fact_unavailable');continue
                if not any(contains(n.get('value'),term) for n in fields.get('titles',[]) for term in terms(fact)):
                    finding('dynamic_stable_field_missing','title','template_review','动态数值可变化，实体、交易对与产品等稳定字段必须与页面一致。',fact)
    return result
