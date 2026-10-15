"""Preserve CrUX/PSI scopes and units; absent data never becomes a healthy zero."""
import math
from datetime import date
from .metrics import assess_field
from .shared import url_id,origin,moment
CRUX={'LCP':'largest_contentful_paint','INP':'interaction_to_next_paint','CLS':'cumulative_layout_shift','FCP':'first_contentful_paint','TTFB':'experimental_time_to_first_byte'}
PSI={'LCP':'LARGEST_CONTENTFUL_PAINT_MS','INP':'INTERACTION_TO_NEXT_PAINT','CLS':'CUMULATIVE_LAYOUT_SHIFT_SCORE','FCP':'FIRST_CONTENTFUL_PAINT_MS','TTFB':'EXPERIMENTAL_TIME_TO_FIRST_BYTE'}

def number(value):
    if isinstance(value,bool) or value is None:return None
    try:n=float(value)
    except (TypeError,ValueError):return None
    return n if math.isfinite(n) and n>=0 else None

def period(value):
    if not isinstance(value,dict):return None
    try:
        start=value['firstDate'];end=value['lastDate'];first=date(start['year'],start['month'],start['day']);last=date(end['year'],end['month'],end['day'])
        if first>last:return None
        return {'first_date':first.isoformat(),'last_date':last.isoformat(),'days':(last-first).days+1,'meaning':'aggregation window; not proof of continuous samples for every day'}
    except (KeyError,TypeError,ValueError):return None

def failure(payload,source,observed_at):
    e=payload.get('error',{});return {'source':source,'observed_at':observed_at,'status':'no_data' if e.get('code')==404 else 'api_error','error':e,'metrics':{},'gaps':['field_data_unavailable']}

def parse_crux(payload,request,*,observed_at):
    moment(observed_at)
    if payload.get('error'):
        scope='url' if request.get('url') else 'origin'
        return {**failure(payload,'crux_api',observed_at),'scope':scope,'key':request.get(scope),'device':request.get('formFactor','ALL')}
    record=payload.get('record')
    if not isinstance(record,dict):return {'source':'crux_api','observed_at':observed_at,'status':'unverified','metrics':{},'gaps':['record_missing']}
    key=record.get('key',{});scope='url' if key.get('url') else 'origin';value=key.get(scope);requested=request.get(scope);gaps=[];status='observed'
    try:
        actual=url_id(value) if scope=='url' else origin(value);expected=url_id(requested) if scope=='url' else origin(requested)
        normalized=payload.get('urlNormalizationDetails',{})
        if actual!=expected and not (scope=='url' and normalized.get('originalUrl')==request.get('url') and normalized.get('normalizedUrl')==value):gaps.append('response_key_mismatch');status='unverified'
    except (ValueError,TypeError):actual=value;gaps.append('response_key_mismatch');status='unverified'
    device=key.get('formFactor','ALL')
    if device!=request.get('formFactor','ALL'):gaps.append('response_device_mismatch');status='unverified'
    window=period(record.get('collectionPeriod'))
    if not window:gaps.append('collection_period_missing')
    metrics={};raw=record.get('metrics',{})
    for name,api in CRUX.items():
        item=raw.get(api,{}) if isinstance(raw,dict) else {};value=item.get('percentiles',{}).get('p75') if isinstance(item,dict) else None;metrics[name]=number(value)
        if metrics[name] is None:gaps.append(name+'_p75_unavailable')
    return {'source':'crux_api','observed_at':observed_at,'status':status,'scope':scope,'key':actual,'requested_key':{k:request[k] for k in ['url','origin','formFactor'] if k in request},'device':device,'collection_period':window,'metrics':metrics,'assessment':assess_field(metrics),'normalization':payload.get('urlNormalizationDetails'),'gaps':gaps}

def parse_psi(payload,request,*,observed_at):
    moment(observed_at)
    if payload.get('error'):return {**failure(payload,'psi_api',observed_at),'records':[],'scope':'url','key':request.get('url'),'device':{'mobile':'PHONE','desktop':'DESKTOP'}.get(request.get('strategy'),'UNKNOWN')}
    result={'source':'psi_api','observed_at':observed_at,'status':'observed','records':[],'gaps':[]}
    for source_key,scope in [('loadingExperience','url'),('originLoadingExperience','origin')]:
        raw=payload.get(source_key,{})
        if not raw or not raw.get('metrics'):
            result['gaps'].append(scope+'_field_data_unavailable');continue
        key=raw.get('id');gaps=[];status='observed'
        try:
            actual=url_id(key) if scope=='url' else origin(key);expected=url_id(request['url']) if scope=='url' else origin(request['url'])
            if actual!=expected:status='unverified';gaps.append('response_key_mismatch')
        except (ValueError,KeyError,TypeError):actual=key;status='unverified';gaps.append('response_key_mismatch')
        metrics={}
        for name,api in PSI.items():
            item=raw['metrics'].get(api,{});value=number(item.get('percentile'))
            if name=='CLS' and value is not None:
                bounds=[x.get('max') for x in item.get('distributions',[]) if isinstance(x,dict) and 'max' in x]
                if bounds[:2]==[10,25]:value/=100
                else:value=None;gaps.append('psi_cls_scale_unverified')
            metrics[name]=value
            if value is None:gaps.append(name+'_p75_unavailable')
        window=period(raw.get('collectionPeriod'))
        if not window:gaps.append('collection_period_missing')
        strategy=request.get('strategy');device={'mobile':'PHONE','desktop':'DESKTOP'}.get(strategy,'UNKNOWN')
        if device=='UNKNOWN':gaps.append('device_unverified');status='unverified'
        result['records'].append({'source':'psi_api','source_section':source_key,'observed_at':observed_at,'status':status,'scope':scope,'key':actual,'device':device,'collection_period':window,'metrics':metrics,'assessment':assess_field(metrics,policy='psi'),'reported_category':raw.get('overall_category'),'gaps':gaps})
    if not result['records']:result['status']='no_data'
    return result
