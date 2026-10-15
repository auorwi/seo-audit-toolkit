"""HTTP evidence chains, with engine-specific robots error semantics."""
from urllib.parse import urljoin
from .common import moment,fresh,header_pairs,url_id,origin
from .robots import evaluate_rules

def latest_records(records):
    result={}
    for row in records:
        url=url_id(row['url']);moment(row['checked_at'])
        if url not in result or moment(row['checked_at'])>=moment(result[url]['checked_at']):result[url]=row
    return result

def trace(records,start,at,max_age_hours=168,max_redirects=5):
    if not isinstance(max_redirects,int) or max_redirects<0:raise ValueError('invalid_redirect_limit')
    latest=latest_records(records);url=url_id(start);chain=[];seen=set()
    result={'chain':chain,'final_url':url,'record':None,'reason':'complete'}
    for hop in range(max_redirects+1):
        result['final_url']=url
        if url in seen:result['reason']='redirect_loop';return result
        seen.add(url);row=latest.get(url)
        if row is None:result['reason']='redirect_missing_evidence' if chain else 'missing_evidence';return result
        chain.append({k:row[k] for k in ('url','status','checked_at','error','evidence','environment','request_id','capture_id') if k in row})
        if not fresh(row.get('checked_at'),at,max_age_hours):result['reason']='stale';return result
        if row.get('error') or row.get('status') is None:result['reason']='request_unverified';return result
        result['record']=row
        if row['status'] not in {301,302,303,307,308}:return result
        locations=list(dict.fromkeys(v for k,v in header_pairs(row.get('headers',[])) if k=='location'))
        if len(locations)!=1 or not locations[0]:result['reason']='redirect_location_ambiguous';return result
        if hop==max_redirects:result['reason']='redirect_limit';return result
        try:url=url_id(urljoin(url,locations[0]))
        except (ValueError,UnicodeError):result['reason']='redirect_target_invalid';return result
    return result

def evaluate_response(records,target,agent,at,max_age_hours=168,max_redirects=5):
    root=origin(target)+'/robots.txt'
    walked=trace(records,root,at,max_age_hours,max_redirects)
    result={k:v for k,v in walked.items() if k!='record'}
    result.update({'allowed':None,'agent':agent,'robots_url':root,'warnings':[],'matched_rules':[], 'actual_bot_access':'unknown'})
    if walked['reason']!='complete':
        result['reason']={'missing_evidence':'robots_missing_evidence','stale':'robots_stale','request_unverified':'robots_access_unverified'}.get(walked['reason'],walked['reason'])
        return result
    row=walked['record'];status=row['status'];product=agent.lower()
    if status==429 or status>=500:
        result['reason']='robots_access_unverified';return result
    if 400<=status<500:
        if product=='googlebot':result.update({'allowed':True,'reason':'google_4xx_no_restrictions'})
        else:result['reason']='engine_error_behavior_unverified'
        return result
    if not 200<=status<300:result['reason']='robots_http_unverified';return result
    if not isinstance(row.get('body'),bytes):result['reason']='robots_body_missing';return result
    parsed=evaluate_rules(row['body'],target,agent,root)
    result.update({k:v for k,v in parsed.items() if k not in {'agent','robots_url'}})
    return result
