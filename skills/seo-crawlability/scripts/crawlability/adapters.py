"""Read-only evidence inputs. Hashes attest local bytes, not independent provenance."""
import hashlib
import json
import sqlite3
from pathlib import Path
from urllib.parse import urljoin
from .common import header_pairs, moment, origin, url_id

SAFE_HEADERS={'content-type','content-length','content-encoding','location','etag','last-modified',
    'cache-control','retry-after','x-robots-tag','date','cf-ray','x-request-id','x-correlation-id','link','refresh'}

def read_body(evidence,base):
    if not isinstance(evidence,dict):return None,'evidence_missing'
    try:
        path=Path(evidence['path'])
        if not path.is_absolute():path=base/path
        path=path.resolve()
        if not path.is_relative_to(base.resolve()):return None,'evidence_outside_root'
        if path.stat().st_size>8_000_000:return None,'evidence_size_limit'
        data=path.read_bytes()
        if len(data)!=evidence['bytes'] or hashlib.sha256(data).hexdigest()!=evidence['sha256']:
            return None,'evidence_integrity_mismatch'
        return data,None
    except (OSError,KeyError,TypeError,ValueError):return None,'evidence_unreadable'

def clean(row,base,gaps):
    url=url_id(row['url']);moment(row['checked_at'])
    status=row.get('status')
    if status is not None and (type(status) is not int or not 100<=status<=599):raise ValueError('invalid_http_status')
    original=row.get('headers',{})
    pairs=[(k,v) for k,v in header_pairs(original) if k in SAFE_HEADERS]
    record={k:row[k] for k in ('status','error','evidence','checked_at','environment','request_id','capture_id','run_id','mode') if k in row}
    record.update({'url':url,'status':status,'headers':pairs,
        'header_capture_complete':isinstance(original,list) and row.get('header_capture_complete',True) is True})
    record['captured_header_names']=row.get('captured_header_names')
    identifiers=[v for k,v in pairs if k in {'cf-ray','x-request-id','x-correlation-id'}]
    if identifiers and not record.get('request_id'):record['request_id']=identifiers[0]
    if status is not None and not row.get('error'):
        body,reason=read_body(row.get('evidence'),base)
        if reason:
            record['evidence_error']=reason;gaps.append({'url':url,'checked_at':row['checked_at'],'reason':reason})
        else:record['body']=body
    return record

def load_manifest(path):
    path=Path(path).resolve();data=json.loads(path.read_text(encoding='utf-8'))
    if data.get('schema_version')!=1:raise ValueError('unsupported_manifest_version')
    result={'records':[],'rendered':[],'observations':[],'gaps':[]}
    for kind in ('records','rendered'):
        for row in data.get(kind,[]):result[kind].append(clean(row,path.parent,result['gaps']))
    for row in data.get('observations',[]):
        if not all(row.get(k) for k in ('engine','kind','source','checked_at','url')):raise ValueError('observation_provenance_required')
        moment(row['checked_at']);url_id(row['url'])
        result['observations'].append(dict(row))
    return result

def load_inventory(path,urls):
    path=Path(path).resolve()
    if not path.is_file():raise FileNotFoundError(path)
    db=sqlite3.connect(path.as_uri()+'?mode=ro');db.row_factory=sqlite3.Row
    try:
        version=db.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()
        if not version or version[0]!='1':raise ValueError('unsupported_inventory_version')
        rows=[dict(row) for row in db.execute('SELECT * FROM fetches ORDER BY checked_at,id')]
    finally:db.close()
    decoded=[]
    for row in rows:
        row['headers']=json.loads(row['headers_all']) if row.get('headers_all') is not None else json.loads(row.get('headers') or '{}')
        row['evidence']=json.loads(row.get('evidence') or 'null')
        row['header_capture_complete']=row.get('headers_all') is not None
        row['captured_header_names']=json.loads(row['captured_header_names']) if row.get('captured_header_names') is not None else None
        row['environment']='001-inventory:'+str(path)
        row['capture_id']=str(row['run_id'])+':'+str(row['id'])
        decoded.append(row)
    wanted={url_id(u) for u in urls};wanted|={origin(u)+'/robots.txt' for u in wanted}
    # Include all observed redirect edges inside the bounded chain, plus every target's robots.
    # No network is performed; outside-scope targets remain explicit evidence gaps.
    for _ in range(6):
        added=set()
        for row in decoded:
            if url_id(row['url']) not in wanted or row.get('status') not in {301,302,303,307,308}:continue
            for key,value in header_pairs(row['headers']):
                if key=='location':
                    try:added.add(url_id(urljoin(row['url'],value)))
                    except (ValueError,UnicodeError):pass
        added|={origin(u)+'/robots.txt' for u in added}
        if added<=wanted:break
        wanted|=added
    result={'records':[],'rendered':[],'observations':[],'gaps':[]}
    for row in decoded:
        if url_id(row['url']) in wanted:result['records'].append(clean(row,path.parent,result['gaps']))
    return result
