"""Import immutable LHR and field API responses with their actual collection metadata."""
import json
from pathlib import Path
from .shared import url_id,moment
from .lab import parse_lhr
from .field import parse_crux,parse_psi
from .diagnostics import diagnose_lhr
from .reviews import apply_review
from .environment import assess_load
from crawlability.adapters import read_body

def load_manifest(path):
    path=Path(path).resolve();data=json.loads(path.read_text())
    if not isinstance(data,dict) or data.get('schema_version')!=1:raise ValueError('unsupported_manifest_version')
    for key in ['lab_runs','field_records','expected_cells','field_attempts','page_reviews','collection_events']:
        if not isinstance(data.get(key,[]),list):raise ValueError(key+'_array_required')
    result={'lab_runs':[],'field_records':[],'expected_cells':data.get('expected_cells',[]),'field_attempts':[],'collection_events':[],'gaps':[]}
    def obj(proof):
        raw,error=read_body(proof,path.parent)
        if error:raise ValueError(error)
        value=json.loads(raw)
        if not isinstance(value,dict):raise ValueError('evidence_object_required')
        return value
    for proof in data.get('collection_events',[]):
        try:
            value=obj(proof);moment(value['observed_at'])
            if value.get('source')!='host_preflight':raise ValueError('unsupported_collection_event_source')
            q=value['quality'];quality=assess_load(q.get('load_before'),q.get('load_after'),q.get('cpu_count'))
            result['collection_events'].append({**value,'quality':quality,'evidence':proof,'manifest_path':str(path)})
            if not quality['suitable_for_regression']:result['gaps'].append({'reason':'collection_paused_'+quality['status'],'evidence':proof,'manifest_path':str(path)})
        except (ValueError,KeyError,TypeError,AttributeError) as e:result['gaps'].append({'reason':str(e),'kind':'collection_event'})
    reviews={};used_reviews=set()
    for proof in data.get('page_reviews',[]):
        try:
            value=obj(proof);identity=value.get('run_id')
            if not isinstance(identity,str) or not identity:raise ValueError('page_review_run_id_required')
            items=reviews.setdefault(identity,[])
            if not any(p['sha256']==proof['sha256'] for v,p in items):items.append((value,proof))
        except (ValueError,KeyError,TypeError) as e:result['gaps'].append({'reason':str(e),'kind':'page_review_input'})
    for row in data.get('lab_runs',[]):
        failure={'run_id':row.get('run_id') if isinstance(row,dict) else None,'source':'lighthouse','valid_measurement':False,'comparable':False,'metrics':{},'manifest_path':str(path)}
        try:
            if not isinstance(row,dict):raise ValueError('lab_run_object_required')
            saved=obj(row.get('attempt_evidence'))
            if not saved.get('source') or any(saved.get(k)!=row.get(k) for k in ['run_id','url','state','started_at','finished_at']):raise ValueError('attempt_metadata_binding')
            failure.update(requested_url=saved.get('url'),state=saved.get('state'),attempt_evidence=row['attempt_evidence'],error=saved.get('error'))
            if saved['state']!='completed':result['lab_runs'].append(failure);result['gaps'].append({'run_id':row.get('run_id'),'reason':'attempt_'+saved['state']});continue
            cell=obj(row.get('context_evidence'));matches=[a for a in cell.get('attempts',[]) if a.get('run_id')==row['run_id']]
            if len(matches)!=1 or matches[0].get('lhr_evidence',{}).get('sha256')!=row.get('lhr_evidence',{}).get('sha256'):raise ValueError('lhr_context_binding')
            raw=obj(row['lhr_evidence'])
            if not moment(saved['started_at'])<=moment(raw['fetchTime'])<=moment(saved['finished_at']):raise ValueError('lhr_attempt_time_binding')
            if url_id(raw['requestedUrl'])!=url_id(saved['url']):raise ValueError('lhr_requested_url_binding')
            run=parse_lhr(raw,cell['context']);run.update(run_id=row['run_id'],state='completed',evidence=row['lhr_evidence'],attempt_evidence=row['attempt_evidence'],context_evidence=row['context_evidence'],manifest_path=str(path),diagnostics=diagnose_lhr(raw),attempt_finished_at=saved['finished_at'],collection_load={'before':cell.get('load_before'),'after':cell.get('load_after'),'cpu_count':cell.get('cpu_count')})
            run['environment_quality']=assess_load(cell.get('load_before'),cell.get('load_after'),cell.get('cpu_count'))
            if row['run_id'] in reviews:
                used_reviews.add(row['run_id']);items=reviews[row['run_id']]
                try:
                    if len(items)!=1:raise ValueError('page_review_conflict')
                    review,proof=items[0];run=apply_review(run,raw,review);run['page_review_evidence']=proof
                except (ValueError,KeyError,TypeError,AttributeError) as e:result['gaps'].append({'reason':str(e),'run_id':row['run_id'],'kind':'page_review_input'})
            result['lab_runs'].append(run)
        except (ValueError,KeyError,TypeError,AttributeError) as e:
            failure['error']=str(e);result['lab_runs'].append(failure);result['gaps'].append({'run_id':failure['run_id'],'reason':str(e)})
    result['gaps'] += [{'reason':'page_review_measurement_missing','run_id':identity} for identity in reviews if identity not in used_reviews]
    for row in data.get('field_records',[]):
        try:
            if not isinstance(row,dict):raise ValueError('field_record_object_required')
            q=obj(row.get('query_evidence'))
            if q.get('source')!=row.get('source'):raise ValueError('query_source_binding')
            raw=obj(row.get('evidence'));moment(q['observed_at'])
            if row['source']=='crux_api':records=[parse_crux(raw,q['request'],observed_at=q['observed_at'])]
            elif row['source']=='psi_api':
                parsed=parse_psi(raw,q['request'],observed_at=q['observed_at']);records=parsed['records'] or [parsed];result['gaps'] += [{'reason':g,'source':'psi_api'} for g in parsed['gaps']]
            else:raise ValueError('unknown_field_source')
            for record in records:
                if record.get('status')=='observed' and (type(q.get('status')) is not int or not 200<=q['status']<300):record={**record,'status':'unverified','gaps':record.get('gaps',[])+['field_http_status_not_success']}
                result['field_records'].append({**record,'evidence':row['evidence'],'query_evidence':row['query_evidence'],'http_status':q.get('status'),'manifest_path':str(path)})
        except (ValueError,KeyError,TypeError,AttributeError) as e:result['gaps'].append({'reason':str(e),'kind':'field_input'})
    for proof in data.get('field_attempts',[]):
        try:
            attempt=obj(proof);moment(attempt['observed_at'])
            result['field_attempts'].append({**attempt,'evidence':proof,'manifest_path':str(path)})
            if attempt.get('state')!='response_received':result['gaps'].append({'reason':'field_'+str(attempt.get('state','unknown')),'source':attempt.get('source'),'request':attempt.get('request'),'evidence':proof,'manifest_path':str(path)})
        except (ValueError,KeyError,TypeError) as e:result['gaps'].append({'reason':'field_attempt_'+str(e)})
    for cell in result['expected_cells']:
        url_id(cell['url'])
        if cell.get('device') not in {'mobile','desktop'}:raise ValueError('invalid_expected_device')
        if cell.get('minimum_valid_runs',3)!=3:raise ValueError('expected_three_valid_runs')
    return result
