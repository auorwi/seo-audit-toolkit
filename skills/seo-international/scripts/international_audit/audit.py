"""Compose international declaration, body, response and switch evidence."""
import hashlib,math,sys
from pathlib import Path
from .shared import site_host,require_url,url_id,moment,fresh
from .clusters import review_clusters
from .content import review_content,primary
from .switches import review_switch
root=Path(__file__).resolve().parents[3]/'seo-internal-links/scripts'
if not (root/'link_audit/targets.py').is_file():raise ImportError('Requires sibling seo-internal-links response evaluator')
if str(root) not in sys.path:sys.path.insert(0,str(root))
from link_audit.targets import assess_targets

def audit(inputs,*,at,max_age_hours=168):
    moment(at)
    if not math.isfinite(max_age_hours) or max_age_hours<=0:raise ValueError('invalid_freshness_window')
    maps={};ids={}
    for row in inputs['assets']:
        key=url_id(require_url(row['url']))
        if key in maps and maps[key]!=row:raise ValueError('conflicting_asset_mapping')
        maps[key]=row
    for c in inputs['captures']:
        key=c['snapshot_id']
        if key in ids and ids[key]!=c:raise ValueError('conflicting_snapshot_identity')
        ids[key]=c
    valid_assets=[a for a in inputs['assets'] if not a.get('mapped_at') or fresh(a['mapped_at'],at,max_age_hours)]
    mapping_gaps=[{'url':a['url'],'reason':'asset_mapping_not_fresh'} for a in inputs['assets'] if a not in valid_assets]
    clusters=review_clusters(inputs['captures'],valid_assets,at=at,max_age_hours=max_age_hours)
    content=review_content(inputs['captures'],inputs['body_reviews'],valid_assets,at=at,max_age_hours=max_age_hours)
    targets=assess_targets(inputs['http_records'],[d['target_url'] for d in clusters['edges']],at=at,max_age_hours=max_age_hours)
    observations=clusters['observations']+content['observations'];gaps=list(inputs['gaps'])+mapping_gaps+clusters['gaps']+content['gaps']+targets['gaps'];switches=[]
    for t in targets['targets']:
        if t['kind'] in {'broken_http_target','access_limited','server_error','redirect_loop_observed','http_response_review'}:rule='hreflang_target_http_problem'
        elif t['kind']=='redirected_link':rule='hreflang_target_redirect'
        else:continue
        observations.append({'url':t['requested_url'],'rule':rule,'classification':'response_observation','detail':t})
    target_map={t['requested_url']:t for t in targets['targets']}
    conflicting_body_urls={g['url'] for g in content['gaps'] if g['reason']=='body_review_variants_conflict'}
    body_map={r['url']:r for r in content['body_reviews'] if r['url'] not in conflicting_body_urls}
    for edge in clusters['edges']:
        if edge['locale_validation']['google_status']=='fallback':continue
        response=target_map.get(edge['target_url'],{});actual=edge['target_url']
        if response.get('kind')=='redirected_link':actual=response['final_url']
        review=body_map.get(actual)
        if not review:gaps.append({'url':edge['source_url'],'target_url':actual,'reason':'hreflang_target_body_unreviewed'});continue
        if primary(edge['locale'])!=primary(review['body_language']):observations.append({'url':edge['source_url'],'rule':'hreflang_body_language_mismatch','classification':'evidence_supported_review','detail':{'target_url':edge['target_url'],'final_url':actual,'declaration':edge,'body_review':review}})
    for action in inputs['switches']:
        before=ids.get(action.get('before_snapshot'));after=ids.get(action.get('after_snapshot'))
        if not before or not after:gaps.append({'reason':'switch_snapshot_missing','action':action});continue
        r=review_switch(before,after,action,inputs['body_reviews'],at=at,max_age_hours=max_age_hours);switches.append(r);observations+=r['observations'];gaps += [{'reason':g,'action':action} for g in r['gaps']]
    findings={}
    for o in observations:
        detail=o.get('detail',{});dimension=str(detail.get('locale') or detail.get('target_url') or detail.get('field') or detail.get('declaration',{}).get('path') or '')
        key=site_host()+'|010|'+o['rule']+'|'+url_id(o['url'])+'|'+dimension;identity='intl-'+hashlib.sha256(key.encode()).hexdigest()[:24]
        if identity not in findings:findings[identity]={'issue_id':identity,'url':o['url'],'owner_skill':'010','rule':o['rule'],'classification':o['classification'],'observed_at':at,'evidence':[],
            'recommendation':'按证据中的实体、语言和发布策略统一语言声明、页面正文、canonical与语言切换目标；先验证目标GET与内容等价，再修正模板。未发布的语言版本不补写假链接。',
            'retest':'以相同URL、入口、语言环境重取原始响应及业务就绪DOM，核对双向声明、正文引文与实体；保留未获取的渠道和未复现的历史。'}
        if o not in findings[identity]['evidence']:findings[identity]['evidence'].append(o)
    return {'schema_version':1,'configured_site':site_host(),'skill':'010','at':at,'scope':clusters['observed_urls'],'findings':list(findings.values()),'clusters':clusters,'content':content,'targets':targets['targets'],'switches':switches,'gaps':gaps,
        'coverage':{'full_site_proven':False,'observed_urls':len(clusters['observed_urls']),'declarations':len(clusters['declarations']),'body_reviews':len(content['body_reviews']),'switch_actions':len(switches)},
        'pending_reviews':['引擎实际采纳与收录未由页面声明证明。','正文语种/实体复核保留人工或模型判断来源；营销合规与文案地道程度交019。']}
