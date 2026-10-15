"""Accept evidence bytes and purpose reviews bound to the entire immutable capture."""
import hashlib,json
from pathlib import Path
from .shared import moment,fresh,url_id
from .extract import extract_html
from .rules import PURPOSES
from crawlability.adapters import read_body

def load_manifest(path,*,at,max_age_hours=24):
    moment(at);fresh(at,at,max_age_hours);path=Path(path).resolve()
    def decode(raw):return json.loads(raw,parse_constant=lambda v:(_ for _ in ()).throw(ValueError('nonfinite_json')))
    data=decode(path.read_bytes())
    if not isinstance(data,dict) or data.get('schema_version')!=1:raise ValueError('unsupported_manifest_version')
    for key in ('scope','captures','reviews'):
        if not isinstance(data.get(key,[]),list):raise ValueError(key+'_array_required')
    if not data.get('scope'):raise ValueError('scope_required')
    for s in data['scope']:
        url_id(s['url'])
        if not isinstance(s.get('devices'),list) or not s['devices'] or any(d not in {'desktop','mobile'} for d in s['devices']):raise ValueError('invalid_scope_device')
    result={'scope':data['scope'],'captures':[],'reviews':{},'gaps':[]};captures={};proofs={};poisoned=set()
    def obj(proof):
        raw,error=read_body(proof,path.parent)
        if error:raise ValueError(error)
        value=decode(raw)
        if not isinstance(value,dict):raise ValueError('evidence_object_required')
        return value
    for proof in data.get('captures',[]):
        sid=None
        try:
            c=obj(proof);sid=c['snapshot_id']
            if not isinstance(sid,str) or not sid.strip():raise ValueError('snapshot_id_required')
            if sid in captures or sid in poisoned:
                poisoned.add(sid);captures.pop(sid,None);raise ValueError('duplicate_snapshot_id')
            for key in ('url','requested_url'):url_id(c[key])
            if c.get('device') not in {'desktop','mobile'}:raise ValueError('invalid_capture_device')
            if not fresh(c.get('captured_at'),at,max_age_hours):raise ValueError('stale_capture')
            if not isinstance(c.get('html'),str) or hashlib.sha256(c['html'].encode()).hexdigest()!=c.get('document_sha256'):raise ValueError('html_hash_mismatch')
            if not isinstance(c.get('media'),list) or not isinstance(c.get('responses',[]),list):raise ValueError('capture_arrays_required')
            slots=set()
            for row in c['media']:
                if not isinstance(row,dict) or not isinstance(row.get('slot'),str) or not row['slot'] or row['slot'] in slots:raise ValueError('invalid_or_duplicate_media_slot')
                slots.add(row['slot'])
                if row.get('captured_at')!=c['captured_at']:raise ValueError('observation_time_binding')
                probe=row.get('decode',{})
                if probe.get('result') not in {None,'not_attempted'}:
                    if not moment(c['captured_at'])<=moment(probe['completed_at'])<=moment(at):raise ValueError('decode_probe_time_order')
                    if probe.get('source_after_probe')!=row.get('current_src') or probe.get('current_src')!=row.get('current_src'):raise ValueError('decode_source_binding')
            c['declarations']=extract_html(c['html'],c['url']);c['capture_proof']=proof
            captures[sid]=c;proofs[sid]=proof
        except (ValueError,KeyError,TypeError,OSError) as e:
            result['gaps'].append({'snapshot_id':sid,'reason':'capture_rejected','detail':str(e)})
    bad_reviews=set()
    for proof in data.get('reviews',[]):
        sid=None
        try:
            r=obj(proof);sid=r['snapshot_id'];c=captures[sid]
            if sid in bad_reviews:raise ValueError('conflicting_reviews')
            if r.get('capture_sha256')!=proofs[sid]['sha256']:raise ValueError('review_capture_binding')
            for field in ('reviewer','method'):
                if not isinstance(r.get(field),str) or not r[field].strip():raise ValueError('review_attribution_required')
            if not moment(c['captured_at'])<=moment(r['reviewed_at'])<=moment(at):raise ValueError('review_time_order')
            capture_path=Path(proofs[sid]['path'])
            if not capture_path.is_absolute():capture_path=path.parent/capture_path
            shot=c.get('screenshot');raw,error=read_body(shot,capture_path.resolve().parent)
            if error:raise ValueError('review_screenshot_'+error)
            if r.get('screenshot_sha256')!=shot['sha256']:raise ValueError('review_screenshot_binding')
            if not isinstance(r.get('items'),list) or not r['items']:raise ValueError('review_items_required')
            slots={row['slot']:row['tag'] for row in c['media']};items={}
            for item in r['items']:
                slot=item['slot']
                if slot not in slots:raise ValueError('review_slot_absent')
                if slot in items:raise ValueError('duplicate_review_slot')
                if item.get('purpose') not in PURPOSES:raise ValueError('invalid_purpose')
                allowed={'img':{'informative','decorative','functional','unknown'},'css':{'informative','decorative','functional','unknown'},
                         'video':{'watch_video','auxiliary_video','unknown'},'iframe':{'watch_video','auxiliary_video','nonvideo_embed','unknown'},
                         'embed':{'watch_video','auxiliary_video','nonvideo_embed','unknown'},'object':{'watch_video','auxiliary_video','nonvideo_embed','unknown'}}
                if item['purpose'] not in allowed.get(slots[slot],set()):raise ValueError('purpose_tag_mismatch')
                if not isinstance(item.get('notes'),str) or not item['notes'].strip():raise ValueError('purpose_rationale_required')
                cite=item['citation'];field=cite['field'];quote=cite['quote']
                if field not in {'visible_main','entity'} or not isinstance(quote,str) or not quote.strip() or quote not in c.get(field,''):raise ValueError('review_quote_not_bound')
                for flag in ('important_initial','equivalent_img','representative_thumbnail','image_search_target'):
                    if flag in item and type(item[flag]) is not bool:raise ValueError('review_flag_must_be_boolean')
                items[slot]={**item,'reviewer':r['reviewer'],'method':r['method'],'reviewed_at':r['reviewed_at'],'capture_sha256':r['capture_sha256'],'screenshot_sha256':r['screenshot_sha256']}
            existing=result['reviews'].get(sid,{})
            if existing.keys()&items.keys():
                bad_reviews.add(sid);result['reviews'].pop(sid,None);raise ValueError('conflicting_reviews')
            result['reviews'][sid]={**existing,**items}
        except (ValueError,KeyError,TypeError,OSError) as e:result['gaps'].append({'snapshot_id':sid,'reason':'purpose_review_rejected','detail':str(e)})
    result['captures']=list(captures.values())
    return result
