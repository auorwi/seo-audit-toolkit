"""Read-only S01 evidence bridge and explicitly validated business intent."""
import hashlib
import json
import sqlite3
from pathlib import Path
from urllib.parse import parse_qsl, urlsplit
from .xmlrules import date, identity, SENSITIVE, safe_url

def clean_details(details):
    if not isinstance(details,dict):raise ValueError('page_details_must_be_object')
    if 'noindex_observed' in details and not isinstance(details['noindex_observed'],bool):raise ValueError('page_noindex_must_be_boolean')
    if not isinstance(details.get('canonicals',[]),list) or any(not isinstance(u,str) for u in details.get('canonicals',[])):
        raise ValueError('page_canonicals_must_be_string_list')
    directives=details.get('robots_directives',{})
    if not isinstance(directives,dict) or any(not isinstance(v,list) or any(not isinstance(word,str) for word in v) for v in directives.values()):
        raise ValueError('page_robot_directives_must_be_string_lists')
    if not isinstance(details.get('headers',{}),dict) or any(not isinstance(v,str) for v in details.get('headers',{}).values()):
        raise ValueError('page_headers_must_be_string_values')
    fields={'noindex_observed','robots_directives','canonicals','content_verdict','title','body_mode','evidence'}
    result={k:v for k,v in details.items() if k in fields}
    result['headers']={k.lower():safe_url(v) if k.lower()=='location' else v for k,v in details.get('headers',{}).items()
        if k.lower() in {'location','x-robots-tag','content-type','last-modified','date','retry-after'}}
    result['canonicals']=[safe_url(u) if any(k.lower() in SENSITIVE for k,v in parse_qsl(urlsplit(u).query,keep_blank_values=True)) else u for u in result.get('canonicals',[])]
    return result

def validate_expected(data):
    if not isinstance(data,dict) or not isinstance(data.get('rows'),list) or not data.get('source_id'):
        raise ValueError('expected_requires_source_and_rows')
    if data.get('coverage') not in {'complete','sample','unknown'}:
        raise ValueError('expected_requires_coverage')
    date(data.get('captured_at'))
    if not isinstance(data.get('scope_roots',[]),list):raise ValueError('expected_scope_roots_must_be_list')
    for url in data.get('scope_roots',[]):identity(url)
    seen={}
    for row in data['rows']:
        if not isinstance(row,dict):raise ValueError('expected_row_must_be_object')
        url=identity(row.get('url'))
        for field in ('published','should_index','retired'):
            if field in row and not isinstance(row[field],bool):raise ValueError('expected_flags_must_be_boolean')
        for field in ('url','canonical_url'):
            if field in row:
                p=urlsplit(identity(row[field]))
                if any(k.lower() in SENSITIVE for k,v in parse_qsl(p.query,keep_blank_values=True)):
                    raise ValueError('sensitive_expected_url')
        if row.get('modified_at'):date(row['modified_at'])
        if url in seen and row!=seen[url]:raise ValueError('conflicting_expected_rows')
        seen[url]=row
    return {**data,'rows':list(seen.values())}

def verified_body(evidence, directory):
    if not isinstance(evidence,dict) or not all(k in evidence for k in ('path','sha256','bytes')):
        raise ValueError('evidence_metadata_missing')
    path=Path(evidence['path']).resolve()
    if not path.is_relative_to(directory.resolve()):raise ValueError('evidence_path_outside_inventory')
    if path.stat().st_size>60_000_000:raise ValueError('evidence_local_read_limit')
    body=path.read_bytes()
    if len(body)!=evidence['bytes'] or hashlib.sha256(body).hexdigest()!=evidence['sha256']:
        raise ValueError('evidence_hash_mismatch')
    return body

def from_inventory(path):
    path=Path(path).resolve()
    if not path.is_file():raise ValueError('inventory_missing')
    db=sqlite3.connect(path.as_uri()+'?mode=ro',uri=True)
    db.row_factory=sqlite3.Row
    try:
        db.execute('BEGIN')
        version=db.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()
        if not version or version[0]!='1':raise ValueError('unsupported_inventory_schema')
        sitemap_urls={r[0] for r in db.execute("SELECT DISTINCT url FROM tasks WHERE kind='sitemap'")}
        latest={}
        for row in db.execute('SELECT * FROM fetches ORDER BY checked_at,id'):
            latest[row['url']]=dict(row)
        documents=[]; pages={}
        for url,row in latest.items():
            source={'url':url,'status':row['status'],'checked_at':row['checked_at'],'error':row['error']}
            source['evidence']=json.loads(row['evidence']) if row['evidence'] else None
            headers=json.loads(row['headers']) if row['headers'] else {}
            if not source['error'] and source['status'] is not None:
                try:source['body']=verified_body(source['evidence'],path.parent)
                except (ValueError,OSError) as e:source['error']=str(e) if isinstance(e,ValueError) else 'evidence_file_unavailable'
            if url in sitemap_urls:
                documents.append(source)
            elif not urlsplit(url).path.endswith('/robots.txt'):
                check=db.execute('SELECT * FROM checks WHERE url=? AND run_id=? ORDER BY checked_at DESC,id DESC LIMIT 1',(url,row['run_id'])).fetchone()
                details=json.loads(check['details']) if check else {}
                if not check or check['status']!=row['status'] or details.get('evidence')!=source['evidence']:
                    details={}
                source['details']=clean_details({**details,'headers':headers})
                source.pop('body',None)
                pages[url]=source
        return {'documents':documents,'pages':pages,'inventory_path':str(path)}
    finally:
        db.close()

def from_manifest(path):
    path=Path(path).resolve()
    data=json.loads(path.read_text(encoding='utf-8-sig'))
    if not isinstance(data,dict) or not isinstance(data.get('documents'),list) or not isinstance(data.get('pages',{}),dict):
        raise ValueError('evidence_manifest_requires_documents_and_pages')
    for doc in data['documents']:
        identity(doc['url']);date(doc['checked_at'])
        if not doc.get('error') and doc.get('status') is not None:
            try:doc['body']=verified_body(doc.get('evidence'),path.parent)
            except (ValueError,OSError) as e:doc['error']=str(e) if isinstance(e,ValueError) else 'evidence_file_unavailable'
    for url,page in data.get('pages',{}).items():
        identity(url);date(page['checked_at'])
        page['details']=clean_details(page.get('details',{}))
        if not page.get('error') and page.get('status') is not None:
            try:verified_body(page.get('evidence'),path.parent)
            except (ValueError,OSError) as e:page['error']=str(e) if isinstance(e,ValueError) else 'evidence_file_unavailable'
    return data
