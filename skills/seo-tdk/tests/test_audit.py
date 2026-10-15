import copy
from support import TdkTest,URL,AT
from test_context import capture,context
class AuditTests(TdkTest):
    def audit(self,cs=None,urls=None):
        c=capture();c['context']=context()
        return self.module('audit').audit(cs if cs is not None else [c],urls or [URL],at=AT)
    def test_ready_single_page_keeps_coverage_and_intent_pending(self):
        r=self.audit();self.assertEqual(r['coverage']['ready_pages'],1);self.assertTrue(r['pending_reviews']);self.assertFalse(r['coverage']['full_site'])
    def test_latest_failure_does_not_use_old_good_metadata(self):
        old=capture();new=capture(snapshot_id='new',captured_at='2026-09-17T00:30:00Z',state='timeout')
        r=self.audit([old,new]);self.assertEqual(r['coverage']['ready_pages'],0);self.assertFalse(r['findings']);self.assertTrue(r['gaps'])
    def test_stale_and_unready_excluded_from_duplicate_clusters(self):
        a=capture();b=capture(url='https://bingx.com/en/other',snapshot_id='b',readiness='pending')
        r=self.audit([a,b],[a['url'],b['url']]);self.assertEqual(r['duplicate_clusters'],[])
    def test_all_current_requested_titles_cluster_with_member_evidence(self):
        a=capture();b=capture(url='https://bingx.com/en/other',snapshot_id='b');b['fields']['titles']=[{'value':'  solv | BINGX '}]
        r=self.audit([a,b],[a['url'],b['url']]);cluster=next(x for x in r['duplicate_clusters'] if x['field']=='title')
        self.assertEqual(len(cluster['members']),2);self.assertEqual(cluster['classification'],'duplicate_candidate');self.assertTrue(cluster['members'][0]['snapshot_id'])
    def test_duplicate_input_same_url_not_two_cluster_members(self):
        r=self.audit([capture(),capture()]);self.assertEqual(r['duplicate_clusters'],[])
    def test_other_scope_page_not_silently_added(self):
        r=self.audit([capture(),capture(url='https://bingx.com/en/other',snapshot_id='b')]);self.assertEqual(r['coverage']['requested_urls'],1);self.assertEqual(r['duplicate_clusters'],[])
    def test_initial_vs_rendered_same_url_not_duplicate_pages(self):
        r=self.audit([capture(representation='initial_html',readiness=None,snapshot_id='source'),capture()]);self.assertEqual(r['duplicate_clusters'],[])
    def test_different_languages_group_separately(self):
        a=capture();b=capture(url='https://bingx.com/ja/other',snapshot_id='b');b['fields']['html_lang']='ja'
        r=self.audit([a,b],[a['url'],b['url']]);self.assertEqual(r['duplicate_clusters'],[])
    def test_issue_identity_kept_and_multiple_evidence_merged(self):
        c=capture();c['fields']['titles']=[{'value':' '},{'value':' '}]
        r=self.audit([c]);ids=[f['issue_id'] for f in r['findings']];self.assertEqual(len(ids),len(set(ids)))
    def test_invalid_scope_empty_scope_and_freshness_fail(self):
        for urls in [[],['https://example.com/']]:
            with self.assertRaises(ValueError):self.module('audit').audit([],urls,at=AT)
        with self.assertRaises(ValueError):self.module('audit').audit([], [URL],at=AT,max_age_hours=0)
    def test_conflicting_capture_identity_rejected(self):
        a=capture();b=copy.deepcopy(a);b['fields']['titles']=[]
        with self.assertRaises(ValueError):self.audit([a,b])
    def test_missing_page_is_gap_not_zero_issue_pass(self):
        r=self.audit([]);self.assertEqual(r['coverage']['ready_pages'],0);self.assertTrue(r['gaps'])
    def test_duplicate_candidates_are_persistent_findings(self):
        a=capture();b=capture(url='https://bingx.com/en/other',snapshot_id='b')
        r=self.audit([a,b],[a['url'],b['url']]);self.assertTrue(any(f['rule']=='duplicate_metadata_cluster' and f['classification']=='duplicate_candidate' for f in r['findings']))
