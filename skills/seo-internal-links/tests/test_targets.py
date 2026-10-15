from support import LinkTest,URL,AT
B='https://bingx.com/en/price';C='https://bingx.com/en/download'
def response(url=URL,status=200,**kw):return {'url':url,'status':status,'checked_at':'2026-09-17T02:00:00Z','method':'GET','source':'actual HTTP fixture','headers':[],'evidence':{'sha256':'a'*64},**kw}
class TargetTests(LinkTest):
    def resolve(self,rows,targets=None,**kw):return self.module('targets').assess_targets(rows,targets or [URL],at=AT,**kw)
    def test_404_and_410_are_observed_broken_http_targets(self):
        for code in [404,410]:self.assertEqual(self.resolve([response(status=code)])['targets'][0]['kind'],'broken_http_target')
    def test_server_failure_is_not_permanent_dead_page(self):
        r=self.resolve([response(status=503)])['targets'][0];self.assertEqual(r['kind'],'server_error');self.assertFalse(r['permanent_broken_proven'])
    def test_403_429_are_access_limits_not_broken_targets(self):
        for code in [403,429]:self.assertEqual(self.resolve([response(status=code)])['targets'][0]['kind'],'access_limited')
    def test_200_does_not_certify_content_or_indexability(self):
        r=self.resolve([response()])['targets'][0];self.assertEqual(r['kind'],'http_success_observed');self.assertEqual(r['content_validity'],'unverified');self.assertEqual(r['indexability'],'unverified')
    def test_redirect_chain_keeps_original_requested_target(self):
        r=self.resolve([response(status=301,headers=[['location','/en/price']]),response(B)])['targets'][0];self.assertEqual(r['kind'],'redirected_link');self.assertEqual(r['requested_url'],URL);self.assertEqual(r['final_url'],B);self.assertEqual(len(r['chain']),2)
    def test_redirect_then_404_retains_both_observations(self):
        r=self.resolve([response(status=302,headers=[['location',B]]),response(B,404)])['targets'][0];self.assertEqual(r['kind'],'broken_http_target');self.assertTrue(r['redirect_observed'])
    def test_missing_redirect_destination_is_explicitly_unverified(self):
        r=self.resolve([response(status=301,headers=[['location',B]])])['targets'][0];self.assertEqual(r['kind'],'redirect_target_unverified');self.assertEqual(r['final_url'],B)
    def test_redirect_loop_terminates_with_evidence(self):
        r=self.resolve([response(status=301,headers=[['location',B]]),response(B,302,headers=[['location',URL]])])['targets'][0];self.assertEqual(r['kind'],'redirect_loop_observed');self.assertLessEqual(len(r['chain']),3)
    def test_conflicting_location_headers_not_guessed(self):
        r=self.resolve([response(status=301,headers=[['location',B],['location',C]])])['targets'][0];self.assertEqual(r['kind'],'redirect_location_ambiguous')
    def test_relative_location_and_repeated_identical_headers_allowed(self):
        r=self.resolve([response(status=301,headers=[['Location','/en/price'],['location','/en/price']]),response(B)])['targets'][0];self.assertEqual(r['final_url'],B)
    def test_latest_request_failure_not_old_200(self):
        r=self.resolve([response(),response(status=None,error='timeout',checked_at='2026-09-17T02:30:00Z')])['targets'][0];self.assertEqual(r['kind'],'request_failed')
    def test_corrupt_latest_body_not_old_status(self):
        r=self.resolve([response(),response(status=404,evidence_error='hash mismatch',checked_at='2026-09-17T02:30:00Z')])['targets'][0];self.assertEqual(r['kind'],'evidence_unverified')
    def test_stale_future_missing_provenance_and_head_not_current_get(self):
        for kw in [{'checked_at':'2020-01-01T00:00:00Z'},{'checked_at':'2027-01-01T00:00:00Z'},{'source':''},{'method':'HEAD'},{'evidence':None}]:
            self.assertEqual(self.resolve([response(status=404,**kw)])['targets'][0]['kind'],'evidence_unverified')
    def test_no_record_is_not_inferred_404(self):self.assertEqual(self.resolve([])['targets'][0]['kind'],'not_observed')
    def test_missing_or_nonweb_location_not_guessed(self):
        for headers in [[],[['location','javascript:bad']]]:self.assertEqual(self.resolve([response(status=302,headers=headers)])['targets'][0]['kind'],'redirect_location_ambiguous')
    def test_target_aliases_dedupe_fragments_but_keep_query(self):
        r=self.resolve([],targets=[URL,URL+'#top',URL+'?page=2']);self.assertEqual(len(r['targets']),2)
    def test_chain_bound_prevents_unlimited_resolution(self):
        rows=[response(URL,301,headers=[['location',B]]),response(B,301,headers=[['location',C]]),response(C)]
        self.assertEqual(self.resolve(rows,max_hops=1)['targets'][0]['kind'],'redirect_limit')
    def test_unfollowed_304_not_a_successful_page_body(self):self.assertEqual(self.resolve([response(status=304)])['targets'][0]['kind'],'http_response_review')
