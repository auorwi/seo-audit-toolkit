"""Deterministic checks of explicitly reviewed, evidence-bound content claims."""
from decimal import Decimal,InvalidOperation
from .shared import fresh,moment
from .numbers import parse_quantity

def check_claim(row, *, at, max_age_hours=24):
    moment(at)
    result={'status':'insufficient_data','claim':row}
    if row.get('reviewed') is not True or not fresh(row.get('observed_at'),at,max_age_hours):return result
    kind=row.get('kind')
    if kind=='numeric_display':
        if row.get('expected_numeric') is not True:return result
        number=parse_quantity(row.get('raw'),decimal_mark=row.get('decimal_mark','.'),group_mark=row.get('group_mark',','))
        status='invalid_numeric_display' if number['status']=='invalid' else 'consistent' if number['status']=='observed' else 'insufficient_data'
        return {**result,'status':status,'number':number}
    if kind=='direction':
        if row.get('change_kind') not in {'signed_percent','signed_absolute','magnitude'} or row.get('direction') not in {'increase','decrease'} or row.get('change',{}).get('status')!='observed':return result
        try:value=Decimal(row['change']['value'])
        except (InvalidOperation,KeyError,TypeError):return result
        if not value.is_finite():return result
        conflict=(row['direction']=='increase' and value<0) or (row['direction']=='decrease' and value>0 and row['change_kind']!='magnitude')
        return {**result,'status':'direction_conflict' if conflict else 'consistent'}
    if kind=='template_field':
        if row.get('required') is False:return {**result,'status':'not_applicable'}
        if row.get('required') is not True or not isinstance(row.get('value'),str) or not row.get('field'):return result
        status='unexpanded_placeholder' if row.get('unexpanded') is True else 'empty_template_field' if not row['value'].strip() else 'consistent'
        return {**result,'status':status}
    if kind=='freshness':
        if row.get('live_claim') is False:return {**result,'status':'not_applicable'}
        if row.get('live_claim') is not True:return result
        try:delta=(moment(at)-moment(row.get('data_at'))).total_seconds()
        except ValueError:return result
        if delta<0:return result
        return {**result,'status':'stale_data_live_claim' if delta>max_age_hours*3600 else 'consistent','data_age_seconds':delta}
    if kind=='lifecycle':
        if row.get('reference_market') and row.get('market')!=row['reference_market']:return {**result,'status':'incomparable'}
        if row.get('reference_asset_id') and row.get('asset_id')!=row['reference_asset_id']:return {**result,'status':'incomparable'}
        scope=row.get('reference_scope')
        if scope=='official_api':
            if row.get('reference_status')!='ok' or not fresh(row.get('reference_at'),at,max_age_hours):return result
            if not row.get('asset_id') or not row.get('market') or row.get('asset_id')!=row.get('reference_asset_id') or row.get('market')!=row.get('reference_market'):
                return {**result,'status':'incomparable'}
        elif scope!='same_page':return result
        state,reference=row.get('page_state'),row.get('reference_state')
        if reference not in {'active','ended','inactive','unlisted'} or state not in {'active','ended','inactive','unlisted','buy_cta'}:return result
        if state=='buy_cta':return {**result,'status':'potential_copy_conflict' if reference!='active' else 'consistent'}
        conflict=(state=='active')!=(reference=='active')
        return {**result,'status':'lifecycle_conflict' if conflict else 'consistent'}
    return result
