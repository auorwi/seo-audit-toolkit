from support import StructuredTest,URL,AT

def current(**kw):return {'url':URL,'document_sha256':'a'*64,'captured_at':'2026-09-17T01:00:00Z','ready':True,'extraction_complete':True,'checked_rules':['rating_number_review'],'observations':[],**kw}
def report(**kw):return {'url':URL,'engine':'Google','tool':'Search Console','kind':'historical_issue','checked_at':'2026-09-01T00:00:00Z','source':'actual platform export fixture','artifact_sha256':'b'*64,'rule':'rating_number_review','result':'error',**kw}
class EngineTests(StructuredTest):
    def assess(self,reports=None,c=None):return self.module('engine').assess_engine_evidence(reports if reports is not None else [report()],c or current(),at=AT)
    def test_history_not_reproduced_is_not_closed_or_fixed(self):
        r=self.assess();self.assertEqual(r['history'][0]['status'],'not_reproduced_in_current_scope');self.assertFalse(r['history'][0]['auto_close'])
    def test_history_current_same_rule_reproduced(self):
        r=self.assess(c=current(observations=[{'rule':'rating_number_review'}]));self.assertEqual(r['history'][0]['status'],'reproduced')
    def test_unchecked_rule_or_incomplete_capture_cannot_claim_non_reproduction(self):
        for kw in [{'checked_rules':[]},{'extraction_complete':False},{'ready':False}]:self.assertEqual(self.assess(c=current(**kw))['history'][0]['status'],'not_verified')
    def test_historical_valid_result_is_not_current_engine_validation(self):
        r=self.assess([report(result='valid')]);self.assertEqual(r['engine_validation'],'unverified')
    def test_bound_current_code_test_keeps_engine_result_without_guaranteeing_display(self):
        r=self.assess([report(kind='code_test',tool='Rich Results Test',checked_at='2026-09-17T01:30:00Z',result='valid',document_sha256='a'*64)])
        self.assertEqual(r['engine_validation'],'observed_valid');self.assertEqual(r['actual_display'],'unverified')
    def test_wrong_code_document_or_stale_result_rejected(self):
        for kw in [{'document_sha256':'c'*64,'checked_at':'2026-09-17T01:30:00Z'},{'document_sha256':'a'*64,'checked_at':'2020-01-01T00:00:00Z'}]:
            r=self.assess([report(kind='code_test',tool='Rich Results Test',result='valid',**kw)]);self.assertEqual(r['engine_validation'],'unverified');self.assertTrue(r['gaps'])
    def test_remote_url_test_not_bound_to_local_snapshot(self):
        r=self.assess([report(kind='url_test',tool='Rich Results Test',checked_at='2026-09-17T01:30:00Z',result='valid')]);self.assertEqual(r['engine_validation'],'remote_url_result_observed');self.assertTrue(r['gaps'])
    def test_future_result_wrong_url_and_missing_source_rejected(self):
        for kw in [{'checked_at':'2027-01-01T00:00:00Z'},{'url':'https://bingx.com/other'},{'source':''},{'artifact_sha256':'bad'}]:
            r=self.assess([report(**kw)]);self.assertFalse(r['history']);self.assertTrue(r['gaps'])
    def test_actual_display_requires_query_device_locale_and_real_observation(self):
        incomplete=report(kind='serp_observation',result='observed',checked_at='2026-09-17T01:30:00Z')
        self.assertEqual(self.assess([incomplete])['actual_display'],'unverified')
        complete={**incomplete,'query':'BingX app','device':'desktop','locale':'en-SG','feature':'software_app'}
        r=self.assess([complete]);self.assertEqual(r['actual_display'],'observed_at_recorded_time');self.assertEqual(r['engine_validation'],'unverified')
    def test_latest_engine_failure_does_not_fall_back_old_valid(self):
        good=report(kind='code_test',tool='Rich Results Test',result='valid',document_sha256='a'*64,checked_at='2026-09-17T01:10:00Z')
        failed={**good,'result':'test_failed','checked_at':'2026-09-17T01:30:00Z'}
        self.assertEqual(self.assess([good,failed])['engine_validation'],'unverified')
    def test_unbound_remote_result_does_not_override_bound_code_result(self):
        code=report(kind='code_test',tool='Rich Results Test',result='invalid',document_sha256='a'*64,checked_at='2026-09-17T01:10:00Z')
        remote=report(kind='url_test',tool='Rich Results Test',result='valid',checked_at='2026-09-17T01:30:00Z')
        self.assertEqual(self.assess([code,remote])['engine_validation'],'observed_invalid')
    def test_historical_entity_absent_cannot_be_cleared_by_other_entity_check(self):
        r=self.assess([report(entity_id=URL+'#old',field='ratingValue')],current(entities=[{'id':URL+'#new','data':{'ratingValue':4.9}}]))
        self.assertEqual(r['history'][0]['status'],'not_verified')
    def test_historical_field_absent_on_target_entity_is_unverified(self):
        r=self.assess([report(entity_id=URL+'#old',field='ratingValue')],current(entities=[{'id':URL+'#old','data':{'name':'App'}}]))
        self.assertEqual(r['history'][0]['status'],'not_verified')
    def test_historical_entity_and_field_actually_checked_can_be_not_reproduced(self):
        r=self.assess([report(entity_id=URL+'#old',field='ratingValue')],current(entities=[{'id':URL+'#old','data':{'ratingValue':4.9}}]))
        self.assertEqual(r['history'][0]['status'],'not_reproduced_in_current_scope')
