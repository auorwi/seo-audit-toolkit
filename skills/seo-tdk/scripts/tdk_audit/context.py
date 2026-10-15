"""Validate explicit observations; never infer product availability from advertising."""
import hashlib,re,unicodedata
from .shared import fresh,url_id

def normalized(text):return re.sub(r'\s+',' ',unicodedata.normalize('NFKC',text or '')).strip().casefold()
def contains(text,term):
    text=normalized(text);term=normalized(term)
    if not term:return False
    # ASCII tickers must not match a substring of a different ticker.
    pattern=re.escape(term)
    if term[0].isascii() and term[0].isalnum():pattern=r'(?<![a-z0-9])'+pattern
    if term[-1].isascii() and term[-1].isalnum():pattern+=r'(?![a-z0-9])'
    return bool(re.search(pattern,text))

def validate_context(capture,context,*,at,max_age_hours=168):
    result={'facts':{},'gaps':[],'metadata':{}}
    if not context:return {**result,'gaps':['context_not_observed']}
    try:
        if any(context.get(k)!=capture.get(k) for k in ['snapshot_id','document_sha256']) or url_id(context['url'])!=url_id(capture['url']):raise ValueError('context_document_binding')
        if not context.get('source') or not fresh(context.get('checked_at'),at,max_age_hours):raise ValueError('context_provenance_or_time')
        facts=context.get('facts',[])
        if not isinstance(facts,list):raise ValueError('facts_array_required')
        ids=[f['id'] for f in facts]
        if len(set(ids))!=len(ids):raise ValueError('duplicate_fact_id')
        for key in ['requirements','reviews']:
            if key in context and (not isinstance(context[key],list) or not all(isinstance(v,dict) for v in context[key])):raise ValueError('invalid_'+key)
        if 'translation_keys' in context and (not isinstance(context['translation_keys'],list) or not all(isinstance(v,str) for v in context['translation_keys'])):raise ValueError('invalid_translation_keys')
        if 'dynamic_title' in context:
            d=context['dynamic_title']
            if not isinstance(d,dict) or not isinstance(d.get('enabled',False),bool) or not isinstance(d.get('stable_fact_ids',[]),list) or not all(isinstance(v,str) for v in d.get('stable_fact_ids',[])):raise ValueError('invalid_dynamic_title')
        result['metadata']={k:context[k] for k in ['template','language','requirements','translation_keys','dynamic_title','reviews'] if k in context}
        for fact in facts:
            try:
                if not all(isinstance(fact.get(k),str) and fact[k].strip() for k in ['id','role','value','quote','source','origin']):raise ValueError('fact_provenance_required')
                if not fresh(fact.get('observed_at'),at,max_age_hours):raise ValueError('fact_not_current')
                if fact['origin']=='page':
                    if capture.get('representation')!='rendered_html' or capture.get('readiness')!='ready' or fact.get('visibility')!='visible' or not fact.get('location'):raise ValueError('visible_page_fact_required')
                    text=capture['fields']['body_text']
                elif fact['origin'] in {'route_registry','product_catalog','search_console'}:
                    document=fact.get('document',{});text=document.get('text')
                    if not isinstance(text,str) or hashlib.sha256(text.encode()).hexdigest()!=document.get('sha256'):raise ValueError('external_fact_document_binding')
                else:raise ValueError('unsupported_fact_origin')
                if normalized(fact['quote']) not in normalized(text):raise ValueError('fact_quote_not_observed')
                aliases=fact.get('aliases',[fact['value']])
                if not isinstance(aliases,list) or not aliases or not all(isinstance(x,str) and x.strip() for x in aliases):raise ValueError('fact_aliases_invalid')
                if not contains(fact['quote'],fact['value']):raise ValueError('fact_value_not_supported_by_quote')
                if fact['role']=='listing_status' and (fact['origin']!='product_catalog' or fact['value'] not in {'listed','not_listed','delisted','unknown'}):raise ValueError('catalog_listing_status_required')
                result['facts'][fact['id']]=dict(fact)
            except (ValueError,KeyError,TypeError) as error:result['gaps'].append({'fact_id':fact.get('id'),'reason':str(error)})
        for id,fact in list(result['facts'].items()):
            if fact['role']!='listing_status':continue
            subject=fact.get('subject',{});entities=[f for f in result['facts'].values() if f['role']=='page_entity']
            matching=len(entities)==1 and any(normalized(subject.get('entity'))==normalized(t) for t in [entities[0]['value']]+entities[0].get('aliases',[]))
            if not matching or not all(isinstance(subject.get(k),str) and subject[k] for k in ['entity','product','market_scope']) or not all(contains(fact['quote'],subject[k]) for k in ['entity','product']):
                del result['facts'][id];result['gaps'].append({'fact_id':id,'reason':'catalog_subject_not_bound_to_current_page'})
    except (ValueError,KeyError,TypeError) as error:
        result['facts']={};result['metadata']={};result['gaps'].append(str(error))
    return result
