"""Conservative BCP47 subset and distinct Google hreflang profile."""
import hashlib,json,re
from pathlib import Path
from functools import lru_cache

@lru_cache(maxsize=1)
def registry():
    root=Path(__file__).resolve().parents[2]/'references/data'
    raw=(root/'language-subtag-registry.txt').read_bytes()
    records={};ranges=[]
    for block in raw.decode().split('%%')[1:]:
        fields={};key=None
        for line in block.strip().splitlines():
            if line.startswith(' ') and key:fields[key][-1]+=' '+line.strip()
            elif ': ' in line:
                key,value=line.split(': ',1);fields.setdefault(key,[]).append(value)
        typ=fields.get('Type',[''])[0];subtag=fields.get('Subtag',fields.get('Tag',['']))[0].lower()
        if '..' in subtag:ranges.append((typ,*subtag.split('..'),fields))
        else:records[(typ,subtag)]=fields
    countries={x['alpha_2'].lower() for x in json.loads((root/'iso3166-1.json').read_text())['3166-1']}
    return records,ranges,countries,raw.decode().splitlines()[0].split(': ',1)[1],hashlib.sha256(raw).hexdigest()

def validate_locale(value):
    records,ranges,countries,date,sha=registry()
    out={'value':value,'normalized':value,'bcp_status':'invalid','google_status':'unsupported','language':None,'script':None,'region':None,'preferred':None,'registry_date':date,'registry_sha256':sha}
    def lookup(typ,subtag):
        key=subtag.lower()
        return records.get((typ,key)) or next((fields for t,lo,hi,fields in ranges if t==typ and len(key)==len(lo) and lo<=key<=hi),None)
    if not isinstance(value,str) or not re.fullmatch(r'[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*',value):return out
    if value.lower()=='x-default':return {**out,'normalized':'x-default','bcp_status':'special_fallback','google_status':'fallback'}
    parts=value.split('-');lang=parts.pop(0).lower();out['language']=lang
    if lang=='x' or ('grandfathered',value.lower()) in records:return {**out,'bcp_status':'review','google_status':'review'}
    language=lookup('language',lang)
    if not language:return out
    script=parts.pop(0).title() if parts and len(parts[0])==4 and parts[0].isalpha() else None
    region=parts.pop(0).upper() if parts and ((len(parts[0])==2 and parts[0].isalpha()) or (len(parts[0])==3 and parts[0].isdigit())) else None
    out.update(script=script,region=region,normalized='-'.join(x for x in [lang,script,region,*parts] if x))
    if parts:return {**out,'bcp_status':'review','google_status':'review'}
    if script and not lookup('script',script):return out
    if region and not lookup('region',region):return out
    out.update(bcp_status='registered_subset',google_status='supported')
    if len(lang)!=2 or (region and region.lower() not in countries):out['google_status']='unsupported'
    if language.get('Deprecated'):
        out.update(preferred=language.get('Preferred-Value',[None])[0],google_status='review')
    if script in {'Zzzz','Zyyy','Zinh'}:out['google_status']='review'
    return out
