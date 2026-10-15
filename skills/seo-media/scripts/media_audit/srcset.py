"""Bounded srcset candidate parsing; actual resource selection belongs to a browser."""
import re
from decimal import Decimal,InvalidOperation,localcontext
from urllib.parse import urlsplit,urljoin
SPACE='\t\n\f\r '

def density_text(n):
    with localcontext() as context:
        context.prec=max(32,len(n.as_tuple().digits)+2)
        return str(n.normalize())

def resolve_resource(value,base_url):
    if not isinstance(value,str) or not value.strip():return None
    value=value.strip();url=urljoin(base_url,value)
    try:
        p=urlsplit(url)
        if p.scheme in {'data','blob'}:return url
        if p.scheme in {'https','http'} and p.hostname and not p.username and not p.password and not any(ord(c)<32 or c.isspace() for c in url):return url
    except ValueError:pass
    return None

def parse_srcset(value,base_url):
    if not isinstance(value,str):raise ValueError('srcset_string_required')
    result={'candidates':[],'gaps':[],'selected_url':None};i=0;seen=set();types=set()
    if len(value)>1_000_000:return {**result,'gaps':[{'reason':'srcset_size_limit'}]}
    while i<len(value):
        start=i
        while i<len(value) and value[i] in SPACE+',':i+=1
        if ',' in value[start:i]:result['gaps'].append({'reason':'extra_separator'})
        if i==len(value):break
        start=i
        while i<len(value) and value[i] not in SPACE:i+=1
        raw=value[start:i];descriptors=[]
        if raw.endswith(','):
            trimmed=raw.rstrip(',')
            if len(raw)-len(trimmed)>1:result['gaps'].append({'reason':'multiple_trailing_commas','raw_url':raw})
            raw=trimmed
        else:
            token='';paren=False
            while i<len(value):
                ch=value[i];i+=1
                if paren:
                    token+=ch
                    if ch==')':paren=False
                elif ch=='(':token+=ch;paren=True
                elif ch==',':break
                elif ch in SPACE:
                    if token:descriptors.append(token);token=''
                else:token+=ch
            if token:descriptors.append(token)
        width=None;density=None;future_h=None;error=False
        for d in descriptors:
            if len(d)>1000:error=True;continue
            if re.fullmatch(r'[0-9]+w',d):
                n=int(d[:-1])
                if not n or width is not None or density is not None:error=True
                width=n
            elif re.fullmatch(r'-?(?:[0-9]+(?:\.[0-9]+)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?x',d):
                try:n=Decimal(d[:-1])
                except InvalidOperation:error=True;continue
                if not n.is_finite() or abs(n.adjusted())>1000 or abs(n.as_tuple().exponent)>1000 or n<0 or width is not None or density is not None or future_h is not None:error=True
                density=n
            elif re.fullmatch(r'[0-9]+h',d):
                n=int(d[:-1]);result['gaps'].append({'reason':'future_height_descriptor','raw_url':raw})
                if not n or future_h is not None or density is not None:error=True
                future_h=n
            else:error=True
        if future_h is not None and width is None:error=True
        url=resolve_resource(raw,base_url)
        if error or not url:
            result['gaps'].append({'reason':'invalid_descriptor' if error else 'unsupported_resource_url','raw_url':raw,'descriptors':descriptors});continue
        if width is None and density is None:density=Decimal(1)
        if density==0:result['gaps'].append({'reason':'nonpositive_density_authoring','raw_url':raw})
        key=('w',width) if width is not None else ('x',density_text(density))
        if key in seen:result['gaps'].append({'reason':'duplicate_descriptor','descriptor':key})
        seen.add(key);types.add(key[0])
        result['candidates'].append({'raw_url':raw,'url':url,'width':width,'density':density_text(density) if density is not None else None,'descriptors':descriptors})
    if len(types)>1:result['gaps'].append({'reason':'mixed_width_density_descriptors'})
    return result
