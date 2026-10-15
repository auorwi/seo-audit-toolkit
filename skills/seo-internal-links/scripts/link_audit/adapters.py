"""Load immutable HTML and observation files; preserve failed latest attempts."""
import json
from pathlib import Path
from .shared import url_id,moment
from .extract import extract_links
from crawlability.adapters import read_body

def load_manifest(path):
    path=Path(path).resolve();data=json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(data,dict) or data.get('schema_version')!=1:raise ValueError('unsupported_manifest_version')
    for key in ['captures','http_records','assets','pagination','language_expectations']:
        if not isinstance(data.get(key,[]),list):raise ValueError(key+'_array_required')
    if not isinstance(data.get('seeds',{}),dict):raise ValueError('seeds_object_required')
    result={'captures':[],'http_records':[],'assets':data.get('assets',[]),'seeds':data.get('seeds',{}),'pagination':[],'language_expectations':[],'gaps':[]}
    def body(proof):
        value,error=read_body(proof,path.parent)
        if error:raise ValueError(error)
        return value
    def obj(proof):
        value=json.loads(body(proof))
        if not isinstance(value,dict):raise ValueError('evidence_object_required')
        return value
    for row in data.get('captures',[]):
        if not isinstance(row,dict):raise ValueError('capture_object_required')
        meta={k:row[k] for k in ['url','snapshot_id','captured_at','source','representation','document_sha256','entry_mode','discovery_mode','requested_url','state','evidence'] if k in row};meta['manifest_path']=str(path)
        try:
            url_id(row['url']);moment(row['captured_at'])
            if not row.get('snapshot_id') or not row.get('source') or row.get('representation') not in {'initial_html','rendered_html'}:raise ValueError('capture_provenance_required')
            if row.get('state','completed')!='completed':result['captures'].append(meta);continue
            ready=row.get('readiness')
            if row['representation']=='rendered_html' and ready not in {'ready','pending','unknown_timeout','page_error'}:raise ValueError('rendered_readiness_required')
            raw=body(row.get('evidence'))
            if row.get('document_sha256')!=row['evidence']['sha256']:raise ValueError('document_hash_mismatch')
            parsed=extract_links(raw.decode('utf-8',errors='replace'),row['url']);c={**meta,'readiness':ready,'state':'completed','links':parsed['links'],'controls':parsed['controls'],'html_lang':parsed['html_lang'],'base_url':parsed['base_url']}
            result['gaps'] += [{'url':row['url'],'kind':'html_extraction',**g} for g in parsed['gaps']]
            if row.get('browser_evidence'):
                try:
                    b=obj(row['browser_evidence'])
                    if not b.get('source') or any(b.get(k)!=c.get(k) for k in ['url','snapshot_id','document_sha256','captured_at']):raise ValueError('browser_document_binding')
                    if not isinstance(b.get('links',[]),list):raise ValueError('browser_links_array_required')
                    for observation in b.get('links',[]):
                        if not isinstance(observation,dict):raise ValueError('browser_link_object_required')
                        candidates=[link for link in c['links'] if link['locator']==observation.get('locator') and link['href']==observation.get('href')]
                        if len(candidates)!=1 or not isinstance(observation.get('visible'),bool):result['gaps'].append({'url':row['url'],'kind':'browser_link','reason':'browser_link_binding','observation':observation});continue
                        candidates[0]['visibility']='visible' if observation['visible'] else 'hidden';candidates[0]['browser_inner_text']=observation.get('inner_text');candidates[0]['browser_evidence']=row['browser_evidence']
                    items=b.get('item_keys')
                    if isinstance(items,list) and all(isinstance(x,str) for x in items):c['item_keys']=items
                    c['browser_evidence']=row['browser_evidence']
                except (ValueError,KeyError,TypeError,UnicodeError) as error:result['gaps'].append({'url':row['url'],'kind':'browser','reason':str(error)})
            result['captures'].append(c)
        except (ValueError,KeyError,TypeError,UnicodeError) as error:
            result['gaps'].append({'url':row.get('url'),'kind':'capture','reason':str(error)})
            try:
                url_id(row['url']);moment(row['captured_at'])
                if row.get('snapshot_id') and row.get('representation'):result['captures'].append({**meta,'state':'evidence_error','error':str(error)})
            except (ValueError,KeyError,TypeError):pass
    for row in data.get('http_records',[]):
        if not isinstance(row,dict):raise ValueError('http_record_object_required')
        url_id(row['url']);moment(row['checked_at']);c={**row,'manifest_path':str(path)}
        if not row.get('error') and row.get('state','completed')=='completed':
            try:
                body(row.get('evidence'))
                if row.get('evidence_kind')=='actual_response_metadata':
                    saved=obj(row['evidence'])
                    if any(saved.get(k)!=row.get(k) for k in ['url','status','method','headers','checked_at','source','state']):raise ValueError('http_metadata_binding')
            except ValueError as error:c['evidence_error']=str(error);result['gaps'].append({'url':row['url'],'kind':'http','reason':str(error)})
        result['http_records'].append(c)
    for row in data.get('pagination',[]):
        try:
            if not isinstance(row,dict):raise ValueError('pagination_object_required')
            result['pagination'].append({**row,'action':obj(row.get('action_evidence')),'manifest_path':str(path)})
        except (ValueError,KeyError,TypeError,UnicodeError) as error:result['gaps'].append({'kind':'pagination','reason':str(error)})
    for proof in data.get('language_expectations',[]):
        try:result['language_expectations'].append({**obj(proof),'mapping_evidence':proof,'manifest_path':str(path)})
        except (ValueError,KeyError,TypeError,UnicodeError) as error:result['gaps'].append({'kind':'language_expectation','reason':str(error)})
    return result
