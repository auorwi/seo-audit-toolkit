"""Selected field/graph rules. Engine eligibility and actual display stay unverified."""
import json,re
from decimal import Decimal,InvalidOperation

SOURCES={'price':'https://schema.org/price','rating':'https://developers.google.com/search/docs/appearance/structured-data/review-snippet',
 'breadcrumb':'https://developers.google.com/search/docs/appearance/structured-data/breadcrumb','product':'https://developers.google.com/search/docs/appearance/structured-data/product-snippet',
 'software':'https://developers.google.com/search/docs/appearance/structured-data/software-app','schema':'https://schema.org/docs/datamodel.html'}

def numeric(value):
    if isinstance(value,bool) or value is None:return None
    if not isinstance(value,(str,int,float,Decimal)):return None
    if isinstance(value,str) and not re.fullmatch(r'-?[0-9]+(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?',value.strip()):return None
    try:
        n=Decimal(str(value));return n if n.is_finite() else None
    except InvalidOperation:return None

def present(value):return value is not None and value!='' and value!=[] and value!={}

def audit_entities(entities,*,profile=None):
    if profile not in {None,'google_product_snippet','google_software_app','google_breadcrumb'}:raise ValueError('unsupported_local_profile')
    result={'observations':[],'gaps':[],'suggested_fabricated_values':False,'layers':{'syntax':'not_checked_here','schema_semantics':'partial_rules_only','engine_eligibility':'unverified','actual_display':'unverified'},'profile':profile,'rules_checked_at':'2026-09-17'}
    def emit(entity,rule,field,value=None,*,layer='schema_usage',classification='review',source='schema',detail=None):
        result['observations'].append({'rule':rule,'layer':layer,'classification':classification,'syntax':entity.get('syntax','json-ld'),
            'entity_path':entity['path'],'entity_id':entity.get('id'),'field':field,'value':value,'source_url':SOURCES[source],'detail':detail,
            'recommendation':'依据实际可见内容与对应规则修改字段；不补造价格、评分、商品资格或展示结果。'})
    valid=[]
    for entity in entities:
        if not entity.get('schema_context_known'):result['gaps'].append({'path':entity['path'],'reason':'schema_context_unknown'});continue
        valid.append(entity);types=set(entity.get('types',[]));data=entity['data']
        for key in ['price','lowPrice','highPrice']:
            if key in data and (numeric(data[key]) is None or (isinstance(data[key],str) and re.search('[eE]',data[key]))):emit(entity,'price_format_review',key,data[key],source='price')
        if types&{'Rating','AggregateRating'}:
            if 'ratingValue' in data:
                value=numeric(data['ratingValue']);best=numeric(data.get('bestRating',5));worst=numeric(data.get('worstRating',1))
                if None in (value,best,worst):emit(entity,'rating_number_review','ratingValue',data.get('ratingValue'),source='rating')
                elif worst>best or value<worst or value>best:emit(entity,'rating_bounds_review','ratingValue',data['ratingValue'],source='rating',detail={'best':str(best),'worst':str(worst)})
            for key in ['ratingCount','reviewCount']:
                if key in data:
                    n=numeric(data[key])
                    if n is None or n<0 or n!=n.to_integral_value():emit(entity,'rating_count_review',key,data[key],source='rating')
        brands=data.get('brand')
        if isinstance(brands,list):
            fingerprints=[]
            for brand in brands:
                if isinstance(brand,dict) and set(brand)=={'@id'}:continue
                fingerprint=json.dumps(brand,ensure_ascii=False,sort_keys=True)
                if fingerprint in fingerprints:emit(entity,'repeated_brand_value_review','brand',brands);break
                fingerprints.append(fingerprint)
        if 'BreadcrumbList' in types:
            items=data.get('itemListElement',[]);items=items if isinstance(items,list) else [items]
            positions=[numeric(x.get('position')) for x in items if isinstance(x,dict)]
            if len(positions)!=len(items) or any(p is None or p<=0 or p!=p.to_integral_value() for p in positions):emit(entity,'breadcrumb_position_review','itemListElement',items,source='breadcrumb')
            good=[p for p in positions if p is not None]
            if len(good)!=len(set(good)):emit(entity,'breadcrumb_position_duplicate','itemListElement',items,source='breadcrumb')
            if profile=='google_breadcrumb':
                if len(items)<2:emit(entity,'required_breadcrumb_items','itemListElement',items,layer='engine_local_rules',source='breadcrumb')
                last=max(good) if good else None
                for i,item in enumerate(items):
                    if not isinstance(item,dict):continue
                    nested=item.get('item');name=item.get('name') or (nested.get('name') if isinstance(nested,dict) else None)
                    if not present(name):emit(entity,'breadcrumb_name_missing',f'itemListElement[{i}].name',name,layer='engine_local_rules',source='breadcrumb')
                    if numeric(item.get('position'))!=last and not present(nested):emit(entity,'breadcrumb_item_missing',f'itemListElement[{i}].item',nested,layer='engine_local_rules',source='breadcrumb')
        if profile=='google_product_snippet':
            if 'Product' in types:
                if not present(data.get('name')):emit(entity,'required_product_name','name',layer='engine_local_rules',source='product')
                if not any(present(data.get(k)) for k in ['offers','aggregateRating','review']):emit(entity,'required_product_supporting_property','offers|aggregateRating|review',layer='engine_local_rules',source='product')
            if 'Offer' in types:
                spec=data.get('priceSpecification',{});spec=spec if isinstance(spec,dict) else {}
                if not present(data.get('price')) and not present(spec.get('price')):emit(entity,'required_offer_price','price|priceSpecification.price',layer='engine_local_rules',source='product')
                currency=data.get('priceCurrency',spec.get('priceCurrency'))
                if not present(currency):emit(entity,'recommended_price_currency_missing','priceCurrency',layer='engine_local_rules',classification='recommendation',source='product')
                elif not isinstance(currency,str) or not re.fullmatch('[A-Z]{3}',currency):emit(entity,'google_currency_format_review','priceCurrency',currency,layer='engine_local_rules',source='product')
            if 'AggregateOffer' in types:
                if not present(data.get('lowPrice')):emit(entity,'required_aggregate_low_price','lowPrice',layer='engine_local_rules',source='product')
                if not present(data.get('priceCurrency')):emit(entity,'required_aggregate_currency','priceCurrency',layer='engine_local_rules',source='product')
        if profile=='google_software_app' and types&{'SoftwareApplication','MobileApplication','WebApplication'}:
            if not present(data.get('name')):emit(entity,'required_software_name','name',layer='engine_local_rules',source='software')
            offers=data.get('offers',[]);offers=offers if isinstance(offers,list) else [offers]
            if not any(isinstance(x,dict) and present(x.get('price')) for x in offers):emit(entity,'required_software_price','offers.price',layer='engine_local_rules',source='software')
            if not any(present(data.get(k)) for k in ['aggregateRating','review']):emit(entity,'required_software_rating_or_review','aggregateRating|review',layer='engine_local_rules',source='software')
    by_id={}
    for entity in valid:
        if entity.get('id'):by_id.setdefault(entity['id'],[]).append(entity)
    for id,definitions in by_id.items():
        fields={}
        for entity in definitions:
            for key,value in entity['data'].items():
                if key.startswith('@'):continue
                previous=fields.get(key)
                if previous is not None and previous!=value:emit(entity,'entity_field_conflict_review',key,value,detail={'other_value':previous,'id':id})
                fields[key]=value
    return result
