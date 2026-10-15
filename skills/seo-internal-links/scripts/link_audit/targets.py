"""Resolve bounded chains from latest verified GET observations; no network guessing."""
import math,re
from urllib.parse import urljoin
from .shared import url_id,moment,fresh
from crawlability.common import header_pairs
REDIRECTS={301,302,303,307,308}
def assess_targets(records,targets,*,at,max_age_hours=168,max_hops=5):
    moment(at)
    if not isinstance(max_hops,int) or isinstance(max_hops,bool) or max_hops<1:raise ValueError('invalid_hop_limit')
    if not math.isfinite(max_age_hours) or max_age_hours<=0:raise ValueError('invalid_freshness_window')
    latest={}
    for record in records:
        url=url_id(record['url']);time=moment(record['checked_at'])
        if url not in latest or time>moment(latest[url]['checked_at']):latest[url]=record
    result={'targets':[],'gaps':[]}
    for requested in sorted({url_id(u) for u in targets}):
        row={'requested_url':requested,'final_url':requested,'kind':'not_observed','chain':[],'redirect_observed':False,'content_validity':'unverified','indexability':'unverified','permanent_broken_proven':False,
            'chain_basis':'assembled from latest observed hops; not necessarily one navigation'}
        result['targets'].append(row);current=requested;visited=set()
        while True:
            row['final_url']=current
            if current in visited:row['kind']='redirect_loop_observed';break
            visited.add(current);record=latest.get(current)
            if record is None:row['kind']='redirect_target_unverified' if row['redirect_observed'] else 'not_observed';break
            row['chain'].append(record)
            if record.get('error') or record.get('state','completed')!='completed':row['kind']='request_failed';break
            proof=record.get('evidence')
            if not fresh(record.get('checked_at'),at,max_age_hours) or record.get('evidence_error') or record.get('method')!='GET' or not record.get('source') or not isinstance(proof,dict) or not re.fullmatch('[a-f0-9]{64}',proof.get('sha256','')):
                row['kind']='evidence_unverified';break
            status=record.get('status');row['status']=status
            if type(status) is not int or not 100<=status<=599:row['kind']='evidence_unverified';break
            if status in REDIRECTS:
                row['redirect_observed']=True
                try:
                    locations={url_id(urljoin(current,value)) for key,value in header_pairs(record.get('headers',[])) if key=='location'}
                    if len(locations)!=1:raise ValueError('location_not_unique')
                except (ValueError,TypeError):row['kind']='redirect_location_ambiguous';break
                if len(row['chain'])>max_hops:row['kind']='redirect_limit';break
                current=next(iter(locations));continue
            if status in {404,410}:row['kind']='broken_http_target'
            elif status in {401,403,429}:row['kind']='access_limited'
            elif status>=500:row['kind']='server_error'
            elif 200<=status<300:row['kind']='redirected_link' if row['redirect_observed'] else 'http_success_observed'
            else:row['kind']='http_response_review'
            break
        if row['kind'] in {'not_observed','request_failed','evidence_unverified','redirect_target_unverified','redirect_location_ambiguous','redirect_limit'}:
            result['gaps'].append({'url':requested,'at_url':current,'reason':row['kind']})
    return result
