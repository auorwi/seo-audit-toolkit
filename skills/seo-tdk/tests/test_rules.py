from support import TdkTest,AT
from test_context import capture,context,fact,external_fact
class RuleTests(TdkTest):
    def audit(self,c=None,ctx=None):return self.module('rules').audit_page(c or capture(),ctx if ctx is not None else context(),at=AT)
    def fields(self,**kw):
        c=capture();c['fields'].update(kw);return c
    def names(self,r):return {f['rule'] for f in r['findings']}
    def test_good_metadata_no_missing_title_or_keywords_task(self):
        r=self.audit();self.assertNotIn('missing_title',self.names(r));self.assertFalse(any('keyword' in x for x in self.names(r)))
    def test_missing_title_and_description_are_separate(self):
        self.assertEqual({'missing_title','missing_description'}&self.names(self.audit(self.fields(titles=[],descriptions=[]))),{'missing_title','missing_description'})
    def test_empty_tag_differs_from_absent(self):
        names=self.names(self.audit(self.fields(titles=[{'value':' '}],descriptions=[{'value':None}])))
        self.assertIn('empty_title',names);self.assertIn('empty_description',names)
    def test_identical_duplicate_nodes_still_duplicate(self):
        names=self.names(self.audit(self.fields(titles=[{'value':'SOLV'},{'value':'SOLV'}],descriptions=[{'value':'A'},{'value':'B'}])))
        self.assertIn('duplicate_title_nodes',names);self.assertIn('duplicate_description_nodes',names)
    def test_unfinished_head_does_not_confirm_absent_metadata(self):
        c=self.fields(titles=[],coverage={'head_seen':True,'closed_head':False,'body_complete':True});r=self.audit(c)
        self.assertNotIn('missing_title',self.names(r));self.assertTrue(r['gaps'])
    def test_unready_and_stale_do_not_produce_page_defects(self):
        for c in [capture(readiness='pending'),capture(captured_at='2020-01-01T00:00:00Z')]:
            r=self.audit(c);self.assertFalse(r['findings']);self.assertTrue(r['gaps'])
    def test_long_title_is_advisory_never_hard_limit(self):
        r=self.audit(self.fields(titles=[{'value':'Long descriptive SOLV project title '*5}]))
        row=next(f for f in r['findings'] if f['rule']=='title_length_review');self.assertEqual(row['classification'],'display_advisory')
    def test_template_placeholders_and_known_translation_key(self):
        r=self.audit(self.fields(titles=[{'value':'Buy {{coin}} | BingX'}],descriptions=[{'value':'seo.launchpad.description'}]),context(translation_keys=['seo.launchpad.description']))
        self.assertIn('unexpanded_placeholder',self.names(r));self.assertIn('translation_key',self.names(r))
    def test_coin_symbols_and_ordinary_word_nullify_not_placeholder(self):
        self.assertNotIn('unexpanded_placeholder',self.names(self.audit(self.fields(titles=[{'value':'SOLV nullify policy'}]))))
    def test_half_empty_brand_title_is_review(self):
        self.assertIn('half_empty_title',self.names(self.audit(self.fields(titles=[{'value':' | BingX'}]))))
    def test_empty_country_slot_is_template_specific(self):
        c=self.fields(titles=[{'value':'Buy Bitcoin in | BingX'}])
        self.assertIn('empty_country_slot',self.names(self.audit(c,context(template='buy_crypto'))))
        self.assertNotIn('empty_country_slot',self.names(self.audit(c,context(template='article'))))
    def test_required_country_with_fact_detects_omission(self):
        ctx=context(facts=[external_fact('country','country','Brazil')],requirements=[{'field':'title','fact_id':'country'}])
        r=self.audit(ctx=ctx);self.assertIn('required_fact_missing',self.names(r))
    def test_unknown_required_country_is_gap_not_invented_fix(self):
        r=self.audit(ctx=context(requirements=[{'field':'title','fact_id':'unknown'}]));self.assertNotIn('required_fact_missing',self.names(r));self.assertTrue(r['gaps'])
    def test_route_gold_body_btc_handoff_not_title_only_fix(self):
        c=self.fields(body_text='BTC Project Details',titles=[{'value':'Gold price | BingX'}])
        ctx=context(facts=[fact(value='BTC',aliases=['BTC'],quote='BTC Project Details'),external_fact('route','route_entity','Gold')],requirements=[{'field':'title','fact_id':'page'}])
        r=self.audit(c,ctx);self.assertEqual({h['owner_skill'] for h in r['handoffs']},{'004','012'})
        self.assertNotIn('required_fact_missing',self.names(r));self.assertTrue(r['rewrite_blocked'])
    def test_product_category_mismatch_handoff(self):
        c=self.fields(body_text='SOLV spot trading')
        ctx=context(facts=[fact('product','page_product','spot',quote='SOLV spot trading'),external_fact('routeprod','route_product','futures')])
        self.assertTrue(self.audit(c,ctx)['rewrite_blocked'])
    def test_unlisted_asset_trade_claim_needs_content_review(self):
        c=self.fields(titles=[{'value':'Trade SOLV now | BingX'}])
        r=self.audit(c,context(facts=[fact(),external_fact('status','listing_status','not_listed','product_catalog')]))
        self.assertIn('availability_claim_conflict',self.names(r));self.assertTrue(r['rewrite_blocked'])
        self.assertTrue(any(h['owner_skill']=='012' for h in r['handoffs']))
    def test_unknown_listing_status_does_not_invent_listing(self):
        r=self.audit(self.fields(titles=[{'value':'Trade SOLV now | BingX'}]))
        self.assertNotIn('availability_claim_conflict',self.names(r));self.assertIn('product_availability',r['pending_reviews'])
    def test_dynamic_title_keeps_required_entity_and_pair(self):
        c=self.fields(titles=[{'value':'$3,456.12 ETH/USDT | BingX'}])
        ctx=context(facts=[external_fact('btc','route_entity','BTC')],dynamic_title={'enabled':True,'stable_fact_ids':['btc']})
        self.assertIn('dynamic_stable_field_missing',self.names(self.audit(c,ctx)))
    def test_price_change_alone_not_entity_mismatch(self):
        c=self.fields(titles=[{'value':'$123.45 SOLV | BingX'}])
        ctx=context(dynamic_title={'enabled':True,'stable_fact_ids':['page']})
        self.assertNotIn('dynamic_stable_field_missing',self.names(self.audit(c,ctx)))
    def test_source_observation_not_labeled_current_rendered_defect(self):
        c=self.fields(titles=[]);c.update(representation='initial_html',readiness=None)
        r=self.audit(c);f=next(f for f in r['findings'] if f['rule']=='missing_title')
        self.assertEqual(f['classification'],'initial_html_observation');self.assertTrue(r['gaps'])
    def test_stable_issue_id_ignores_changed_wrong_value(self):
        a=self.audit(self.fields(titles=[{'value':'{{coin}}'}]));b=self.audit(self.fields(titles=[{'value':'${coin}'}]))
        self.assertEqual(next(x['issue_id'] for x in a['findings'] if x['rule']=='unexpanded_placeholder'),next(x['issue_id'] for x in b['findings'] if x['rule']=='unexpanded_placeholder'))
    def test_catalog_for_another_asset_does_not_confirm_availability_conflict(self):
        status=external_fact('status','listing_status','not_listed','product_catalog',text='ETH spot not_listed')
        status['subject']={'entity':'ETH','product':'spot','market_scope':'unknown'}
        r=self.audit(self.fields(titles=[{'value':'Trade SOLV now'}]),context(facts=[fact(),status]))
        self.assertNotIn('availability_claim_conflict',self.names(r));self.assertTrue(r['gaps'])
    def test_catalog_missing_subject_cannot_confirm_availability(self):
        status=external_fact('status','listing_status','not_listed','product_catalog');status.pop('subject',None)
        r=self.audit(self.fields(titles=[{'value':'Trade SOLV now'}]),context(facts=[fact(),status]))
        self.assertNotIn('availability_claim_conflict',self.names(r));self.assertTrue(r['gaps'])
