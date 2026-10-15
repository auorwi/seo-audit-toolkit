"""Normalize raw LHR without confusing scores, lab metrics or field INP."""
import hashlib,json
from .field import number
from .shared import url_id,moment
AUDITS={'LCP':('largest-contentful-paint','millisecond'),'CLS':('cumulative-layout-shift','unitless'),'TBT':('total-blocking-time','millisecond'),'FCP':('first-contentful-paint','millisecond'),'SI':('speed-index','millisecond'),'TTFB':('server-response-time','millisecond')}

def parse_lhr(lhr,context):
    gaps=[];metrics={'INP':None};audits=lhr.get('audits',{});settings=lhr.get('configSettings',{});env=lhr.get('environment',{})
    requested=url_id(lhr['requestedUrl']);final=url_id(lhr.get('finalDisplayedUrl') or lhr.get('finalUrl') or requested);moment(lhr['fetchTime'])
    for metric,(key,unit) in AUDITS.items():
        a=audits.get(key,{});value=number(a.get('numericValue'))
        if a.get('numericUnit')!=unit or a.get('scoreDisplayMode') in {'error','notApplicable','manual'}:value=None
        metrics[metric]=value
        if value is None:gaps.append(metric+'_lab_unavailable')
    runtime=lhr.get('runtimeError');valid=not runtime and metrics['LCP'] is not None and metrics['CLS'] is not None
    expected=requested
    if context.get('expected_final_url') and context.get('final_url_basis'):expected=url_id(context['expected_final_url'])
    if final!=expected:gaps.append('unexpected_final_url');valid=False
    document_responses=[item for item in audits.get('network-requests',{}).get('details',{}).get('items',[]) if item.get('resourceType')=='Document' and item.get('url')==final]
    if any(type(item.get('statusCode')) is int and item['statusCode']>=400 for item in document_responses):gaps.append('document_http_error');valid=False
    if not document_responses:gaps.append('document_http_status_unobserved')
    fingerprint={'lighthouse_version':lhr.get('lighthouseVersion'),'host_user_agent':env.get('hostUserAgent'),'network_user_agent':env.get('networkUserAgent'),
        'settings':{k:settings.get(k) for k in ['formFactor','screenEmulation','throttlingMethod','throttling','locale','emulatedUserAgent','disableStorageReset','maxWaitForLoad','maxWaitForFcp','pauseAfterFcpMs','pauseAfterLoadMs','onlyCategories']},
        'context':{k:context.get(k) for k in ['runner','host_id','network_location','entry_mode','login','cache_mode','cpu_model','network_profile']}}
    comparable=all(context.get(k) for k in ['runner','host_id','network_location','entry_mode','login']) and bool(lhr.get('lighthouseVersion')) and bool(env.get('hostUserAgent')) and settings.get('formFactor') in {'mobile','desktop'} and bool(settings.get('throttlingMethod'))
    if not comparable:gaps.append('measurement_environment_incomplete')
    return {'source':'lighthouse','requested_url':requested,'final_url':final,'fetched_at':lhr['fetchTime'],'device':settings.get('formFactor'),'metrics':metrics,'performance_score':lhr.get('categories',{}).get('performance',{}).get('score'),
        'field_assessment':'not_available_from_lighthouse','valid_measurement':bool(valid),'comparable':bool(comparable),'environment':fingerprint,'environment_key':hashlib.sha256(json.dumps(fingerprint,sort_keys=True,separators=(',',':')).encode()).hexdigest(),
        'benchmark_index':env.get('benchmarkIndex'),'warnings':lhr.get('runWarnings',[]),'runtime_error':runtime,'document_responses':document_responses,'page_content_validity':'unverified_by_metrics','gaps':gaps}
