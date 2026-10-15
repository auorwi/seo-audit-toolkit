"""Compare only explicitly aligned observations, with visible precision retained."""
from decimal import Decimal,InvalidOperation,localcontext
import math
from .shared import moment,fresh

def check_pair(left,right,*,at,max_age_hours=24,max_time_skew_seconds=60,relative_tolerance='0',absolute_tolerance='0'):
    moment(at)
    if not math.isfinite(max_age_hours) or max_age_hours<=0 or not math.isfinite(max_time_skew_seconds) or max_time_skew_seconds<0:raise ValueError('invalid_comparison_time_policy')
    def tolerance(raw):
        if type(raw) not in {str,int}:raise ValueError('tolerance_requires_decimal_text')
        try:value=Decimal(raw)
        except InvalidOperation:raise ValueError('invalid_tolerance')
        if not value.is_finite() or value<0:raise ValueError('invalid_tolerance')
        return value
    relative,absolute=tolerance(relative_tolerance),tolerance(absolute_tolerance)
    result={'status':'incomparable','reasons':[],'left':left,'right':right,'difference':None,'relative_tolerance':str(relative),'absolute_tolerance':str(absolute),'max_time_skew_seconds':max_time_skew_seconds}
    for row in [left,right]:
        if not fresh(row.get('observed_at'),at,max_age_hours):return {**result,'status':'insufficient_data','reasons':['observation_not_current']}
        if row.get('number',{}).get('status')!='observed':return {**result,'status':'insufficient_data','reasons':['numeric_value_unavailable']}
    keys=['asset_id','concept','unit','basis','period','scenario','temporal_kind']
    mismatches=[key for key in keys if not isinstance(left.get(key),str) or not left[key].strip() or not isinstance(right.get(key),str) or not right[key].strip() or left[key]!=right[key]]
    if mismatches:return {**result,'reasons':['semantic_context_not_aligned'],'mismatched_dimensions':mismatches}
    if left['temporal_kind'] not in {'live','static','same_snapshot_assertions'}:return {**result,'reasons':['unsupported_temporal_kind']}
    if left['temporal_kind']=='same_snapshot_assertions':
        if not left.get('snapshot_id') or left['snapshot_id']!=right.get('snapshot_id') or left['observed_at']!=right['observed_at']:return {**result,'reasons':['statements_not_in_same_snapshot']}
        result['scope']='internal statements in one capture; not synchronized source-data accuracy'
    if left['temporal_kind']=='live':
        if not all(fresh(row.get('data_at'),at,max_age_hours) for row in [left,right]):return {**result,'reasons':['data_time_unavailable_or_not_current']}
        skew=abs((moment(left['data_at'])-moment(right['data_at'])).total_seconds());result['data_time_skew_seconds']=skew
        if skew>max_time_skew_seconds:return {**result,'reasons':['live_snapshots_not_synchronized']}
    try:
        a,b=(Decimal(row['number']['value']) for row in [left,right]);qa,qb=(Decimal(row['number']['quantum']) for row in [left,right])
        if any(not x.is_finite() for x in [a,b,qa,qb]) or qa<0 or qb<0:raise InvalidOperation()
        with localcontext() as context:
            context.prec=max(64,sum(len(x.as_tuple().digits)+abs(x.as_tuple().exponent) for x in [a,b,qa,qb])+32)
            delta=abs(a-b);rounding=(qa+qb)/2;allowance=max(absolute,max(abs(a),abs(b))*relative)
            result.update(difference=format(delta,'f'),combined_display_half_step=format(rounding,'f'),configured_allowance=format(allowance,'f'))
            if a==b:status='consistent'
            elif delta==rounding:status='display_rounding_boundary'
            elif delta<=rounding:
                status='precision_loss' if (a==0 and b>0) or (b==0 and a>0) else 'consistent_with_display_precision'
            elif delta<=rounding+allowance:status='within_configured_tolerance'
            elif delta<qa+qb:status='possible_truncation'
            else:status='conflict'
            return {**result,'status':status}
    except (KeyError,TypeError,InvalidOperation):return {**result,'status':'insufficient_data','reasons':['invalid_numeric_representation']}
