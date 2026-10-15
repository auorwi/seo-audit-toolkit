from support import InternationalTest,AT
from test_clusters import cap,E,F
from test_content import review
def case():
    before=cap(E,snapshot_id='before',visible_main='Bitcoin price');after=cap(F,snapshot_id='after',visible_main='Prix du Bitcoin')
    action={'source':'actual browser click','clicked_at':AT,'selector':'a.fr','before_snapshot':'before','after_snapshot':'after','before_sha256':'a'*64,'after_sha256':'a'*64,'before_url':E,'after_url':F,'expected_locale':'fr'}
    rs=[review(before,'en',quotes=['Bitcoin price']),review(after,'fr',quotes=['Prix du Bitcoin'])]
    return before,after,action,rs
class SwitchTests(InternationalTest):
    def run_check(self,b,a,action,rs):return self.module('switches').review_switch(b,a,action,rs,at=AT)
    def rules(self,r):return [o['rule'] for o in r['observations']]
    def test_entity_preserved(self):
        b,a,x,rs=case();r=self.run_check(b,a,x,rs);self.assertEqual(r['outcome'],'entity_preserved');self.assertEqual(r['observations'],[])
    def test_entity_lost(self):
        b,a,x,rs=case();rs[1]['entity_id']='homepage';self.assertIn('language_switch_entity_changed',self.rules(self.run_check(b,a,x,rs)))
    def test_wrong_actual_language(self):
        b,a,x,rs=case();rs[1]['body_language']='id';self.assertIn('language_switch_body_language_mismatch',self.rules(self.run_check(b,a,x,rs)))
    def test_hash_not_bound(self):
        b,a,x,rs=case();x['after_sha256']='b'*64;self.assertEqual(self.run_check(b,a,x,rs)['outcome'],'unknown')
    def test_unready_after_not_entity_lost(self):
        b,a,x,rs=case();a['readiness']='unknown_timeout';r=self.run_check(b,a,x,rs);self.assertEqual(r['outcome'],'unknown');self.assertEqual(r['observations'],[])
    def test_no_entity_evidence_unknown(self):
        b,a,x,rs=case();del rs[1]['entity_id'];self.assertEqual(self.run_check(b,a,x,rs)['outcome'],'unknown')
    def test_stale_action_unknown(self):
        b,a,x,rs=case();x['clicked_at']='2020-01-01T00:00:00Z';self.assertEqual(self.run_check(b,a,x,rs)['outcome'],'unknown')
    def test_missing_source_unknown(self):
        b,a,x,rs=case();del x['source'];self.assertEqual(self.run_check(b,a,x,rs)['outcome'],'unknown')
    def test_wrong_review_hash_unknown(self):
        b,a,x,rs=case();rs[1]['document_sha256']='c'*64;self.assertEqual(self.run_check(b,a,x,rs)['outcome'],'unknown')
    def test_same_url_not_assumed_failure(self):
        b,a,x,rs=case();a['url']=E;x['after_url']=E;rs[1]['url']=E;self.assertEqual(self.run_check(b,a,x,rs)['outcome'],'entity_preserved')
    def test_action_different_url_rejected(self):
        b,a,x,rs=case();x['after_url']='https://bingx.com/fr/';self.assertEqual(self.run_check(b,a,x,rs)['outcome'],'unknown')
    def test_action_no_selector_unknown(self):
        b,a,x,rs=case();del x['selector'];self.assertEqual(self.run_check(b,a,x,rs)['outcome'],'unknown')
    def test_action_before_before_snapshot_rejected(self):
        b,a,x,rs=case();x['clicked_at']='2026-09-17T03:59:00Z';self.assertEqual(self.run_check(b,a,x,rs)['outcome'],'unknown')
