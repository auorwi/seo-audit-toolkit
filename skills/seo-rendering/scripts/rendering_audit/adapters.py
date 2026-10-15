"""Verified local snapshots, with capture provenance kept outside inferred content."""
import json
from pathlib import Path
from .shared import moment,url_id
from .snapshots import extract_html,normalize_dom
from crawlability.adapters import read_body

META=('id','url','requested_url','stage','entry_mode','navigation_id','source','captured_at')
EXTRA=('phase_id','navigation_started_at','environment','http_status','evidence','kind','baseline_relation')

def snapshot(row,root,gaps):
    locator=row.get('url')
    body,reason=read_body(row.get('evidence'),root)
    if reason:
        gaps.append({'url':locator,'id':row.get('id'),'reason':reason});return None
    try:
        if any(not isinstance(row.get(k),str) or not row[k].strip() for k in META):raise ValueError('snapshot_provenance_required')
        moment(row['captured_at']);url_id(row['url']);url_id(row['requested_url'])
        if row['entry_mode'] not in {'direct','internal','back'}:raise ValueError('invalid_entry_mode')
        if row['stage'] not in {'initial','dom','interaction'}:raise ValueError('invalid_snapshot_stage')
        kind=row['kind']
        if kind=='initial_html':
            if row['stage']!='initial':raise ValueError('initial_html_is_not_browser_execution')
            fields=extract_html(body.decode('utf-8',errors='replace'),row['url'])
        elif kind=='rendered_html':
            if row['stage']=='initial':raise ValueError('rendered_html_is_not_initial_response')
            fields=extract_html(body.decode('utf-8',errors='replace'),row['url'])
            fields.update({'representation':'rendered_html','full_dom':True})
        elif kind=='dom_fields':
            if row['stage']=='initial':raise ValueError('dom_fields_are_not_initial_response')
            payload=json.loads(body)
            if not isinstance(payload,dict):raise ValueError('dom_capture_must_be_object')
            if any(payload.get(key)!=row[key] for key in META):raise ValueError('dom_capture_provenance_mismatch')
            for key in ('phase_id','navigation_started_at','environment','http_status'):
                if (key in payload)!=(key in row) or payload.get(key)!=row.get(key):
                    raise ValueError('dom_capture_context_mismatch')
            fields=normalize_dom(payload)
        else:raise ValueError('unsupported_snapshot_kind')
        return {**fields,**{k:row[k] for k in META+EXTRA if k in row}}
    except (ValueError,KeyError,TypeError,UnicodeError) as error:
        gaps.append({'url':locator,'id':row.get('id'),'reason':str(error)});return None

def interaction(row,root,gaps):
    body,reason=read_body(row.get('evidence'),root)
    if reason:gaps.append({'url':row.get('url'),'id':row.get('id'),'reason':reason});return None
    try:
        for key in ('id','url','kind','before_id','after_id','source','checked_at'):
            if not row.get(key):raise ValueError('interaction_provenance_required')
        url_id(row['url']);moment(row['checked_at'])
        saved=json.loads(body)
        if not isinstance(saved,dict) or any(saved.get(key)!=value for key,value in row.items() if key!='evidence'):
            raise ValueError('interaction_capture_mismatch')
        return dict(row)
    except (ValueError,TypeError,KeyError,UnicodeError) as error:
        gaps.append({'url':row.get('url'),'id':row.get('id'),'reason':str(error)});return None

def load_manifest(path):
    path=Path(path).resolve();data=json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(data,dict) or data.get('schema_version')!=1:raise ValueError('unsupported_manifest_version')
    gaps=data.get('gaps',[])
    if not isinstance(gaps,list) or not all(isinstance(gap,dict) for gap in gaps):raise ValueError('invalid_gap_list')
    result={'snapshots':[],'interactions':[],'gaps':list(gaps)}
    for key,reader in [('snapshots',snapshot),('interactions',interaction)]:
        rows=data.get(key,[])
        if not isinstance(rows,list) or not all(isinstance(row,dict) for row in rows):raise ValueError('invalid_record_list')
        for row in rows:
            parsed=reader(row,path.parent,result['gaps'])
            if parsed is not None:result[key].append(parsed)
    return result
