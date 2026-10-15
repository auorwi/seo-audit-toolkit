"""Purpose-aware rules. Caller must bind human/agent review to exact captured evidence."""
PURPOSES={'informative','decorative','functional','watch_video','auxiliary_video','nonvideo_embed','unknown'}
def review_media(row,*,review=None):
    out={'findings':[],'referrals':[],'gaps':[],'video_indexed_verified':False,'playback_verified':False}
    def finding(rule,classification,recommendation,retest):
        out['findings'].append({'rule':rule,'classification':classification,'recommendation':recommendation,'retest':retest})
    def refer(owner,rule):out['referrals'].append({'owner':owner,'rule':rule,'slot':row.get('slot')})
    tag=row.get('tag');purpose=(review or {}).get('purpose','unknown')
    if purpose not in PURPOSES:out['gaps'].append('invalid_purpose');purpose='unknown'
    if purpose=='unknown':out['gaps'].append('purpose_unreviewed')
    if tag=='img':
        if purpose=='functional':refer('006','functional_image_accessible_name_context')
        elif purpose in {'informative','decorative'}:
            if not row.get('alt_present'):refer('006','image_alt_attribute_missing')
            elif purpose=='informative' and not (row.get('alt') or '').strip():refer('006','information_image_alt_empty')
        if (review or {}).get('important_initial') is True and row.get('visible') is True and row.get('in_viewport') is True and row.get('loading')=='lazy':
            refer('011','initial_important_image_lazy_loading_risk')
    if tag=='css' and purpose=='informative' and row.get('background_urls'):
        equivalent=(review or {}).get('equivalent_img')
        intent=(review or {}).get('image_search_target')
        if equivalent is False and intent is True:
            finding('essential_css_image_no_img_equivalent','confirmed',
                    '将需被图片搜索发现的主要信息图提供为可抓取 img/picture；保留布局与视觉等价内容，避免仅 CSS 背景承载。',
                    '同 URL 与设备重新检查实际 DOM、可见内容和图片 GET/解码；不以修改后的声明推断已被图片搜索收录。')
        elif equivalent not in {True,False}:out['gaps'].append('css_equivalent_img_unreviewed')
        if equivalent is not True and intent not in {True,False}:out['gaps'].append('css_image_search_intent_unreviewed')
    if tag=='css' and purpose=='functional':refer('006','functional_css_icon_accessible_name_context')
    if tag=='iframe' and not (row.get('title') or '').strip():refer('006','iframe_accessible_name_context')
    if tag=='video' and row.get('error_code')==1:out['gaps'].append('video_load_aborted')
    if tag=='video' and row.get('error_code') in {2,3,4}:
        finding('browser_video_error','confirmed',
                '依据同次浏览器 error_code、当前资源和网络响应排查加载、解码或格式支持；保留设备环境，勿将单环境失败泛化。',
                '在同设备重新采集错误与资源响应；播放成功需另有实际播放证据，元数据就绪不等于播放成功。')
    if purpose=='watch_video' and tag in {'video','iframe','embed','object'}:
        thumb=(review or {}).get('representative_thumbnail')
        if thumb is False:
            finding('video_thumbnail_unavailable','candidate',
                    '为以视频为主的观看页提供稳定、可访问且代表视频的缩略图，并关联 008 的 VideoObject 核验；先确认是否已有引擎可发现的缩略图。',
                    '核验缩略图实际响应、内容与视频对应关系，再以站长平台的视频索引数据复核；不要求辅助教程变成观看页。')
        elif thumb is not True:out['gaps'].append('thumbnail_fitness_unreviewed')
        refer('008','watch_video_structured_data_crosscheck')
    return out
