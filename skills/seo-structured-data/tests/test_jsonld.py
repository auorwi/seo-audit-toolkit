import json
from support import StructuredTest,URL
class JsonLdTests(StructuredTest):
    def parse(self,value,raw=False):
        html=value if raw else '<html><head><script type="application/ld+json">'+json.dumps(value)+'</script></head></html>'
        return self.module('jsonld').extract_jsonld(html,URL)
    def test_simple_entity_keeps_script_index_and_json_path(self):
        r=self.parse({'@context':'https://schema.org','@type':'Product','name':'Bitcoin'})
        self.assertEqual(r['entities'][0]['types'],['Product']);self.assertEqual(r['entities'][0]['path'],'$');self.assertEqual(r['entities'][0]['script_index'],0)
    def test_array_graph_and_nested_offer_preserve_paths(self):
        r=self.parse({'@context':'https://schema.org','@graph':[{'@type':'Product','offers':{'@type':'Offer','price':'1'}}]})
        self.assertEqual({x['path'] for x in r['entities']},{'$["@graph"][0]','$["@graph"][0]["offers"]'})
    def test_root_array_is_valid(self):
        self.assertEqual(len(self.parse([{'@context':'https://schema.org','@type':'WebPage'},{'@context':'https://schema.org','@type':'Organization'}])['entities']),2)
    def test_malformed_empty_and_non_json_constants_are_syntax_errors(self):
        for value in ['{bad}','', '{"price":NaN}','{"price":Infinity}']:
            r=self.parse('<script type="application/ld+json">'+value+'</script>',True);self.assertTrue(r['errors']);self.assertFalse(r['entities'])
    def test_scalar_root_is_not_valid_entity_document(self):
        self.assertTrue(self.parse('just text')['errors'])
    def test_duplicate_brand_key_not_silently_overwritten(self):
        r=self.parse('<script type="application/ld+json">{"@context":"https://schema.org","@type":"Product","brand":"A","brand":"B"}</script>',True)
        self.assertTrue(any(x['rule']=='duplicate_json_key' and x['key']=='brand' and x['values']==['A','B'] for x in r['errors']))
    def test_id_only_reference_not_duplicate_definition(self):
        r=self.parse({'@context':'https://schema.org','@graph':[{'@id':'#org','@type':'Organization','name':'BingX'},{'@type':'WebPage','publisher':{'@id':'#org'}}]})
        self.assertEqual(len(r['entities']),2);self.assertEqual(r['references'][0]['id'],URL+'#org')
    def test_relative_id_resolves_against_actual_page(self):
        r=self.parse({'@context':'https://schema.org','@id':'#page','@type':'WebPage'});self.assertEqual(r['entities'][0]['id'],URL+'#page')
    def test_multiple_types_and_schema_prefix_supported(self):
        r=self.parse({'@context':{'@vocab':'https://schema.org/','schema':'https://schema.org/'},'@type':['schema:Product','https://schema.org/Thing']})
        self.assertEqual(r['entities'][0]['types'],['Product','Thing'])
    def test_unknown_remote_context_is_gap_not_schema_certification(self):
        r=self.parse({'@context':'https://example.com/context','@type':'Product'})
        self.assertTrue(r['gaps']);self.assertFalse(r['entities'][0]['schema_context_known'])
    def test_template_and_non_ld_script_not_extracted(self):
        r=self.parse('<template><script type="application/ld+json">{"@type":"Product"}</script></template><script type="application/json">{}</script>',True)
        self.assertEqual(r['scripts'],[])
    def test_mime_case_and_parameter_allowed(self):
        r=self.parse('<script type="APPLICATION/LD+JSON; charset=utf-8">{"@context":"https://schema.org","@type":"WebPage"}</script>',True);self.assertEqual(len(r['entities']),1)
    def test_source_line_and_raw_preserved(self):
        r=self.parse('<html>\n<script type="application/ld+json"> {"@type":"WebPage"} </script></html>',True)
        self.assertEqual(r['scripts'][0]['line'],2);self.assertEqual(r['scripts'][0]['raw'],' {"@type":"WebPage"} ')
    def test_unclosed_script_is_coverage_gap(self):
        r=self.parse('<script type="application/ld+json">{"@type":"WebPage"}',True);self.assertTrue(r['gaps'])
    def test_missing_markup_is_inventory_not_automatic_error(self):
        r=self.parse('<html><body>Bitcoin</body></html>',True);self.assertEqual(r['errors'],[]);self.assertEqual(r['entities'],[])
    def test_nested_duplicate_key_has_field_path(self):
        r=self.parse('<script type="application/ld+json">{"@context":"https://schema.org","@type":"Product","offers":{"@type":"Offer","price":1,"price":2}}</script>',True)
        row=next(x for x in r['errors'] if x['rule']=='duplicate_json_key');self.assertEqual(row['path'],'$["offers"]');self.assertEqual(row['key'],'price')
    def test_blank_node_ids_preserve_blank_node_identity(self):
        r=self.parse({'@context':'https://schema.org','@graph':[{'@id':'_:org','@type':'Organization'},{'@type':'WebPage','publisher':{'@id':'_:org'}}]})
        self.assertEqual(r['entities'][0]['id'],'_:org');self.assertEqual(r['references'][0]['id'],'_:org')
