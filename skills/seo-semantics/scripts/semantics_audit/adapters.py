"""Load locally verified checker and element evidence without inventing provenance."""
import json
from pathlib import Path
from .shared import moment,url_id
from .elements import parse_html
from crawlability.adapters import read_body

def load_manifest(path):
    path=Path(path).resolve();data=json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(data,dict) or data.get('schema_version')!=1:raise ValueError('unsupported_manifest_version')
    result={'captures':[],'tool_reports':[],'gaps':[]}
    for group in ('captures','tool_reports'):
        rows=data.get(group,[])
        if not isinstance(rows,list) or not all(isinstance(row,dict) for row in rows):raise ValueError('invalid_manifest_rows')
        for row in rows:
            try:
                body,error=read_body(row.get('evidence'),path.parent)
                if error:raise ValueError(error)
                url_id(row['url'])
                time_key='captured_at' if group=='captures' else 'checked_at'
                moment(row[time_key])
                if group=='captures' and row.get('kind')=='initial_html':
                    if not row.get('source') or not row.get('snapshot_id'):raise ValueError('source_provenance_required')
                    parsed=parse_html(body.decode('utf-8',errors='replace'),row['url'])
                    parsed.update({k:row[k] for k in ('snapshot_id','captured_at','source')})
                    parsed.update({'document_sha256':row['evidence']['sha256'],'readiness':None,'scope':'document','evidence':row['evidence']})
                else:
                    parsed=json.loads(body)
                    if not isinstance(parsed,dict):raise ValueError('capture_object_required')
                    required=('url','snapshot_id','captured_at','source') if group=='captures' else ('tool','url','capture_id','checked_at')
                    if any(not row.get(key) or parsed.get(key)!=row[key] for key in required):raise ValueError('capture_provenance_mismatch')
                    for key,value in row.items():
                        if key not in {'kind','evidence','document_evidence'} and key in parsed and parsed[key]!=value:raise ValueError('capture_metadata_mismatch')
                    document,error=read_body(row.get('document_evidence'),path.parent)
                    if error:raise ValueError('document_'+error)
                    if parsed.get('document_sha256')!=row['document_evidence']['sha256']:raise ValueError('document_capture_binding_mismatch')
                    if group=='captures' and (row.get('kind')!='rendered_elements' or parsed.get('representation')!='rendered_elements' or not isinstance(parsed.get('nodes'),list)):
                        raise ValueError('rendered_elements_required')
                    parsed.update({'evidence':row['evidence'],'document_evidence':row['document_evidence']})
                result[group].append(parsed)
            except (ValueError,KeyError,TypeError,UnicodeError) as error:
                result['gaps'].append({'url':row.get('url'),'kind':group,'reason':str(error)})
    return result
