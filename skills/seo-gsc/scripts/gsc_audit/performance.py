"""Compare only like-for-like observed Search Analytics rows, not inferred site totals."""
import json,math
from datetime import date

def compare(before,after):
    qa,qb=before['query'],after['query'];
    if set(qa.get('dimensions',[]))&{'date','hour'} or set(qb.get('dimensions',[]))&{'date','hour'}:raise ValueError('time_dimension_requires_alignment_not_supported')
    a0,a1=(date.fromisoformat(qa[k]) for k in ['startDate','endDate']);b0,b1=(date.fromisoformat(qb[k]) for k in ['startDate','endDate'])
    if (a1-a0)!=(b1-b0) or a1>=b0:raise ValueError('windows_not_comparable')
    if before['may_include_incomplete_data'] or after['may_include_incomplete_data']:raise ValueError('incomplete_data')
    if before['start_row'] or after['start_row']:raise ValueError('partial_page_offset')
    if before['response_aggregation']!=after['response_aggregation']:raise ValueError('aggregation_mismatch')
    def query(q):
        defaults={'dimensions':[],'type':'web','aggregationType':'auto','dimensionFilterGroups':[],'dataState':'final','rowLimit':1000,'startRow':0}
        return {k:v for k,v in {**defaults,**q}.items() if k not in {'startDate','endDate'}}
    if query(qa)!=query(qb):raise ValueError('query_scope_mismatch')
    def keyed(period):
        out={}
        for r in period['rows']:
            key=json.dumps(r['dimensions'],sort_keys=True,separators=(',',':'))
            if key in out:raise ValueError('duplicate_dimension_keys')
            out[key]=r
        return out
    def aggregate(period):
        rows=period['rows'];i=sum(r['impressions'] for r in rows);c=sum(r['clicks'] for r in rows)
        return {'clicks':c,'impressions':i,'ctr':c/i if i else None,'position':math.fsum(r['position']*(r['impressions']/i) for r in rows) if i else None,'observed_rows_only':True}
    a,b=keyed(before),keyed(after);matched=[]
    for key in sorted(a.keys()&b.keys()):
        x,y=a[key],b[key];matched.append({'dimensions':x['dimensions'],'before':x,'after':y,'clicks_delta':y['clicks']-x['clicks'],'impressions_delta':y['impressions']-x['impressions'],
          'ctr_percentage_point_delta':(y['ctr']-x['ctr'])*100,'position_delta':y['position']-x['position'],'clicks_change_ratio':(y['clicks']-x['clicks'])/x['clicks'] if x['clicks'] else None})
    return {'matched_rows':matched,'unmatched_before':[a[k]['dimensions'] for k in sorted(a.keys()-b.keys())],
            'unmatched_after':[b[k]['dimensions'] for k in sorted(b.keys()-a.keys())],'observed_before':aggregate(before),'observed_after':aggregate(after),
            'sitewide_change_proven':False,'missing_rows_are_zero':False,'causality_proven':False,'timezone':'America/Los_Angeles'}
