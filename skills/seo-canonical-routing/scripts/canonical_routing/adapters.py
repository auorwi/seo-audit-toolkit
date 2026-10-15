"""Canonical target closure and independently recorded semantic/browser evidence."""
import json
from pathlib import Path
from .shared import url_id,moment
from .declarations import parse
from .audit import document
from crawlability import adapters as evidence_adapter
from crawlability.responses import latest_records

EXTENSIONS=('facts','navigation','equivalences','engine_observations')

def blank(base):
    return {'records':base['records'],'rendered':base['rendered'],'gaps':base['gaps'],**{k:[] for k in EXTENSIONS}}

def extension(row,kind,root,gaps):
    location=row.get('url') or row.get('from_url') or row.get('source_url')
    body,reason=evidence_adapter.read_body(row.get('evidence'),root)
    if reason:
        gaps.append({'url':location,'kind':kind,'reason':reason});return None
    try:
        if not isinstance(row.get('source'),str) or not row['source'].strip():raise ValueError('source_required')
        moment(row['checked_at'])
        output=dict(row)
        if kind=='facts':
            output['url']=url_id(row['url'])
            if not row.get('selector') or not row.get('quote') or row['quote'] not in body.decode('utf-8',errors='replace'):
                raise ValueError('fact_quote_or_locator_unverified')
            if not any(row.get(k) for k in ('entity','language','role')):raise ValueError('fact_value_required')
            output['evidence_verification']='hash_and_quote'
        elif kind=='navigation':
            output['from_url']=url_id(row['from_url']);output['to_url']=url_id(row['to_url'])
            if row.get('entry_mode') not in {'direct','internal','back','other'}:raise ValueError('entry_mode_required')
            saved=json.loads(body)
            if not isinstance(saved,dict):raise ValueError('navigation_evidence_must_be_object')
            if any(saved.get(k)!=row.get(k) for k in ('from_url','to_url','entry_mode','checked_at')):raise ValueError('navigation_evidence_mismatch')
        elif kind=='equivalences':
            output['source_url']=url_id(row['source_url']);output['target_url']=url_id(row['target_url'])
            if row.get('result') not in {'equivalent','different','unknown'}:raise ValueError('invalid_equivalence_result')
            if not row.get('source_sha256') or not row.get('target_sha256'):raise ValueError('page_hashes_required')
            saved=json.loads(body)
            if not isinstance(saved,dict):raise ValueError('equivalence_evidence_must_be_object')
            if any(saved.get(k)!=row.get(k) for k in ('source_url','target_url','result','source_sha256','target_sha256','checked_at')):raise ValueError('equivalence_evidence_mismatch')
        else:
            output['url']=url_id(row['url']);output['canonical']=url_id(row['canonical'])
            if not row.get('engine') or not row.get('kind'):raise ValueError('engine_snapshot_provenance_required')
        return output
    except (ValueError,KeyError,TypeError,UnicodeError) as error:
        gaps.append({'url':location,'kind':kind,'reason':str(error)});return None

def load_manifest(path):
    path=Path(path).resolve();raw=json.loads(path.read_text(encoding='utf-8'))
    result=blank(evidence_adapter.load_manifest(path))
    for kind in EXTENSIONS:
        candidates=raw.get(kind,[])
        if kind=='engine_observations':candidates=candidates+[o for o in raw.get('observations',[]) if o.get('canonical')]
        for row in candidates:
            item=extension(row,kind,path.parent,result['gaps'])
            if item is not None:result[kind].append(item)
    return result

def load_inventory(path,urls,max_graph_depth=30):
    if type(max_graph_depth) is not int or max_graph_depth<0:raise ValueError('invalid_graph_depth')
    wanted={url_id(url) for url in urls}
    for depth in range(max_graph_depth+1):
        base=evidence_adapter.load_inventory(path,sorted(wanted));found=set()
        for url,row in latest_records(base['records']).items():
            if row.get('error') or type(row.get('status')) is not int or not 200<=row['status']<300 or not isinstance(row.get('body'),bytes):continue
            declarations=parse(document(row),row.get('headers',[]),url)
            found.update(declarations['targets'])
            found.update(r['target'] for r in declarations['refreshes'])
        if found<=wanted:break
        if depth==max_graph_depth:
            base['gaps'].append({'reason':'canonical_input_closure_limit','urls':sorted(found-wanted)});break
        wanted|=found
    return blank(base)
