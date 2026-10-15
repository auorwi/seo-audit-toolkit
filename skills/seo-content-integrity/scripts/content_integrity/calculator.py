"""Verify observed calculator interactions against their own declared rate."""
from decimal import Decimal, InvalidOperation, localcontext
from .shared import fresh, moment

DIRECTIONS = {'asset_to_quote','quote_to_asset'}

def check_trial(row, *, at, max_age_hours=24):
    moment(at)
    result = {'status':'insufficient_data','trial':row,'market_rate_accuracy_verified':False}
    if (not fresh(row.get('observed_at'),at,max_age_hours)
        or row.get('interaction_status')!='completed' or row.get('readiness')!='ready'
        or row.get('rate_changed') is not False or row.get('direction') not in DIRECTIONS
        or row.get('rate_basis')!='quote_per_asset'):
        return {**result,'reason':'capture_or_rate_context_incomplete'}
    if not all(row.get(k) for k in ['asset_id','quote_unit','input_unit','output_unit','before_evidence_id','after_evidence_id','rate_evidence_id']):
        return {**result,'reason':'units_or_evidence_missing'}
    if row['before_evidence_id']==row['after_evidence_id']:
        return {**result,'reason':'no_distinct_interaction_evidence'}
    names=['requested_input','actual_input','output','rate']
    if any(row.get(k,{}).get('status')!='observed' for k in names):
        return {**result,'reason':'numeric_value_unavailable'}
    try:
        wanted,actual,output,rate=[Decimal(row[k]['value']) for k in names]
        oq,rq=[Decimal(row[k]['quantum']) for k in ['output','rate']]
        if any(not n.is_finite() for n in [wanted,actual,output,rate,oq,rq]) or min(wanted,actual,oq,rq)<0 or rate<=0:
            raise InvalidOperation()
        if wanted!=actual:return {**result,'status':'interaction_not_applied'}
        asset_unit=row.get('asset_unit',row['asset_id'])
        expected_units=(asset_unit,row['quote_unit']) if row['direction']=='asset_to_quote' else (row['quote_unit'],asset_unit)
        if (row['input_unit'],row['output_unit'])!=expected_units:
            return {**result,'status':'unit_conflict','expected_units':list(expected_units)}
        with localcontext() as context:
            context.prec=max(64,sum(len(n.as_tuple().digits)+abs(n.as_tuple().exponent) for n in [wanted,output,rate,oq,rq])+32)
            low,high=rate-rq/2,rate+rq/2
            if low<=0:return {**result,'reason':'rate_display_precision_too_coarse'}
            if row['direction']=='asset_to_quote':
                expected=actual*rate;lower=actual*low;upper=actual*high
            else:
                expected=actual/rate;lower=actual/high;upper=actual/low
            intersects=output+oq/2>=lower and output-oq/2<=upper
            if output==expected:status='consistent'
            elif intersects:status='precision_loss' if output==0 and expected>0 else 'consistent_with_display_precision'
            else:status='calculation_conflict'
            return {**result,'status':status,'expected_at_displayed_rate':format(expected,'f'),
                    'expected_interval':[format(lower,'f'),format(upper,'f')],'observed_output':format(output,'f')}
    except (KeyError,TypeError,InvalidOperation,ZeroDivisionError):
        return {**result,'reason':'invalid_numeric_representation'}

def check_suite(rows, *, at, quantities=('1','10','1000'), max_age_hours=24):
    contexts={(r.get('asset_id'),r.get('quote_unit')) for r in rows}
    required={(str(q),d) for q in quantities for d in DIRECTIONS}
    results=[check_trial(row,at=at,max_age_hours=max_age_hours) for row in rows]
    checked=set();interacted=set()
    for result in results:
        row=result['trial']
        try:
            actual=Decimal(row['actual_input']['value']);wanted=Decimal(row['requested_input']['value'])
            if actual.is_finite() and actual==wanted and row.get('interaction_status')=='completed' and row.get('readiness')=='ready' and fresh(row.get('observed_at'),at,max_age_hours) and row.get('direction') in DIRECTIONS:
                interacted.add((str(actual.normalize()),row['direction']))
        except (InvalidOperation,KeyError,TypeError):pass
        if result['status'] not in {'insufficient_data','interaction_not_applied'}:
            row=result['trial'];checked.add((str(Decimal(row['actual_input']['value']).normalize()),row['direction']))
    missing=[{'quantity':q,'direction':d} for q,d in sorted(required) if (str(Decimal(q).normalize()),d) not in checked]
    interaction_missing=[{'quantity':q,'direction':d} for q,d in sorted(required) if (str(Decimal(q).normalize()),d) not in interacted]
    return {'status':'mixed_context' if len(contexts)>1 else 'checked','results':results,
            'missing_cases':missing,'coverage_complete':bool(rows) and len(contexts)==1 and not missing,
            'completed_interactions':len(interacted),'interaction_missing_cases':interaction_missing,
            'interaction_coverage_complete':bool(rows) and len(contexts)==1 and not interaction_missing,
            'market_rate_accuracy_verified':False}
