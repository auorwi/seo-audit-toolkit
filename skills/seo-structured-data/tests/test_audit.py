import copy,json
from support import StructuredTest,URL,AT
from test_vocabulary import vocabulary

def capture(**kw):
    return {'url':URL,'snapshot_id':'dom1','document_sha256':'a'*64,'captured_at':'2026-09-17T01:00:00Z','source':'actual browser fixture','representation':'rendered_html','readiness':'ready','entry_mode':'direct',
        'jsonld':{'scripts':[{'raw':'{}'}],'entities':[{'types':['Offer'],'data':{'@type':'Offer','price':'$12.00','priceCurrency':'USD'},'id':URL+'#offer','path':'$','script_index':0,'schema_context_known':True}],'references':[],'errors':[],'gaps':[]},**kw}
class AuditTests(StructuredTest):
    def run_audit(self,cs=None,scope=None,**kw):
        return self.module('audit').audit(cs if cs is not None else [capture()],scope or [{'url':URL,'entries':['direct']}],at=AT,**kw)
    def test_actual_price_observation_and_four_separate_layers(self):
        r=self.run_audit();self.assertTrue(any(f['rule']=='price_format_review' for f in r['findings']));row=r['rows'][0]
        self.assertEqual(row['layers']['engine_eligibility'],'unverified');self.assertEqual(row['layers']['actual_display'],'unverified');self.assertFalse(r['coverage']['full_site'])
    def test_missing_microdata_rdfa_tool_is_gap_not_full_extraction(self):
        r=self.run_audit();self.assertTrue(any('extruct' in str(g) for g in r['gaps']));self.assertEqual(r['coverage']['complete_extractions'],0)
    def test_latest_failed_capture_never_falls_back_old_success(self):
        failed=capture(snapshot_id='new',captured_at='2026-09-17T01:30:00Z',state='timeout');r=self.run_audit([capture(),failed]);self.assertFalse(r['findings']);self.assertEqual(r['coverage']['ready_documents'],0)
    def test_default_scope_requires_direct_and_internal_and_reports_missing(self):
        r=self.run_audit(scope=[URL]);self.assertTrue(any(g.get('entry_mode')=='internal' for g in r['gaps']))
    def test_same_problem_source_and_rendered_merge_evidence_not_duplicate_issue(self):
        source=capture(snapshot_id='source',representation='initial_html',readiness=None);r=self.run_audit([source,capture()]);fs=[f for f in r['findings'] if f['rule']=='price_format_review'];self.assertEqual(len(fs),1);self.assertEqual(len(fs[0]['evidence']),2)
    def test_syntax_error_not_hidden_by_other_valid_entities(self):
        c=capture();c['jsonld']['errors']=[{'rule':'duplicate_json_key','script_index':0,'path':'$','key':'brand','values':['A','B']}];r=self.run_audit([c]);self.assertTrue(any(f['rule']=='duplicate_json_key' for f in r['findings']))
    def test_vocabulary_unknown_type_review_uses_supplied_snapshot(self):
        v={'terms':self.module('vocabulary').build_vocabulary(vocabulary()),'retrieved_at':'2026-09-17T01:00:00Z','source':'https://schema.org/','evidence':{'sha256':'b'*64}}
        c=capture();c['jsonld']['entities'][0]['types']=['Prodcut'];r=self.run_audit([c],vocabulary=v);self.assertEqual(next(f['value'] for f in r['findings'] if f['rule']=='unknown_schema_type'),'Prodcut')
    def test_stale_vocabulary_not_presented_as_current_authority(self):
        v={'terms':self.module('vocabulary').build_vocabulary(vocabulary()),'retrieved_at':'2020-01-01T00:00:00Z','source':'https://schema.org/','evidence':{'sha256':'b'*64}}
        r=self.run_audit(vocabulary=v);self.assertTrue(any('vocabulary' in str(g) for g in r['gaps']))
    def test_native_extraction_with_matching_document_is_used(self):
        from test_embedded import record
        c=capture(extruct=record());r=self.run_audit([c]);self.assertEqual(r['coverage']['complete_extractions'],1)
    def test_wrong_native_document_not_counted_as_complete(self):
        from test_embedded import record
        c=capture(extruct=record(document_sha256='b'*64));self.assertEqual(self.run_audit([c])['coverage']['complete_extractions'],0)
    def test_conflicting_capture_id_and_invalid_scope_rejected(self):
        a=capture();b=copy.deepcopy(a);b['document_sha256']='b'*64
        with self.assertRaises(ValueError):self.run_audit([a,b])
        with self.assertRaises(ValueError):self.module('audit').audit([],[],at=AT)
        with self.assertRaises(ValueError):self.run_audit(scope=['https://example.com/'])
    def test_partial_scope_and_inputs_not_mutated(self):
        cs=[capture()];before=copy.deepcopy(cs);self.run_audit(cs);self.assertEqual(cs,before)
    def test_comparisons_do_not_cross_unrelated_source_navigation_stages(self):
        from test_embedded import record
        rows=[capture(snapshot_id='sd',representation='initial_html',readiness=None,entry_mode='direct',extruct=record()),capture(snapshot_id='rd',entry_mode='direct',extruct=record()),capture(snapshot_id='si',representation='initial_html',readiness=None,entry_mode='internal',extruct=record()),capture(snapshot_id='ri',entry_mode='internal',extruct=record())]
        r=self.run_audit(rows,scope=[URL]);self.assertEqual(len(r['comparisons']),3)
    def test_latest_failed_entry_cannot_use_older_other_entry_for_history_recheck(self):
        from test_embedded import record
        from test_engine import report
        old=capture(snapshot_id='internal-old',entry_mode='internal',extruct=record());old['jsonld']['entities']=[{'types':['AggregateRating'],'data':{'ratingValue':4.9},'id':'#rating','path':'$','schema_context_known':True}]
        failed=capture(snapshot_id='direct-failed',captured_at='2026-09-17T01:30:00Z',state='timeout')
        r=self.run_audit([old,failed],scope=[URL],engine_reports=[report()]);self.assertEqual(r['engine_results'][0]['history'][0]['status'],'not_verified')
    def test_entity_inventory_and_reference_edges_preserved_even_without_findings(self):
        from test_embedded import record
        c=capture(extruct=record());c['jsonld']['references']=[{'script_index':0,'path':'$["seller"]','id':'https://bingx.com/#organization'}]
        r=self.run_audit([c]);self.assertTrue(r['entity_inventory']);self.assertEqual(r['graph_edges'][0]['to_entity'],'https://bingx.com/#organization')
        self.assertFalse(any(f['rule']=='unresolved_local_reference_review' for f in r['findings']))
    def test_complete_missing_local_reference_is_review_only(self):
        from test_embedded import record
        c=capture(extruct=record());c['jsonld']['references']=[{'script_index':0,'path':'$["brand"]','id':URL+'#missing'}]
        r=self.run_audit([c]);self.assertTrue(any(f['rule']=='unresolved_local_reference_review' for f in r['findings']))
    def test_incomplete_extraction_cannot_assert_unresolved_local_reference(self):
        c=capture();c['jsonld']['references']=[{'script_index':0,'path':'$["brand"]','id':URL+'#missing'}]
        self.assertFalse(any(f['rule']=='unresolved_local_reference_review' for f in self.run_audit([c])['findings']))
