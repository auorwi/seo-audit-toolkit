from support import StructuredTest,URL,AT
from test_rules import entity

def snapshot(**kw):return {'url':URL,'snapshot_id':'a','captured_at':'2026-09-17T01:00:00Z','representation':'rendered_html','readiness':'ready','entry_mode':'direct','document_sha256':'a'*64,'entities':[entity('Product',{'name':'BTC'},id=URL+'#product')],'extraction_complete':True,**kw}
class CompareTests(StructuredTest):
    def compare(self,a=None,b=None):return self.module('compare').compare_snapshots(a or snapshot(),b or snapshot(snapshot_id='b'),at=AT)
    def test_same_entities_in_two_snapshots_are_not_duplicate_injection(self):
        self.assertEqual(self.compare()['observations'],[])
    def test_rendered_repeat_of_same_definition_is_candidate_not_error(self):
        a=snapshot(representation='initial_html',readiness=None);b=snapshot(snapshot_id='b',entities=a['entities']+a['entities'])
        r=self.compare(a,b);row=next(x for x in r['observations'] if x['rule']=='repeated_definition_increase');self.assertEqual(row['classification'],'duplicate_candidate')
    def test_complementary_same_id_does_not_count_as_repeated_definition(self):
        a=snapshot();b=snapshot(snapshot_id='b',entities=a['entities']+[entity('Product',{'url':URL},id=URL+'#product')])
        self.assertNotIn('repeated_definition_increase',{x['rule'] for x in self.compare(a,b)['observations']})
    def test_entry_path_difference_is_review_with_both_evidence_ids(self):
        b=snapshot(snapshot_id='b',entry_mode='internal',entities=[entity('Product',{'name':'ETH'},id=URL+'#product')]);r=self.compare(b=b)
        row=next(x for x in r['observations'] if x['rule']=='entry_path_schema_difference');self.assertEqual(row['before_snapshot'],'a');self.assertEqual(row['after_snapshot'],'b')
    def test_source_dom_price_change_is_observation_not_confirmed_bug(self):
        a=snapshot(representation='initial_html',entities=[entity(data={'price':'1'})]);b=snapshot(snapshot_id='b',entities=[entity(data={'price':'2'})]);r=self.compare(a,b)
        self.assertTrue(r['observations']);self.assertTrue(all(x['classification']=='stage_observation' for x in r['observations']))
    def test_incomplete_extraction_does_not_claim_removed_schema(self):
        r=self.compare(b=snapshot(snapshot_id='b',entities=[],extraction_complete=False));self.assertEqual(r['observations'],[]);self.assertTrue(r['gaps'])
    def test_unready_or_stale_after_snapshot_is_gap(self):
        for kw in [{'readiness':'pending'},{'captured_at':'2020-01-01T00:00:00Z'}]:
            r=self.compare(b=snapshot(snapshot_id='b',entities=[],**kw));self.assertFalse(r['observations']);self.assertTrue(r['gaps'])
    def test_different_urls_not_called_same_page_path_mismatch(self):
        r=self.compare(b=snapshot(url='https://bingx.com/en/price/ethereum',snapshot_id='b',entities=[]));self.assertFalse(r['observations']);self.assertTrue(r['gaps'])
    def test_complete_ready_empty_after_can_observe_removal(self):
        r=self.compare(b=snapshot(snapshot_id='b',entities=[]));self.assertIn('schema_entity_removed',{x['rule'] for x in r['observations']})
    def test_json_object_key_order_not_change(self):
        a=snapshot(entities=[entity(data={'price':1,'priceCurrency':'USD'})]);b=snapshot(snapshot_id='b',entities=[entity(data={'priceCurrency':'USD','price':1})]);self.assertFalse(self.compare(a,b)['observations'])
