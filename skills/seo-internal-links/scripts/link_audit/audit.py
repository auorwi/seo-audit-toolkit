"""Compose independent link, target, pagination and explicit-language evidence."""
import hashlib
from .shared import site_host,require_url,url_id
from .graph import build_graph
from .targets import assess_targets
from .reviews import review_links
from .pagination import review_pagination
from .language import review_language

def audit(inputs,*,at,max_age_hours=168,depth_hint=4,parameter_variant_hint=100,expected_parameters=None):
    assets={}
    for asset in inputs['assets']:
        item={'url':asset} if isinstance(asset,str) else asset;url=url_id(require_url(item['url']))
        if url in assets and assets[url]!=item:raise ValueError('conflicting_asset_metadata')
        assets[url]=item
    cs=inputs['captures'];graph=build_graph(cs,list(assets.values()),inputs['seeds'],at=at,max_age_hours=max_age_hours,depth_hint=depth_hint)
    targets=assess_targets(inputs.get('http_records',[]),list(graph['nodes']),at=at,max_age_hours=max_age_hours)
    reviews=review_links(cs,graph,targets,at=at,max_age_hours=max_age_hours,parameter_variant_hint=parameter_variant_hint,expected_parameters=expected_parameters)
    result={'schema_version':1,'configured_site':site_host(),'skill':'009','at':at,'scope':list(assets),'assets':list(assets.values()),'seeds':inputs['seeds'],'graph':graph,'targets':targets['targets'],**reviews,
        'gaps':list(inputs.get('gaps',[]))+graph['gaps']+targets['gaps'],'pagination':[],'language':None,'coverage':{**graph['coverage'],'target_get_observations':sum(bool(t['chain']) for t in targets['targets'])}}
    def finding(observation,url,identity):
        key=site_host()+'|009|'+observation['rule']+'|'+url_id(url)+'|'+identity
        result['findings'].append({'issue_id':'links-'+hashlib.sha256(key.encode()).hexdigest()[:24],'url':url_id(url),'owner_skill':'009','observed_at':at,'source_urls':[url_id(url)],'link_occurrences':[],
            'recommendation':'依据实际href、点击状态、直达内容或明确语言对应关系修正模板；先确定实体与语言等价，不盲目改所有链接。','retest':'重复同一控件操作及声明href的独立直达，保存快照、条目身份和目标响应。','evidence':[observation],**{k:v for k,v in observation.items() if k!='evidence'}})
    ids={c['snapshot_id']:c for c in cs}
    for request in inputs.get('pagination',[]):
        before=ids.get(request.get('before'));after=ids.get(request.get('after'));direct=ids.get(request.get('direct'))
        if before is None or after is None:result['gaps'].append({'reason':'pagination_snapshot_missing','request':request});continue
        p=review_pagination(before,after,request['action'],direct=direct,at=at,max_age_hours=max_age_hours);result['pagination'].append({'before':before['snapshot_id'],'after':after['snapshot_id'],**p})
        result['gaps'] += [{'url':before['url'],'reason':g} for g in p['gaps']]
        for o in p['observations']:finding(o,before['url'],request['action'].get('selector',''))
    language=review_language(cs,inputs.get('language_expectations',[]),at=at,max_age_hours=max_age_hours,target_assessments=targets['targets']);result['language']=language;result['gaps']+=language['gaps']
    for o in language['observations']:finding(o,o['url'],o['target_url'])
    unique={}
    for f in result['findings']:
        if f['issue_id'] not in unique:unique[f['issue_id']]=f
        else:
            for proof in f['evidence']:
                if proof not in unique[f['issue_id']]['evidence']:unique[f['issue_id']]['evidence'].append(proof)
    result['findings']=list(unique.values());return result
