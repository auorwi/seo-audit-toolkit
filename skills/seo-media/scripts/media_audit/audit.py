"""Combine current, scoped media observations; preserve uncertainty and issue history."""
import base64,hashlib
from .shared import site_host,require_url,moment,fresh,url_id
from .browser_state import review_image
from .resources import review_resource
from .rules import review_media

def audit(inputs,*,at,max_age_hours=24):
    moment(at);fresh(at,at,max_age_hours)
    for row in inputs['scope']:require_url(row['url'])
    required={(url_id(s['url']),d) for s in inputs['scope'] for d in s['devices']}
    findings={};checks=[];declarations=[];gaps=list(inputs.get('gaps',[]));referrals=[];performed=set();accepted=0
    def add(c,row,rule,classification,detail,recommendation=None,retest=None):
        family='image_availability' if row['tag']=='img' and rule in {'browser_image_failure','decode_rejected','media_resource_not_found','html_instead_of_media','empty_resource_body'} else rule
        identity='media-'+hashlib.sha256((site_host()+'|013|'+url_id(c['url'])+'|'+row['slot']+'|'+family).encode()).hexdigest()[:24]
        e={'snapshot_id':c['snapshot_id'],'device':c['device'],'phase':c.get('phase'),'slot':row['slot'],'resource':row.get('current_src') or row.get('src'),
           'captured_at':c['captured_at'],'rule':rule,'detail':detail}
        if identity not in findings:
            findings[identity]={'issue_id':identity,'owner_skill':'013','url':url_id(c['url']),'slot':row['slot'],'rule':rule,'classification':classification,
                'recommendation':recommendation or '依据本次设备、当前资源、实际响应与解码状态排查媒体路径、发布文件、类型与访问控制；先复现，再确定修复位置。',
                'retest':retest or '同 URL、设备、视口与阶段重新采集当前资源、真实响应和解码；保留修复前后证据，未出现不自动关闭。','evidence':[]}
        findings[identity]['evidence'].append(e)
        if classification=='confirmed':findings[identity].update(classification='confirmed',rule=rule)
    for c in inputs['captures']:
        try:
            key=(url_id(c['requested_url']),c['device']);actual=url_id(c['url'])
            if key not in required:raise ValueError('capture_out_of_scope')
            if actual!=key[0]:raise ValueError('unexpected_landing_url')
            if c['readiness']!='ready':raise ValueError('page_not_ready')
            if not fresh(c['captured_at'],at,max_age_hours):raise ValueError('stale_capture')
        except (ValueError,KeyError,TypeError) as e:gaps.append({'snapshot_id':c.get('snapshot_id'),'reason':str(e)});continue
        performed.add(key);accepted+=1
        for g in c.get('gaps',[]):gaps.append({'snapshot_id':c['snapshot_id'],'reason':g})
        declaration=c.get('declarations',{})
        selected={r.get('current_src') for r in c.get('media',[]) if isinstance(r,dict) and r.get('current_src')}
        declared={r['url'] for r in declaration.get('resource_refs',[]) if r.get('url')}
        declarations.append({'snapshot_id':c['snapshot_id'],'device':c['device'],'url':actual,'declared_resource_urls':sorted(declared),
                             'unselected_resource_urls':sorted(declared-selected),'gaps':declaration.get('gaps',[]),
                             'unselected_means_not_in_currentSrc_not_necessarily_unused':True})
        for g in declaration.get('gaps',[]):gaps.append({'snapshot_id':c['snapshot_id'],'reason':'declaration_validation_gap','detail':g})
        for row in c.get('media',[]):
            if not isinstance(row,dict) or not row.get('slot') or row.get('tag') not in {'img','video','iframe','embed','object','css'}:
                gaps.append({'snapshot_id':c['snapshot_id'],'reason':'invalid_media_row'});continue
            context={'snapshot_id':c['snapshot_id'],'url':actual,'device':c['device'],'slot':row['slot']}
            purpose=inputs.get('reviews',{}).get(c['snapshot_id'],{}).get(row['slot'])
            result=review_media(row,review=purpose);check={**context,'purpose':purpose,'rules':result,'resources':[]}
            for g in result['gaps']:gaps.append({**context,'reason':g})
            for r in result['referrals']:referrals.append({**context,**r})
            for f in result['findings']:add(c,row,f['rule'],f['classification'],{'review':purpose,'observation':row},f['recommendation'],f['retest'])
            browser=None
            if row['tag']=='img':
                browser=review_image(row,at=at,max_age_hours=max_age_hours);check['browser']=browser
                state=browser['status']
                if state in {'browser_image_failure','decode_rejected'}:add(c,row,state,'confirmed' if state=='browser_image_failure' else 'candidate',{'browser':browser,'observation':row})
                elif state not in {'decoded','loaded_dimensions_observed'}:gaps.append({**context,'reason':state})
            targets=[]
            if row['tag']=='img' and row.get('current_src'):targets=[(row['current_src'],'image')]
            elif row['tag']=='css':targets=[(u,'image') for u in row.get('background_urls',[])]
            elif row['tag']=='video':
                if row.get('current_src'):targets.append((row['current_src'],'video'))
                if row.get('poster'):targets.append((row['poster'],'image'))
            elif row.get('src'):targets=[(row['src'],'embed_document')]
            for target,kind in targets:
                responses=[r for r in c.get('responses',[]) if r.get('url')==target]
                if not responses and not (browser and browser['status'] in {'decoded','loaded_dimensions_observed'}):gaps.append({**context,'resource':target,'reason':'resource_response_unobserved'})
                for raw in responses:
                    try:
                        response=dict(raw);encoded=response.pop('body_prefix_base64',None)
                        if encoded is not None:response['body_prefix']=base64.b64decode(encoded,validate=True)
                        r=review_resource(response,expected_kind=kind,at=at,max_age_hours=max_age_hours)
                    except (ValueError,KeyError,TypeError) as e:gaps.append({**context,'reason':'invalid_response','detail':str(e)});continue
                    check['resources'].append({'url':target,'kind':kind,'source':raw.get('source'),'result':r})
                    state=r['status']
                    if state in {'resource_not_found','html_instead_of_media','empty_resource_body','mime_signature_mismatch','unexpected_resource_type','server_error'}:
                        if browser and browser['status'] in {'decoded','loaded_dimensions_observed'} and state in {'resource_not_found','html_instead_of_media','empty_resource_body','server_error'}:
                            gaps.append({**context,'resource':target,'reason':'response_browser_disagreement','response_status':state});continue
                        add(c,row,'media_resource_not_found' if state=='resource_not_found' else state,'confirmed' if raw.get('source')=='actual browser response' else 'candidate',{'response':{k:v for k,v in raw.items() if k!='body_prefix_base64'},'review':r})
                    elif state not in {'image_response_observed','image_response_generic_mime','image_response_mime_alias','video_response_observed','video_playlist_observed','embed_response_observed'}:
                        if state=='body_unobserved' and browser and browser['decode_verified']:continue
                        gaps.append({**context,'resource':target,'reason':state})
            checks.append(check)
    for url,device in sorted(required-performed):gaps.append({'url':url,'device':device,'reason':'declared_variant_not_captured'})
    return {'schema_version':1,'configured_site':site_host(),'skill':'013','at':at,'scope':inputs['scope'],'findings':list(findings.values()),'checks':checks,'declaration_checks':declarations,'referrals':referrals,'gaps':gaps,
            'coverage':{'declared_variants':len(required),'captured_declared_variants':len(required&performed),'accepted_captures':accepted,'observed_media_checks':len(checks),
              'declared_checks_complete':bool(required) and required<=performed and not gaps,'all_declared_resources_verified':False,'full_site_proven':False,
              'video_playback_verified':False,'video_indexing_verified':False,'cwv_verified':False},
            'limitations':['当前资源以实际 currentSrc 为准；未选中的 srcset 候选和未触发的懒加载不声称已验证。',
             '自然尺寸是密度校正后的 CSS 像素，不推断编码像素、传输浪费或 CLS。',
             '媒体用途依赖具名证据复核；自动检查不证明图片搜索或视频索引结果。',
             '问题按 URL、媒体槽位与规则族稳定去重；DOM 槽位重排可能需人工归并，本轮缺席不自动关闭。']}
