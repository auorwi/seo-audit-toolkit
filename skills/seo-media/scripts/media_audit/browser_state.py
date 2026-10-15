"""Classify a browser observation without turning HTMLImageElement.complete into proof."""
import math
from .shared import moment,fresh

def review_image(row,*,at,max_age_hours=24):
    moment(at)
    result={'status':'invalid_observation','selected_url':row.get('current_src'),
            'decode_verified':False,'encoded_pixel_width':None,
            'natural_width_css_pixels':row.get('natural_width')}
    def done(status):return {**result,'status':status}
    if not fresh(row.get('captured_at'),at,max_age_hours):return done('stale_observation')
    for key in ('natural_width','natural_height'):
        v=row.get(key)
        if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or v<0:return done('invalid_observation')
    if type(row.get('complete')) is not bool or not isinstance(row.get('current_src'),str):return done('invalid_observation')
    src=row['current_src']
    if not row['complete']:
        return done('lazy_deferred' if row.get('loading')=='lazy' and row.get('in_viewport') is False else 'loading')
    if not src:return done('no_selected_resource')
    decode=row.get('decode') or {}
    if not isinstance(decode,dict):return done('invalid_observation')
    state=decode.get('result','not_attempted')
    if state not in {'not_attempted','fulfilled','rejected','timeout'}:return done('invalid_observation')
    if state!='not_attempted' and decode.get('current_src')!=src:return done('decode_source_mismatch')
    if state=='fulfilled':
        result['decode_verified']=True
        return done('decoded')
    if row['natural_width']==0 and row['natural_height']==0 and row.get('error_event_src')==src:
        return done('browser_image_failure')
    if state in {'rejected','timeout'}:return done('decode_'+state)
    if row['natural_width']>0 and row['natural_height']>0:return done('loaded_dimensions_observed')
    return done('zero_dimensions_unresolved')
