"""Keep fact-backed editorial drafts separate from automated observations."""
import re
from .shared import fresh
from .context import normalized,contains

def review_drafts(capture,validated,*,rewrite_blocked,at,max_age_hours=168):
    result={'drafts':[],'withheld':[],'gaps':[],'pending':['search_intent','language_and_wording']}
    meta=validated['metadata'];facts=validated['facts']
    for review in meta.get('reviews',[]):
        try:
            if any(review.get(k)!=capture.get(k) for k in ['snapshot_id','document_sha256']):raise ValueError('review_document_binding')
            if not review.get('source') or not fresh(review.get('checked_at'),at,max_age_hours):raise ValueError('review_not_current_or_sourced')
            if review.get('topic') not in {'search_intent','language_and_wording'}:raise ValueError('unsupported_review_topic')
            if review.get('status')=='unknown':continue
            if review.get('status') not in {'needs_change','looks_reasonable'}:raise ValueError('unsupported_review_status')
            quotes=review.get('quotes',[])
            if not quotes:raise ValueError('review_quotes_required')
            for quote in quotes:
                field=quote['field'];value=capture['fields'].get(field)
                texts=[n.get('value','') for n in value] if field in {'titles','descriptions','keywords'} else value if field=='h1' else [value] if field=='body_text' else []
                if not quote.get('text') or not any(normalized(quote['text']) in normalized(t) for t in texts):raise ValueError('review_quote_not_observed')
            refs=review.get('fact_ids',[])
            if not refs or any(id not in facts for id in refs):raise ValueError('review_fact_reference_missing')
            if not review.get('update_rule') or not review.get('reason') or review.get('language')!=meta.get('language'):raise ValueError('review_scope_or_update_rule')
            proposed=review.get('proposed',{})
            if review['status']=='looks_reasonable':continue
            if not isinstance(proposed,dict) or not proposed or not set(proposed)<={'title','description'} or not all(isinstance(v,str) and v.strip() for v in proposed.values()):raise ValueError('proposed_metadata_invalid')
            text=' '.join(proposed.values());reason=None
            if rewrite_blocked:reason='route_or_product_conflict_requires_resolution'
            elif re.search(r'guaranteed\s+(?:profit|returns?)|risk[- ]free|稳赚|保证收益|无风险',text,re.I):reason='unsupported_return_claim'
            elif re.search(r'\b(?:buy|trade|trading)\b',text,re.I) and not any(f['role']=='listing_status' and f['value']=='listed' for f in facts.values()):reason='availability_not_verified'
            for id in refs:
                f=facts[id]
                if f['role'] in {'page_entity','route_entity'} and not any(contains(text,x) for x in [f['value']]+f.get('aliases',[])):reason='proposed_entity_not_supported'
            if reason:result['withheld'].append({'reason':reason,'review':review});continue
            result['drafts'].append({**review,'status':'draft_requires_editorial_review','template':meta.get('template'),
                'fact_sources':{id:facts[id] for id in refs},'limitations':'Automated guards are incomplete; language, scope, product and factual accuracy still require editorial review. No automatic publishing.'})
        except (ValueError,KeyError,TypeError) as error:result['gaps'].append(str(error))
    return result
