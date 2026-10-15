"""Scoped vocabulary/domain review using a supplied official Schema.org snapshot."""
def term(value):
    if not isinstance(value,str):return None
    for prefix in ['schema:','https://schema.org/','http://schema.org/']:
        if value.startswith(prefix):return value[len(prefix):]
    return None

def refs(value):
    values=value if isinstance(value,list) else [value] if value else []
    return [t for row in values if isinstance(row,dict) and (t:=term(row.get('@id'))) is not None]

def build_vocabulary(data):
    if not isinstance(data,dict) or not isinstance(data.get('@graph'),list):raise ValueError('vocabulary_graph_required')
    result={'classes':{},'properties':{}}
    for node in data['@graph']:
        if not isinstance(node,dict):raise ValueError('vocabulary_node_invalid')
        name=term(node.get('@id'))
        if name is None:continue
        kinds=node.get('@type',[]);kinds=[kinds] if isinstance(kinds,str) else kinds
        if not isinstance(kinds,list):raise ValueError('vocabulary_type_invalid')
        if any(k in {'rdfs:Class','http://www.w3.org/2000/01/rdf-schema#Class'} for k in kinds):
            result['classes'][name]={'parents':refs(node.get('rdfs:subClassOf',node.get('http://www.w3.org/2000/01/rdf-schema#subClassOf')))}
        if any(k in {'rdf:Property','http://www.w3.org/1999/02/22-rdf-syntax-ns#Property'} for k in kinds):
            result['properties'][name]={'domains':refs(node.get('schema:domainIncludes',node.get('https://schema.org/domainIncludes'))),'ranges':refs(node.get('schema:rangeIncludes',node.get('https://schema.org/rangeIncludes')))}
    if not result['classes'] or not result['properties']:raise ValueError('vocabulary_empty_or_unsupported')
    return result

def review_terms(entity,vocabulary):
    result={'observations':[],'gaps':[],'coverage':{'engine_validation':False,'full_schema_semantic_validation':False,'range_validation':False}}
    if not entity.get('schema_context_known'):result['gaps'].append('schema_context_unknown');return result
    def observation(rule,**kw):result['observations'].append({'rule':rule,'classification':'schema_vocabulary_review',**kw})
    ancestors=set();stack=list(entity.get('types',[]))
    for type in entity.get('types',[]):
        if type not in vocabulary['classes']:observation('unknown_schema_type',type=type)
    while stack:
        type=stack.pop()
        if type in ancestors:continue
        ancestors.add(type);stack+=vocabulary['classes'].get(type,{}).get('parents',[])
    for key in entity.get('data',{}):
        if key.startswith('@'):continue
        if ':' in key:result['gaps'].append({'reason':'external_namespace_not_reviewed','property':key});continue
        prop=vocabulary['properties'].get(key)
        if prop is None:observation('unknown_schema_property',property=key);continue
        if prop['domains'] and ancestors and not ancestors.intersection(prop['domains']):observation('property_domain_review',property=key,expected_domains=prop['domains'],actual_types=entity.get('types',[]))
    return result
