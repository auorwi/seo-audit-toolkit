"""Parse explicitly formatted quantities without float conversion or unit guessing."""
import re
from decimal import Decimal,InvalidOperation,localcontext
SCALE={'K':3,'M':6,'B':9,'T':12}

def parse_quantity(raw,*,decimal_mark='.',group_mark=',',exact=False):
    if type(exact) is not bool:raise ValueError('exact_flag_requires_boolean')
    if decimal_mark not in {'.',','} or group_mark not in {None,',','.',' ','\u00a0','\u202f'} or decimal_mark==group_mark:raise ValueError('invalid_numeric_separators')
    result={'raw':raw,'status':'invalid','value':None,'quantum':None,'decimal_mark':decimal_mark,'group_mark':group_mark,'exact':exact}
    if raw is None or (isinstance(raw,str) and raw.strip().lower() in {'','--','n/a','null'}):return {**result,'status':'missing','reason':'missing_numeric_value'}
    if type(raw) not in {str,int}:return {**result,'reason':'numeric_text_or_integer_required'}
    text=str(raw).strip()
    if len(text)>2048:return {**result,'reason':'numeric_literal_too_long'}
    shift=SCALE.get(text[-1:],0)
    if shift:text=text[:-1].rstrip()
    digits=r'[0-9]+'
    if group_mark is not None:
        g=re.escape(group_mark);digits=r'(?:[0-9]+|[0-9]{1,3}(?:'+g+r'[0-9]{3})+)'
    pattern=r'[+-]?'+digits+r'(?:'+re.escape(decimal_mark)+r'[0-9]+)?(?:[eE][+-]?[0-9]+)?'
    if not re.fullmatch(pattern,text):return {**result,'reason':'unsupported_numeric_notation'}
    canonical=text.replace(group_mark,'') if group_mark else text;canonical=canonical.replace(decimal_mark,'.')
    try:
        value=Decimal(canonical)
        if not value.is_finite() or abs(value.as_tuple().exponent)>1000 or abs(value.adjusted())>1000:return {**result,'reason':'numeric_range_exceeded'}
        with localcontext() as context:
            context.prec=max(64,len(value.as_tuple().digits)+20)
            value=value.scaleb(shift);quantum=Decimal(0) if exact else Decimal(1).scaleb(value.as_tuple().exponent)
            result.update(status='observed',value=format(value,'f'),quantum=format(quantum,'f'))
        return result
    except InvalidOperation:return {**result,'reason':'invalid_decimal'}
