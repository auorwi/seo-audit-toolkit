from support import StructuredTest,URL

def entity(type='Offer',data=None,path='$',id=None,**kw):
    return {'types':[type],'data':{'@type':type,**(data or {})},'path':path,'id':id,'schema_context_known':True,'syntax':'json-ld','script_index':0,**kw}
class EntityRuleTests(StructuredTest):
    def check(self,rows,profile=None):return self.module('rules').audit_entities(rows,profile=profile)
    def names(self,r):return {x['rule'] for x in r['observations']}
    def test_price_currency_symbols_comma_and_placeholder_detected(self):
        for value in ['$12.3','1,200.00','--','{{price}}','１２']:
            r=self.check([entity(data={'price':value})]);self.assertIn('price_format_review',self.names(r))
    def test_numeric_zero_decimal_and_numeric_string_valid(self):
        for value in [0,12.34,'0','12.34']:
            self.assertNotIn('price_format_review',self.names(self.check([entity(data={'price':value})])))
    def test_boolean_is_not_valid_price(self):self.assertIn('price_format_review',self.names(self.check([entity(data={'price':True})])))
    def test_schema_crypto_currency_not_rejected_as_not_three_letters(self):
        r=self.check([entity(data={'price':'1','priceCurrency':'USDT'})]);self.assertNotIn('google_currency_format_review',self.names(r))
    def test_google_product_currency_rule_separate_from_schema(self):
        r=self.check([entity(data={'price':'1','priceCurrency':'USDT'})],profile='google_product_snippet')
        row=next(x for x in r['observations'] if x['rule']=='google_currency_format_review');self.assertEqual(row['layer'],'engine_local_rules')
    def test_product_snippet_currency_missing_is_recommendation(self):
        r=self.check([entity(data={'price':1})],profile='google_product_snippet');row=next(x for x in r['observations'] if x['rule']=='recommended_price_currency_missing');self.assertEqual(row['classification'],'recommendation')
    def test_product_page_not_automatically_declared_shopping_eligible(self):
        r=self.check([entity('Product',{'name':'Bitcoin'})]);self.assertFalse(any(x['rule'].startswith('required_') for x in r['observations']));self.assertEqual(r['layers']['engine_eligibility'],'unverified')
    def test_product_requires_name_and_one_of_offer_rating_review_when_profile_explicit(self):
        r=self.check([entity('Product')],profile='google_product_snippet');self.assertIn('required_product_name',self.names(r));self.assertIn('required_product_supporting_property',self.names(r))
    def test_product_review_alternative_does_not_require_offer(self):
        r=self.check([entity('Product',{'name':'BTC','review':{'@type':'Review'}})],profile='google_product_snippet');self.assertNotIn('required_product_supporting_property',self.names(r))
    def test_offer_price_specification_alternative_allowed(self):
        r=self.check([entity(data={'priceSpecification':{'@type':'PriceSpecification','price':'0'}})],profile='google_product_snippet');self.assertNotIn('required_offer_price',self.names(r))
    def test_aggregate_offer_requires_lowprice_and_currency_for_selected_profile(self):
        names=self.names(self.check([entity('AggregateOffer')],profile='google_product_snippet'));self.assertIn('required_aggregate_low_price',names);self.assertIn('required_aggregate_currency',names)
    def test_rating_value_outside_default_and_explicit_scale(self):
        for data in [{'ratingValue':'8'},{'ratingValue':101,'bestRating':100,'worstRating':0}]:self.assertIn('rating_bounds_review',self.names(self.check([entity('AggregateRating',data)])))
    def test_custom_rating_scale_can_be_valid(self):
        self.assertNotIn('rating_bounds_review',self.names(self.check([entity('Rating',{'ratingValue':90,'bestRating':100,'worstRating':0})])))
    def test_rating_bad_number_and_negative_count_detected(self):
        r=self.check([entity('AggregateRating',{'ratingValue':'4.5 stars','ratingCount':-1})]);self.assertIn('rating_number_review',self.names(r));self.assertIn('rating_count_review',self.names(r))
    def test_software_app_free_price_zero_is_valid_present_value(self):
        r=self.check([entity('SoftwareApplication',{'name':'BingX','offers':{'@type':'Offer','price':0},'aggregateRating':{'ratingValue':4.5}})],profile='google_software_app');self.assertNotIn('required_software_price',self.names(r))
    def test_software_requires_real_rating_or_review_no_fabrication(self):
        r=self.check([entity('SoftwareApplication',{'name':'BingX','offers':{'price':0}})],profile='google_software_app');self.assertIn('required_software_rating_or_review',self.names(r));self.assertFalse(r['suggested_fabricated_values'])
    def test_last_breadcrumb_without_item_is_allowed(self):
        data={'itemListElement':[{'@type':'ListItem','position':1,'name':'Home','item':'https://bingx.com/'},{'@type':'ListItem','position':2,'name':'Price'}]}
        r=self.check([entity('BreadcrumbList',data)],profile='google_breadcrumb');self.assertNotIn('breadcrumb_item_missing',self.names(r))
    def test_nonfinal_breadcrumb_item_missing_detected(self):
        data={'itemListElement':[{'position':1,'name':'Home'},{'position':2,'name':'Price'}]};self.assertIn('breadcrumb_item_missing',self.names(self.check([entity('BreadcrumbList',data)],profile='google_breadcrumb')))
    def test_duplicate_breadcrumb_positions_detected(self):
        data={'itemListElement':[{'position':1,'name':'A','item':'/a'},{'position':1,'name':'B','item':'/b'}]};self.assertIn('breadcrumb_position_duplicate',self.names(self.check([entity('BreadcrumbList',data)])))
    def test_separate_breadcrumb_trails_not_cross_compared(self):
        a=entity('BreadcrumbList',{'itemListElement':[{'position':1,'name':'A','item':'/a'},{'position':2,'name':'B'}]});b=entity('BreadcrumbList',{'itemListElement':[{'position':1,'name':'C','item':'/c'},{'position':2,'name':'B'}]},path='$[1]')
        self.assertNotIn('breadcrumb_position_duplicate',self.names(self.check([a,b])))
    def test_breadcrumb_name_can_be_nested_item_name(self):
        r=self.check([entity('BreadcrumbList',{'itemListElement':[{'position':1,'item':{'@id':'/','name':'Home'}},{'position':2,'name':'Price'}]})],profile='google_breadcrumb');self.assertNotIn('breadcrumb_name_missing',self.names(r))
    def test_same_id_complementary_definitions_not_conflict(self):
        r=self.check([entity('Organization',{'name':'BingX'},id=URL+'#org'),entity('Organization',{'url':'https://bingx.com/'},path='$[1]',id=URL+'#org')]);self.assertNotIn('entity_field_conflict_review',self.names(r))
    def test_same_id_conflicting_name_is_review(self):
        r=self.check([entity('Product',{'name':'BTC'},id=URL+'#p'),entity('Product',{'name':'ETH'},path='$[1]',id=URL+'#p')]);self.assertIn('entity_field_conflict_review',self.names(r))
    def test_repeated_brand_literal_not_duplicate_id_reference_error(self):
        r=self.check([entity('Product',{'brand':['BingX','BingX']})]);self.assertIn('repeated_brand_value_review',self.names(r))
        r=self.check([entity('Product',{'brand':[{'@id':'#brand'},{'@id':'#brand'}]})]);self.assertNotIn('repeated_brand_value_review',self.names(r))
    def test_unknown_context_skipped_not_falsely_validated(self):
        r=self.check([entity(data={'price':'$1'},schema_context_known=False)]);self.assertEqual(r['observations'],[]);self.assertTrue(r['gaps'])
    def test_full_syntax_schema_engine_and_display_not_claimed_by_local_rules(self):
        r=self.check([entity(data={'price':1,'priceCurrency':'USD'})],profile='google_product_snippet')
        self.assertEqual(r['layers']['syntax'],'not_checked_here');self.assertEqual(r['layers']['schema_semantics'],'partial_rules_only');self.assertEqual(r['layers']['actual_display'],'unverified')
