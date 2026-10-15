"""Read immutable HTML, visible snapshots, native extraction and platform evidence."""
import json
from pathlib import Path
from .shared import moment,url_id
from .jsonld import extract_jsonld
from .vocabulary import build_vocabulary
from crawlability.adapters import read_body

def load_manifest(path):
    path=Path(path).resolve();data=json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(data,dict) or data.get('schema_version')!=1:raise ValueError('unsupported_manifest_version')
    result={'captures':[],'engine_reports':[],'vocabulary':None,'gaps':[]}
    def read(proof):
        body,error=read_body(proof,path.parent)
        if error:raise ValueError(error)
        return body
    def read_json(proof):
        value=json.loads(read(proof))
        if not isinstance(value,dict):raise ValueError('evidence_object_required')
        return value
    rows=data.get('captures',[])
    if not isinstance(rows,list) or not all(isinstance(r,dict) for r in rows):raise ValueError('capture_array_required')
    for row in rows:
        try:
            url_id(row['url']);moment(row['captured_at'])
            if not row.get('snapshot_id') or not row.get('source'):raise ValueError('capture_provenance_required')
            if row.get('representation') not in {'initial_html','rendered_html'}:raise ValueError('capture_representation_required')
            if row.get('state','completed')!='completed':result['captures'].append({**{k:row[k] for k in ['url','snapshot_id','captured_at','source','representation','state']},'entry_mode':row.get('entry_mode','unknown')});continue
            if row['representation']=='rendered_html' and row.get('readiness') not in {'ready','pending','unknown_timeout','page_error'}:raise ValueError('capture_readiness_required')
            body=read(row.get('evidence'))
            if row.get('document_sha256')!=row['evidence']['sha256']:raise ValueError('document_hash_mismatch')
            c={k:row[k] for k in ['url','snapshot_id','captured_at','source','representation','document_sha256','evidence']}
            c.update(state='completed',readiness=row.get('readiness'),entry_mode=row.get('entry_mode','unknown'),jsonld=extract_jsonld(body.decode('utf-8',errors='replace'),row['url']))
            for key,target in [('visible_evidence','visible'),('extraction_evidence','extruct'),('context_evidence','context')]:
                if not row.get(key):continue
                try:
                    value=read_json(row[key])
                    if target=='visible':
                        if any(value.get(k)!=c.get(k) for k in ['url','snapshot_id','captured_at','document_sha256']) or not isinstance(value.get('visible_text'),str) or not value.get('source'):raise ValueError('visible_capture_binding')
                        c['visible_text']=value['visible_text'];c['visible_evidence']=row[key]
                    else:c[target]=value;c[key]=row[key]
                except (ValueError,KeyError,TypeError,UnicodeError) as error:result['gaps'].append({'url':row['url'],'kind':target,'reason':str(error)})
            result['captures'].append(c)
        except (ValueError,KeyError,TypeError,UnicodeError) as error:
            result['gaps'].append({'url':row.get('url'),'reason':str(error)})
            try:
                url_id(row['url']);moment(row['captured_at'])
                if row.get('snapshot_id') and row.get('representation') in {'initial_html','rendered_html'}:result['captures'].append({**{k:row[k] for k in ['url','snapshot_id','captured_at','representation']},'state':'evidence_error','error':str(error),'entry_mode':row.get('entry_mode','unknown')})
            except (ValueError,KeyError,TypeError):pass
    if data.get('vocabulary'):
        try:
            row=data['vocabulary'];moment(row['retrieved_at'])
            if not isinstance(row.get('source'),str) or not row['source'].startswith('https://schema.org/'):raise ValueError('official_vocabulary_source_required')
            result['vocabulary']={**row,'terms':build_vocabulary(read_json(row.get('evidence')))}
        except (ValueError,KeyError,TypeError,UnicodeError) as error:result['gaps'].append({'kind':'vocabulary','reason':str(error)})
    engine_rows=data.get('engine_reports',[])
    if not isinstance(engine_rows,list):raise ValueError('engine_reports_array_required')
    for row in engine_rows:
        try:
            if not isinstance(row,dict):raise ValueError('engine_report_object_required')
            mapped=read_json(row.get('evidence'));read(row.get('original_evidence'))
            mapped['artifact_sha256']=row['original_evidence']['sha256'];mapped['original_evidence']=row['original_evidence'];mapped['mapping_evidence']=row['evidence'];result['engine_reports'].append(mapped)
        except (ValueError,KeyError,TypeError,UnicodeError) as error:result['gaps'].append({'kind':'engine_report','reason':str(error)})
    return result
