"""Load preserved HTML and independently verifiable context artifacts."""
import json
from pathlib import Path
from .shared import moment,url_id
from .extract import extract
from crawlability.adapters import read_body

def load_manifest(path):
    path=Path(path).resolve();data=json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(data,dict) or data.get('schema_version')!=1:raise ValueError('unsupported_manifest_version')
    rows=data.get('captures',[])
    if not isinstance(rows,list) or not all(isinstance(r,dict) for r in rows):raise ValueError('captures_array_required')
    result={'captures':[],'gaps':[]}
    for row in rows:
        try:
            url_id(row['url']);moment(row['captured_at'])
            if not row.get('source') or not row.get('snapshot_id'):raise ValueError('capture_provenance_required')
            if row.get('representation') not in {'initial_html','rendered_html'}:raise ValueError('representation_required')
            if row.get('state','completed')!='completed':
                result['captures'].append({k:row[k] for k in ['url','snapshot_id','captured_at','source','representation','state']});continue
            if row['representation']=='rendered_html' and row.get('readiness') not in {'ready','pending','unknown_timeout','page_error'}:raise ValueError('readiness_required')
            body,error=read_body(row.get('evidence'),path.parent)
            if error:raise ValueError(error)
            if row.get('document_sha256')!=row['evidence']['sha256']:raise ValueError('document_binding')
            parsed={k:row[k] for k in ['url','snapshot_id','captured_at','source','representation','document_sha256','evidence']}
            parsed.update({'readiness':row.get('readiness'),'state':'completed','fields':extract(body.decode('utf-8',errors='replace'),row['url'])})
            if row.get('context_evidence'):
                try:
                    context_bytes,error=read_body(row['context_evidence'],path.parent)
                    if error:raise ValueError(error)
                    context=json.loads(context_bytes)
                    if not isinstance(context,dict):raise ValueError('context_object_required')
                    for fact in context.get('facts',[]):
                        if fact.get('origin')!='page':
                            document,error=read_body(fact.get('document_evidence'),path.parent)
                            if error:raise ValueError('external_fact_'+error)
                            fact['document']={'text':document.decode('utf-8',errors='strict'),'sha256':fact['document_evidence']['sha256']}
                    parsed['context']=context
                except (ValueError,KeyError,TypeError,UnicodeError) as error:result['gaps'].append({'url':row['url'],'reason':'context_'+str(error)})
            result['captures'].append(parsed)
        except (ValueError,KeyError,TypeError,UnicodeError) as error:
            result['gaps'].append({'url':row.get('url'),'reason':str(error)})
            try:
                url_id(row['url']);moment(row['captured_at'])
                if row.get('snapshot_id') and row.get('representation') in {'initial_html','rendered_html'}:
                    result['captures'].append({**{k:row[k] for k in ['url','snapshot_id','captured_at','representation']},'state':'evidence_error','error':str(error)})
            except (ValueError,KeyError,TypeError):pass
    return result
