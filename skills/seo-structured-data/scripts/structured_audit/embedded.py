"""Normalize native extruct output without calling extraction semantic validation."""
import re
from urllib.parse import urljoin
from .shared import fresh,url_id

def normalize_extruct(record,*,url,document_sha256,at,max_age_hours=168):
    result={'status':'evidence_gap','entities':[],'references':[],'gaps':[],'covered_syntaxes':[],
        'coverage':{'schema_semantic_validation':False,'engine_validation':False}}
    def short(value):
        if isinstance(value,str) and value.startswith(('https://schema.org/','http://schema.org/')):return value.rsplit('/',1)[-1]
        return value
    def identity(value):return value if value.startswith('_:') else urljoin(url,value)
    try:
        if record.get('tool')!='extruct' or not record.get('source') or not record.get('checker_version'):raise ValueError('extruct_provenance_required')
        if url_id(record['url'])!=url_id(url):raise ValueError('extruct_url_mismatch')
        if not fresh(record.get('checked_at'),at,max_age_hours):raise ValueError('extruct_not_current')
        if not re.fullmatch('[0-9a-f]{64}',document_sha256) or record.get('document_sha256')!=document_sha256 or record.get('input_sha256')!=document_sha256:raise ValueError('extruct_document_binding')
        if record.get('state') not in {'completed','partial_extraction'}:raise ValueError('extruct_not_completed')
        if not isinstance(record.get('payload'),dict):raise ValueError('extruct_payload_required')
        for syntax in ['microdata','rdfa']:
            if syntax not in record.get('syntaxes',[]) or not isinstance(record['payload'].get(syntax),list):
                result['gaps'].append({'syntax':syntax,'reason':'syntax_result_missing_or_invalid'});continue
            entities=[];references=[]
            def convert(value,path,depth=0):
                if depth>100:raise ValueError('extraction_depth_limit')
                if isinstance(value,list):return [convert(v,path+'['+str(i)+']',depth+1) for i,v in enumerate(value)]
                if not isinstance(value,dict):return value
                if syntax=='microdata':
                    if 'type' not in value and 'properties' not in value:return {k:convert(v,path+'["'+k+'"]',depth+1) for k,v in value.items()}
                    raw_types=value.get('type',[]);raw_types=[raw_types] if isinstance(raw_types,str) else raw_types
                    if not isinstance(raw_types,list) or not all(isinstance(t,str) for t in raw_types) or not isinstance(value.get('properties',{}),dict):raise ValueError('microdata_shape_invalid')
                    id=value.get('id');data={'@type':[short(t) for t in raw_types]}
                    entity={'syntax':syntax,'path':path,'id':identity(id) if isinstance(id,str) else None,'types':data['@type'],'schema_context_known':any(short(t)!=t for t in raw_types),'data':data}
                    if value.get('_source_locator'):entity['source_locator']=value['_source_locator']
                    entities.append(entity)
                    for k,v in value.get('properties',{}).items():data[short(k)]=convert(v,path+'["properties"]["'+k+'"]',depth+1)
                    if id:data['@id']=identity(id)
                    return data
                if '@value' in value:return value['@value']
                raw_types=value.get('@type',[]);raw_types=[raw_types] if isinstance(raw_types,str) else raw_types
                if not isinstance(raw_types,list) or not all(isinstance(t,str) for t in raw_types):raise ValueError('rdfa_types_invalid')
                id=value.get('@id');resolved=identity(id) if isinstance(id,str) else None
                if set(value)=={'@id'}:
                    if resolved is None:raise ValueError('rdfa_id_invalid')
                    references.append({'syntax':syntax,'path':path,'id':resolved});return {'@id':resolved}
                data={};entity={'syntax':syntax,'path':path,'id':resolved,'types':[short(t) for t in raw_types],'schema_context_known':any(short(t)!=t for t in raw_types),'data':data}
                entities.append(entity)
                for key,val in value.items():
                    if key=='@type':data[key]=[short(t) for t in raw_types]
                    elif key=='@id':data[key]=resolved
                    else:
                        converted=convert(val,path+'["'+key+'"]',depth+1)
                        data[short(key)]=converted[0] if isinstance(converted,list) and len(converted)==1 else converted
                return data
            try:
                for i,row in enumerate(record['payload'][syntax]):
                    if not isinstance(row,dict):raise ValueError('entity_object_required')
                    convert(row,'$["'+syntax+'"]['+str(i)+']')
                result['entities']+=entities;result['references']+=references;result['covered_syntaxes'].append(syntax)
            except (ValueError,TypeError,RecursionError) as error:result['gaps'].append({'syntax':syntax,'reason':str(error)})
        if record.get('state')=='partial_extraction':result['gaps']+=record.get('errors',[{'reason':'partial_extraction'}])
        result['status']='usable' if len(result['covered_syntaxes'])==2 and not result['gaps'] else 'partial' if result['covered_syntaxes'] else 'evidence_gap'
    except (ValueError,KeyError,TypeError) as error:result['gaps'].append(str(error))
    return result
