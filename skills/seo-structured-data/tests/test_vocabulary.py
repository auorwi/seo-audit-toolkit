from support import StructuredTest,AT

def vocabulary():
    return {'@graph':[{'@id':'schema:Thing','@type':'rdfs:Class'},{'@id':'schema:Product','@type':'rdfs:Class','rdfs:subClassOf':{'@id':'schema:Thing'}},{'@id':'schema:IndividualProduct','@type':'rdfs:Class','rdfs:subClassOf':{'@id':'schema:Product'}},{'@id':'schema:Offer','@type':'rdfs:Class','rdfs:subClassOf':{'@id':'schema:Thing'}},{'@id':'schema:name','@type':'rdf:Property','schema:domainIncludes':{'@id':'schema:Thing'},'schema:rangeIncludes':{'@id':'schema:Text'}},{'@id':'schema:price','@type':'rdf:Property','schema:domainIncludes':{'@id':'schema:Offer'},'schema:rangeIncludes':[{'@id':'schema:Number'},{'@id':'schema:Text'}]}]}
class VocabularyTests(StructuredTest):
    def build(self,data=None):return self.module('vocabulary').build_vocabulary(data or vocabulary())
    def review(self,types,props):
        return self.module('vocabulary').review_terms({'types':types,'schema_context_known':True,'data':props},self.build())
    def test_parse_classes_properties_and_multiple_ranges(self):
        v=self.build();self.assertIn('Product',v['classes']);self.assertEqual(set(v['properties']['price']['ranges']),{'Number','Text'})
    def test_inherited_property_allowed_on_subclass(self):
        self.assertEqual(self.review(['IndividualProduct'],{'name':'BTC'})['observations'],[])
    def test_unknown_type_review_not_engine_rejection(self):
        r=self.review(['Prodcut'],{});self.assertEqual(r['observations'][0]['rule'],'unknown_schema_type');self.assertFalse(r['coverage']['engine_validation'])
    def test_unknown_property_review_keeps_name(self):
        r=self.review(['Product'],{'naem':'BTC'});self.assertEqual(r['observations'][0]['property'],'naem')
    def test_property_domain_mismatch_is_review_not_closed_world_invalidity(self):
        r=self.review(['Product'],{'price':'1'});self.assertEqual(r['observations'][0]['classification'],'schema_vocabulary_review')
    def test_multiple_types_allow_property_if_any_type_inherits_domain(self):
        self.assertEqual(self.review(['Product','Offer'],{'price':1})['observations'],[])
    def test_external_namespace_property_not_mislabeled_schema_typo(self):
        r=self.review(['Product'],{'https://example.com/property':'x'});self.assertEqual(r['observations'],[]);self.assertTrue(r['gaps'])
    def test_unknown_context_does_not_run_schema_term_rules(self):
        r=self.module('vocabulary').review_terms({'types':['NotSchema'],'schema_context_known':False,'data':{'alien':'x'}},self.build());self.assertFalse(r['observations']);self.assertTrue(r['gaps'])
    def test_cycle_in_vocabulary_does_not_recurse_forever(self):
        d=vocabulary();d['@graph'][0]['rdfs:subClassOf']={'@id':'schema:IndividualProduct'};v=self.build(d)
        r=self.module('vocabulary').review_terms({'types':['IndividualProduct'],'schema_context_known':True,'data':{'name':'BTC'}},v);self.assertEqual(r['observations'],[])
    def test_malformed_vocabulary_rejected(self):
        with self.assertRaises(ValueError):self.build({'@graph':'bad'})
