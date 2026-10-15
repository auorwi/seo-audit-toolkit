"""Load hashed observations, never substitute manifest assertions for page bytes."""
import json,hashlib
from pathlib import Path
from .shared import url_id,moment
from .extract import extract_html,extract_headers,extract_sitemap
from crawlability.adapters import read_body

def load_manifest(path):
    path=Path(path).resolve();data=json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(data,dict) or data.get('schema_version')!=1:raise ValueError('unsupported_manifest_version')
    keys=['captures','http_records','sitemaps','body_reviews','asset_mappings','switches']
    for key in keys:
        if not isinstance(data.get(key,[]),list):raise ValueError(key+'_array_required')
    result={'captures':[],'http_records':[],'assets':[],'body_reviews':[],'switches':[],'gaps':[]}
    def body(proof):
        value,error=read_body(proof,path.parent)
        if error:raise ValueError(error)
        return value
    def obj(proof):return json.loads(body(proof))
    for row in data.get('captures',[]):
        if not isinstance(row,dict):raise ValueError('capture_object_required')
        meta={k:row[k] for k in ['url','snapshot_id','captured_at','source','representation','document_sha256','entry_mode','requested_url','state','evidence','environment'] if k in row};meta['manifest_path']=str(path)
        try:
            url_id(row['url']);moment(row['captured_at'])
            if not row.get('source') or not row.get('snapshot_id') or row.get('representation') not in {'initial_html','rendered_html'}:raise ValueError('capture_provenance_required')
            if row.get('state','completed')!='completed':result['captures'].append(meta);continue
            raw=body(row.get('evidence'))
            if row.get('document_sha256')!=row['evidence']['sha256']:raise ValueError('document_hash_mismatch')
            parsed=extract_html(raw.decode('utf-8',errors='replace'),row['url']);c={**meta,**{k:v for k,v in parsed.items() if k!='gaps'},'state':'completed','readiness':row.get('readiness')}
            result['gaps'] += [{'url':row['url'],**g} for g in parsed['gaps']]
            if row.get('browser_evidence'):
                try:
                    b=obj(row['browser_evidence'])
                    if not isinstance(b,dict) or not b.get('source') or any(b.get(k)!=c.get(k) for k in ['url','snapshot_id','captured_at','document_sha256']):raise ValueError('browser_document_binding')
                    if isinstance(b.get('visible_main'),str) and b.get('main_selector'):c['visible_main']=b['visible_main'];c['main_selector']=b['main_selector']
                    if isinstance(b.get('visible_fields'),dict) and all(isinstance(v,bool) for v in b['visible_fields'].values()):c['visible_fields']=b['visible_fields']
                    c['browser_evidence']=row['browser_evidence']
                except (ValueError,KeyError,TypeError) as e:result['gaps'].append({'url':row['url'],'reason':str(e)})
            result['captures'].append(c)
        except (ValueError,KeyError,TypeError) as e:
            result['gaps'].append({'url':row.get('url'),'reason':str(e)})
            try:
                url_id(row['url']);moment(row['captured_at'])
                if row.get('snapshot_id') and row.get('representation'):result['captures'].append({**meta,'state':'evidence_error'})
            except (ValueError,KeyError,TypeError):pass
    for row in data.get('http_records',[]):
        if not isinstance(row,dict):raise ValueError('http_record_object_required')
        c={**row,'manifest_path':str(path)}
        try:
            url_id(row['url']);moment(row['checked_at'])
            if row.get('evidence_kind')!='actual_response_metadata':raise ValueError('actual_http_metadata_required')
            saved=obj(row.get('evidence'))
            if not isinstance(saved,dict) or any(saved.get(k)!=row.get(k) for k in ['url','checked_at','source','state','method','status','headers']):raise ValueError('http_metadata_binding')
            if row.get('source') and row.get('method')=='GET' and row.get('state')=='completed' and type(row.get('status')) is int and 200<=row['status']<300:
                parsed=extract_headers(row.get('headers',[]),row['url']);result['gaps'] += [{'url':row['url'],**g} for g in parsed['gaps']]
                result['captures'].append({'url':row['url'],'snapshot_id':'http-'+row['evidence']['sha256'],'document_sha256':row['evidence']['sha256'],'captured_at':row['checked_at'],'source':row['source'],'state':'completed','representation':'http_headers','entry_mode':'http','evidence':row['evidence'],**{k:v for k,v in parsed.items() if k!='gaps'}})
        except (ValueError,KeyError,TypeError) as e:c['evidence_error']=str(e);result['gaps'].append({'url':row.get('url'),'reason':str(e)})
        result['http_records'].append(c)
    for row in data.get('sitemaps',[]):
        try:
            moment(row['captured_at']);url_id(row['url'])
            if not row.get('source'):raise ValueError('sitemap_source_required')
            parsed=extract_sitemap(body(row['evidence']).decode('utf-8'));result['gaps']+=parsed['gaps']
            for url in parsed['urls']:
                key=row['evidence']['sha256']+'|'+url
                result['captures'].append({'url':url,'snapshot_id':'sitemap-'+hashlib.sha256(key.encode()).hexdigest(),'captured_at':row['captured_at'],'source':row['source'],'document_sha256':row['evidence']['sha256'],'state':'completed','representation':'sitemap','channel_scope':row['url'],'entry_mode':'sitemap','evidence':row['evidence'],'alternates':[a for a in parsed['alternates'] if a['source_url']==url]})
        except (ValueError,KeyError,TypeError) as e:result['gaps'].append({'reason':'sitemap_'+str(e)})
    for input_key,output_key in [('body_reviews','body_reviews'),('asset_mappings','assets'),('switches','switches')]:
        for proof in data.get(input_key,[]):
            try:
                value=obj(proof);rows=value if isinstance(value,list) else [value]
                for row in rows:
                    if not isinstance(row,dict):raise ValueError('evidence_object_required')
                    if input_key=='asset_mappings':
                        url_id(row['url']);moment(row['mapped_at'])
                        if not row.get('source'):raise ValueError('mapping_source_required')
                    result[output_key].append({**row,'input_evidence':proof,'manifest_path':str(path)})
            except (ValueError,KeyError,TypeError) as e:result['gaps'].append({'reason':input_key+'_'+str(e)})
    seen={}
    for c in result['captures']:
        key=c['snapshot_id']
        if key in seen and seen[key]!=c:raise ValueError('conflicting_snapshot_identity')
        seen[key]=c
    return result
