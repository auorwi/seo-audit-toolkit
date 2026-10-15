"""Bind a disclosed human/Codex visual review to the actual LHR screenshot.

The binding proves the reviewed capture identity, not the truth of a visual claim.
A final screenshot cannot establish that loading was free of skeletons or shifts.
"""
import base64,binascii,hashlib
from .shared import url_id,moment

def apply_review(run,lhr,review):
    if not isinstance(review,dict):raise ValueError('page_review_object_required')
    if review.get('run_id')!=run.get('run_id') or review.get('lhr_sha256')!=run.get('evidence',{}).get('sha256'):raise ValueError('page_review_measurement_binding')
    if any(url_id(review.get(key,''))!=url_id(run.get(key,'')) for key in ['requested_url','final_url']):raise ValueError('page_review_url_binding')
    if review.get('status') not in {'valid','invalid','inconclusive'}:raise ValueError('page_review_status_invalid')
    if review.get('method') not in {'codex_screenshot_review','human_screenshot_review'}:raise ValueError('page_review_method_unsupported')
    if any(not isinstance(review.get(key),str) or not review[key].strip() for key in ['reviewer','expected_content','visible_evidence','reason']):raise ValueError('page_review_details_required')
    if moment(review['reviewed_at'])<moment(run.get('attempt_finished_at') or run['fetched_at']):raise ValueError('page_review_precedes_measurement')
    data=lhr.get('fullPageScreenshot',{}).get('screenshot',{}).get('data')
    try:
        prefix,encoded=data.split(',',1)
        if not prefix.startswith('data:image/') or not prefix.endswith(';base64'):raise ValueError()
        image=base64.b64decode(encoded,validate=True)
    except (AttributeError,ValueError,binascii.Error):raise ValueError('page_review_screenshot_unavailable')
    if not image or hashlib.sha256(image).hexdigest()!=review.get('screenshot_sha256'):raise ValueError('page_review_screenshot_binding')
    result={**run,'page_content_validity':'reviewed_'+review['status'],'page_review':review,'before_page_review':{'valid_measurement':run.get('valid_measurement',False),'exclusion':run.get('exclusion')}}
    if review['status']=='invalid':result.update(valid_measurement=False,exclusion='business_page_invalid')
    return result
