"""Strict JSON syntax and bounded entity inventory; not a full JSON-LD processor."""
import json
from html.parser import HTMLParser
from urllib.parse import urljoin

class Object(dict):
    def __init__(self,pairs):
        super().__init__();self.duplicates={}
        for key,value in pairs:
            if key in self:
                self.duplicates.setdefault(key,[self[key]]).append(value)
            else:self[key]=value

class Scripts(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=False);self.scripts=[];self.active=None;self.template=0
    def handle_starttag(self,tag,attrs):
        if tag=='template':self.template+=1
        if tag=='script' and not self.template and (dict(attrs).get('type') or '').split(';')[0].strip().lower()=='application/ld+json':
            line,column=self.getpos();self.active={'index':len(self.scripts),'line':line,'column':column+1,'raw':'','closed':False};self.scripts.append(self.active)
    def handle_endtag(self,tag):
        if tag=='script' and self.active:self.active['closed']=True;self.active=None
        if tag=='template':self.template=max(0,self.template-1)
    def handle_data(self,data):
        if self.active:self.active['raw']+=data

def schema_namespace(value):return isinstance(value,str) and value.rstrip('/') in {'http://schema.org','https://schema.org'}

def extract_jsonld(html,url):
    parser=Scripts();parser.feed(html);parser.close()
    result={'scripts':parser.scripts,'entities':[],'references':[],'errors':[],'gaps':[],
        'coverage':{'json_syntax':True,'full_jsonld_semantics':False,'network_context_resolution':False}}
    def error(rule,index,path,**kw):result['errors'].append({'rule':rule,'script_index':index,'path':path,**kw})
    def walk(value,path,index,known=False,prefixes=None,depth=0):
        if depth>100:result['gaps'].append({'script_index':index,'reason':'entity_depth_limit','path':path});return
        if isinstance(value,list):
            for i,item in enumerate(value):walk(item,path+'['+str(i)+']',index,known,prefixes,depth+1)
        elif isinstance(value,dict):
            prefixes=dict(prefixes or {})
            if '@context' in value:
                context=value['@context']
                if schema_namespace(context):known=True
                elif isinstance(context,dict):
                    if '@vocab' in context:known=schema_namespace(context['@vocab'])
                    for key,target in context.items():
                        if schema_namespace(target):prefixes[key]=target
                        elif key!='@vocab':result['gaps'].append({'script_index':index,'reason':'context_mapping_not_expanded','path':path,'term':key})
                else:known=False;result['gaps'].append({'script_index':index,'reason':'context_not_resolved','path':path})
            for key,values in getattr(value,'duplicates',{}).items():error('duplicate_json_key',index,path,key=key,values=values)
            raw_types=value.get('@type',[]);raw_types=[raw_types] if isinstance(raw_types,str) else raw_types
            if not isinstance(raw_types,list) or not all(isinstance(t,str) for t in raw_types):error('invalid_type_value',index,path);raw_types=[]
            types=[];explicit_schema=False
            for t in raw_types:
                if t.startswith(('https://schema.org/','http://schema.org/')):types.append(t.rsplit('/',1)[-1]);explicit_schema=True
                elif ':' in t and t.split(':',1)[0] in prefixes:types.append(t.split(':',1)[1]);explicit_schema=True
                else:types.append(t)
            id=value.get('@id');resolved=(id if id.startswith('_:') else urljoin(url,id)) if isinstance(id,str) else None
            if '@id' in value and not isinstance(id,str):error('invalid_id_value',index,path)
            defined=bool(raw_types) or (resolved is not None and bool(set(value)-{'@id','@context'}))
            if defined:
                result['entities'].append({'script_index':index,'path':path,'id':resolved,'types':types,'schema_context_known':known or explicit_schema,'data':dict(value)})
                if not known and not explicit_schema:result['gaps'].append({'script_index':index,'reason':'schema_context_unknown','path':path})
            elif resolved is not None:result['references'].append({'script_index':index,'path':path,'id':resolved})
            for key,item in value.items():
                if key not in {'@context','@id','@type'}:walk(item,path+'['+json.dumps(key,ensure_ascii=False)+']',index,known,prefixes,depth+1)
    for script in parser.scripts:
        if not script['closed']:
            result['gaps'].append({'script_index':script['index'],'reason':'unclosed_jsonld_script'});continue
        if len(script['raw'].encode())>2*1024*1024:
            result['gaps'].append({'script_index':script['index'],'reason':'jsonld_script_size_limit'});continue
        try:
            def reject_constant(value):raise ValueError('non_json_numeric_constant:'+value)
            parsed=json.loads(script['raw'],object_pairs_hook=Object,parse_constant=reject_constant)
            if not isinstance(parsed,(dict,list)):raise ValueError('jsonld_root_must_be_object_or_array')
            walk(parsed,'$',script['index'])
        except (ValueError,RecursionError) as exc:error('json_syntax_error',script['index'],'$',message=str(exc))
    return result
