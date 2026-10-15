from support import StructuredTest,URL,AT

def record(**kw):return {'tool':'extruct','url':URL,'source':'real checker fixture','checked_at':'2026-09-17T01:00:00Z','checker_version':'0.18.0','document_sha256':'a'*64,'input_sha256':'a'*64,'state':'completed','syntaxes':['microdata','rdfa'],'payload':{'microdata':[],'rdfa':[]},**kw}
class EmbeddedTests(StructuredTest):
    def normalize(self,r):return self.module('embedded').normalize_extruct(r,url=URL,document_sha256='a'*64,at=AT)
    def test_microdata_normalizes_nested_offer_and_preserves_native_path(self):
        r=record(payload={'microdata':[{'type':'https://schema.org/Product','properties':{'name':'BTC','offers':{'type':'https://schema.org/Offer','properties':{'price':'1'}}}}],'rdfa':[]})
        v=self.normalize(r);self.assertEqual([e['types'] for e in v['entities']],[['Product'],['Offer']]);self.assertIn('["properties"]["offers"]',v['entities'][1]['path']);self.assertEqual(v['entities'][1]['data']['price'],'1')
    def test_rdfa_expanded_values_and_id_only_references(self):
        r=record(payload={'microdata':[],'rdfa':[{'@id':'#product','@type':['https://schema.org/Product'],'https://schema.org/name':[{'@value':'BTC'}],'https://schema.org/brand':[{'@id':'_:brand'}]}]})
        v=self.normalize(r);self.assertEqual(v['entities'][0]['data']['name'],'BTC');self.assertEqual(v['entities'][0]['id'],URL+'#product');self.assertEqual(v['references'][0]['id'],'_:brand')
    def test_multiple_microdata_types_preserved(self):
        r=record(payload={'microdata':[{'type':['https://schema.org/Product','https://schema.org/Thing'],'properties':{}}],'rdfa':[]})
        self.assertEqual(self.normalize(r)['entities'][0]['types'],['Product','Thing'])
    def test_wrong_hash_url_version_or_stale_are_gaps(self):
        for kw in [{'document_sha256':'b'*64},{'input_sha256':'b'*64},{'url':'https://bingx.com/en/other'},{'checker_version':''},{'checked_at':'2020-01-01T00:00:00Z'}]:
            r=self.normalize(record(**kw));self.assertEqual(r['status'],'evidence_gap');self.assertFalse(r['entities'])
    def test_missing_syntax_not_empty_success(self):
        r=self.normalize(record(payload={'microdata':[]}));self.assertTrue(r['gaps']);self.assertNotIn('rdfa',r['covered_syntaxes'])
    def test_partial_extraction_preserves_successful_syntax_and_gap(self):
        r=self.normalize(record(state='partial_extraction',payload={'microdata':[{'type':'https://schema.org/Product','properties':{'name':'BTC'}}]},errors=[{'syntax':'rdfa','reason':'failed'}]))
        self.assertEqual(len(r['entities']),1);self.assertTrue(r['gaps']);self.assertEqual(r['covered_syntaxes'],['microdata'])
    def test_unavailable_tool_never_certifies_formats(self):
        r=self.normalize(record(state='unavailable'));self.assertEqual(r['covered_syntaxes'],[]);self.assertTrue(r['gaps'])
    def test_successful_empty_extraction_has_no_schema_or_engine_pass(self):
        r=self.normalize(record());self.assertEqual(r['covered_syntaxes'],['microdata','rdfa']);self.assertFalse(r['coverage']['schema_semantic_validation']);self.assertFalse(r['coverage']['engine_validation'])
    def test_non_schema_rdfa_not_falsely_coerced_into_schema(self):
        r=record(payload={'microdata':[],'rdfa':[{'@id':'#a','@type':['http://example.com/Thing'],'http://example.com/name':[{'@value':'test'}]}]})
        v=self.normalize(r);self.assertFalse(v['entities'][0]['schema_context_known']);self.assertIn('http://example.com/name',v['entities'][0]['data'])
    def test_bad_payload_shape_not_silently_empty(self):
        for payload in [{'microdata':'bad','rdfa':[]},{'microdata':[{'type':'https://schema.org/Product','properties':'bad'}],'rdfa':[]}]:
            v=self.normalize(record(payload=payload));self.assertTrue(v['gaps']);self.assertFalse(v['entities'])
    def test_microdata_item_id_preserved(self):
        v=self.normalize(record(payload={'microdata':[{'id':'#x','type':'https://schema.org/Product','properties':{}}],'rdfa':[]}));self.assertEqual(v['entities'][0]['id'],URL+'#x')
    def test_multiple_values_do_not_disappear(self):
        v=self.normalize(record(payload={'microdata':[],'rdfa':[{'@type':['https://schema.org/Product'],'https://schema.org/brand':[{'@value':'A'},{'@value':'B'}]}]}));self.assertEqual(v['entities'][0]['data']['brand'],['A','B'])
