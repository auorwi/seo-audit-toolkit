import copy,hashlib
from support import TdkTest,URL,AT

def capture(**kw):
    return {'url':URL,'snapshot_id':'dom1','document_sha256':'a'*64,'captured_at':'2026-09-17T00:00:00Z','source':'actual browser',
        'representation':'rendered_html','readiness':'ready','fields':{'body_text':'SOLV Project Details Ended','titles':[{'value':'SOLV | BingX'}],'descriptions':[{'value':'Learn about SOLV.'}],'keywords':[],'h1':['SOLV'],'html_lang':'en','coverage':{'head_seen':True,'closed_head':True,'body_complete':True}},**kw}

def fact(id='page',role='page_entity',value='SOLV',**kw):
    return {'id':id,'role':role,'value':value,'aliases':[value],'origin':'page','quote':'SOLV Project Details','location':'.meta-name','source':'observed ready page','observed_at':'2026-09-17T00:00:00Z','visibility':'visible',**kw}

def context(**kw):
    return {'url':URL,'snapshot_id':'dom1','document_sha256':'a'*64,'checked_at':'2026-09-17T00:00:00Z','source':'Codex evidence-bound review','template':'launchpad_detail','language':'en','facts':[fact()], 'requirements':[],**kw}

def external_fact(id,role,value,origin='route_registry',text=None):
    text=text or ('SOLV spot '+value if role=='listing_status' else role+': '+value)
    result=fact(id,role,value,origin=origin,quote=text,document={'text':text,'sha256':hashlib.sha256(text.encode()).hexdigest()},source='verified '+origin)
    if role=='listing_status':result['subject']={'entity':'SOLV','product':'spot','market_scope':'unknown'}
    return result

class ContextTests(TdkTest):
    def validate(self,c=None,ctx=None):return self.module('context').validate_context(c or capture(),ctx or context(),at=AT)
    def test_current_page_fact_keeps_binding_and_role(self):
        r=self.validate();self.assertEqual(r['facts']['page']['value'],'SOLV');self.assertEqual(r['gaps'],[])
    def test_wrong_document_snapshot_and_url_rejected(self):
        for kw in [{'document_sha256':'b'*64},{'snapshot_id':'old'},{'url':'https://bingx.com/en/other'}]:
            r=self.validate(ctx=context(**kw));self.assertFalse(r['facts']);self.assertTrue(r['gaps'])
    def test_missing_source_and_old_review_rejected(self):
        for kw in [{'source':''},{'checked_at':'2020-01-01T00:00:00Z'},{'checked_at':'bad'}]:self.assertTrue(self.validate(ctx=context(**kw))['gaps'])
    def test_fact_quote_must_exist_in_page(self):
        r=self.validate(ctx=context(facts=[fact(quote='ETH Project Details')]))
        self.assertFalse(r['facts']);self.assertTrue(r['gaps'])
    def test_fact_value_cannot_be_invented_from_unrelated_quote(self):
        r=self.validate(ctx=context(facts=[fact(value='ETH',aliases=['ETH'])]));self.assertFalse(r['facts'])
    def test_unknown_visibility_cannot_confirm_page_entity(self):
        self.assertFalse(self.validate(ctx=context(facts=[fact(visibility='unknown')]))['facts'])
    def test_source_html_is_not_visible_page_entity(self):
        self.assertFalse(self.validate(c=capture(representation='initial_html',readiness=None))['facts'])
    def test_external_route_entity_has_separate_document(self):
        r=self.validate(ctx=context(facts=[external_fact('route','route_entity','SOLV')]))
        self.assertEqual(r['facts']['route']['origin'],'route_registry')
    def test_external_document_hash_and_quote_checked(self):
        for edit in ['hash','quote']:
            f=external_fact('r','route_entity','SOLV')
            if edit=='hash':f['document']['sha256']='b'*64
            else:f['quote']='ETH'
            self.assertFalse(self.validate(ctx=context(facts=[f]))['facts'])
    def test_listing_status_requires_product_catalog_not_page_advertisement(self):
        self.assertFalse(self.validate(ctx=context(facts=[fact('status','listing_status','SOLV')]))['facts'])
        self.assertTrue(self.validate(ctx=context(facts=[fact(),external_fact('status','listing_status','not_listed','product_catalog')]))['facts'])
    def test_expired_fact_not_refreshed_by_new_context_time(self):
        self.assertFalse(self.validate(ctx=context(facts=[fact(observed_at='2020-01-01T00:00:00Z')]))['facts'])
    def test_duplicate_fact_id_is_gap_not_last_write_wins(self):
        self.assertFalse(self.validate(ctx=context(facts=[fact(),fact(value='ETH')]))['facts'])
    def test_entity_boundary_does_not_match_sol_inside_solv(self):
        r=self.validate(ctx=context(facts=[fact(value='SOL',aliases=['SOL'])]));self.assertFalse(r['facts'])
    def test_input_not_modified(self):
        ctx=context();before=copy.deepcopy(ctx);self.validate(ctx=ctx);self.assertEqual(ctx,before)
    def test_alias_cannot_turn_unrelated_quote_into_fact(self):
        f=fact(value='ETH',aliases=['SOLV'])
        self.assertFalse(self.validate(ctx=context(facts=[f]))['facts'])
    def test_malformed_rule_configuration_is_gap_not_runtime_exception(self):
        for kw in [{'requirements':'bad'},{'requirements':[None]},{'dynamic_title':[]},{'translation_keys':[None]},{'reviews':'bad'}]:
            r=self.validate(ctx=context(**kw));self.assertTrue(r['gaps']);self.assertEqual(r['metadata'],{})
