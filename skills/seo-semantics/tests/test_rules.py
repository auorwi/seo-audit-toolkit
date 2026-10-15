from support import SemanticsTest,URL,AT


def dom(nodes,**kw):
    return {'url':URL,'snapshot_id':'dom1','captured_at':'2026-09-17T00:00:00Z','source':'browser elements',
        'document_sha256':'a'*64,'representation':'rendered_elements','readiness':'ready','scope':'document',
        'coverage':{'nodes':'complete','visibility':'complete','accessible_names':'complete'},'nodes':nodes,**kw}

def node(id,tag,text='',**kw):
    return {'node_id':id,'tag':tag,'selector':'#'+id,'attributes':{},'text':text,'accessible_name':text,'visibility':'visible','parent_id':None,'ancestor_tags':[],**kw}

class SemanticRuleTests(SemanticsTest):
    def test_two_unnamed_navigation_landmarks_need_disambiguation_review(self):
        result=self.audit(dom([node('m','main'),node('n1','nav'),node('n2','nav')]))
        self.assertIn('navigation_landmark_name_review',self.rules(result))

    def test_distinct_navigation_names_do_not_trigger_missing_name_review(self):
        result=self.audit(dom([node('m','main'),node('n1','nav',accessible_name='Primary'),node('n2','nav',accessible_name='Related')]))
        self.assertNotIn('navigation_landmark_name_review',self.rules(result))

    def test_orphan_list_item_is_structure_review(self):
        result=self.audit(dom([node('m','main'),node('li','li','BTC',parent_id='m')]))
        self.assertIn('list_structure_review',self.rules(result))

    def test_native_and_aria_lists_do_not_create_orphan_findings(self):
        result=self.audit(dom([node('m','main'),node('list','div',attributes={'role':'list'}),node('item','div','BTC',attributes={'role':'listitem'},parent_id='list'),node('menu','menu'),node('li','li','ETH',parent_id='menu')]))
        self.assertNotIn('list_structure_review',self.rules(result))

    def review(self,**kw):
        return {'snapshot_id':'dom1','document_sha256':'a'*64,'source':'model review of actual captured DOM','checked_at':'2026-09-17T00:00:00Z',
            'topic':'heading_topic_hierarchy','status':'needs_change','nodes':['h'],'quotes':{'h':'FAQ'},'reason':'This FAQ heading introduces product overview content.',
            'recommendation':'Align the heading with the observed product overview section.','retest':'Re-read heading and following section in the stable page.',**kw}

    def test_model_review_keeps_provenance_and_is_not_indexing_fact(self):
        result=self.audit(dom([node('m','main'),node('h','h2','FAQ')],semantic_reviews=[self.review()]))
        row=next((f for f in result['findings'] if f['rule']=='model_semantic_review'),None)
        self.assertIsNotNone(row)
        self.assertEqual(row['classification'],'model_review');self.assertEqual(row['locator']['selector'],'#h')
        self.assertIn('heading_topic_hierarchy',result['reviewed_topics'])

    def test_wrong_snapshot_or_unmatched_quote_cannot_be_presented_as_review_evidence(self):
        for review in [self.review(snapshot_id='old'),self.review(quotes={'h':'Not in the page'})]:
            result=self.audit(dom([node('m','main'),node('h','h2','FAQ')],semantic_reviews=[review]))
            self.assertNotIn('model_semantic_review',self.rules(result));self.assertIn('semantic_review_evidence',result['gaps'])

    def audit(self,capture,**kw):return self.module('rules').audit_elements(capture,at=AT,**kw)
    def rules(self,result):return {r['rule'] for r in result['findings']}

    def test_empty_visible_heading_has_element_evidence_and_fix(self):
        result=self.audit(dom([node('m','main'),node('h','h1')]))
        self.assertIn('empty_heading',self.rules(result))
        row=next(f for f in result['findings'] if f['rule']=='empty_heading')
        self.assertEqual(row['locator']['selector'],'#h');self.assertTrue(row['recommendation']);self.assertTrue(row['retest'])
        self.assertEqual(row['impact_domain'],'semantic_structure')

    def test_hidden_duplicate_h1_is_not_multiple_h1_failure(self):
        result=self.audit(dom([node('m','main'),node('h1','h1','Price'),node('h2','h1','Price',visibility='hidden')]))
        self.assertNotIn('multiple_h1',self.rules(result));self.assertNotIn('empty_heading',self.rules(result))

    def test_multiple_nonempty_h1_not_automatic_indexing_error(self):
        result=self.audit(dom([node('m','main'),node('a','h1','Prices'),node('b','h1','FAQ')]))
        self.assertFalse(any(f['rule'] in {'multiple_h1','indexing_error'} for f in result['findings']))
        self.assertIn('heading_topic_hierarchy',result['pending_reviews'])

    def test_heading_with_accessible_name_is_not_empty(self):
        result=self.audit(dom([node('m','main'),node('h','h1','',accessible_name='Market prices')]))
        self.assertNotIn('empty_heading',self.rules(result))

    def test_unknown_visibility_not_claimed_visible_heading_failure(self):
        result=self.audit(dom([node('h','h1',visibility='unknown')]))
        self.assertNotIn('empty_heading',self.rules(result));self.assertIn('visibility',result['gaps'])

    def test_heading_jump_is_review_not_html_conformance_error(self):
        result=self.audit(dom([node('m','main'),node('a','h1','Prices'),node('b','h3','Bitcoin')]))
        row=next(f for f in result['findings'] if f['rule']=='heading_level_review')
        self.assertEqual(row['classification'],'semantic_review')

    def test_missing_main_requires_complete_document_dom(self):
        self.assertIn('main_landmark_missing',self.rules(self.audit(dom([node('h','h1','Prices')]))))
        for override in [{'scope':'subtree'},{'coverage':{'nodes':'partial'}},{'readiness':'pending'}]:
            self.assertNotIn('main_landmark_missing',self.rules(self.audit(dom([node('h','h1','Prices')],**override))))

    def test_role_main_counts_as_landmark(self):
        result=self.audit(dom([node('m','div',attributes={'role':'main'}),node('h','h1','Prices')]))
        self.assertNotIn('main_landmark_missing',self.rules(result))

    def test_source_html_does_not_claim_rendered_name_or_visibility(self):
        result=self.audit(dom([node('h','h1')],representation='source_elements',readiness=None))
        self.assertNotIn('empty_heading',self.rules(result));self.assertTrue(result['gaps'])

    def test_empty_button_and_form_names_are_separate_elements(self):
        result=self.audit(dom([node('m','main'),node('b','button'),node('q','input',attributes={'type':'search'})]))
        self.assertIn('control_name_missing',self.rules(result))
        names=[f['locator']['selector'] for f in result['findings'] if f['rule']=='control_name_missing']
        self.assertEqual(names,['#b','#q'])

    def test_hidden_input_and_known_named_control_are_not_missing_name(self):
        result=self.audit(dom([node('m','main'),node('hidden','input',attributes={'type':'hidden'}),node('q','input','',accessible_name='Search')]))
        self.assertNotIn('control_name_missing',self.rules(result))

    def test_unknown_accessible_name_is_gap_not_empty_name(self):
        result=self.audit(dom([node('m','main'),node('b','button',accessible_name=None)]))
        self.assertNotIn('control_name_missing',self.rules(result));self.assertIn('accessible_names',result['gaps'])

    def test_iframe_name_missing_is_accessibility_review(self):
        result=self.audit(dom([node('m','main'),node('f','iframe')]))
        self.assertIn('iframe_name_missing',self.rules(result))

    def test_role_link_without_real_href_is_discovery_candidate(self):
        result=self.audit(dom([node('m','main'),node('l','div','Project',attributes={'role':'link'})]))
        row=next(f for f in result['findings'] if f['rule']=='navigation_without_crawlable_href')
        self.assertEqual(row['impact_domain'],'seo_discovery')
        self.assertEqual(row['classification'],'semantic_review')

    def test_fragment_link_and_regular_button_are_not_automatically_wrong(self):
        result=self.audit(dom([node('m','main'),node('l','a','FAQ',attributes={'href':'#faq'}),node('b','button','Sort')]))
        self.assertNotIn('navigation_without_crawlable_href',self.rules(result))

    def test_observed_button_navigation_gets_link_recommendation(self):
        purpose={'node_id':'b','snapshot_id':'dom1','document_sha256':'a'*64,'purpose':'navigation','target_url':'https://bingx.com/en/price/bitcoin','source':'actual public click trace','checked_at':'2026-09-17T00:00:00Z'}
        result=self.audit(dom([node('m','main'),node('b','button','Bitcoin')]),purposes=[purpose])
        self.assertIn('navigation_without_crawlable_href',self.rules(result))

    def test_purpose_bound_to_old_snapshot_cannot_reclassify_button(self):
        purpose={'node_id':'b','snapshot_id':'old','document_sha256':'a'*64,'purpose':'navigation','target_url':'https://bingx.com/en/price/bitcoin','source':'trace','checked_at':'2026-09-17T00:00:00Z'}
        result=self.audit(dom([node('m','main'),node('b','button','Bitcoin')]),purposes=[purpose])
        self.assertNotIn('navigation_without_crawlable_href',self.rules(result));self.assertIn('purpose_evidence_binding',result['gaps'])

    def test_layout_table_not_called_data_table_without_headers(self):
        result=self.audit(dom([node('m','main'),node('t','table',attributes={'role':'presentation'})]))
        self.assertNotIn('table_header_review',self.rules(result))

    def test_table_without_headers_needs_data_purpose_review(self):
        result=self.audit(dom([node('m','main'),node('t','table'),node('cell','td','BTC',parent_id='t',ancestor_tags=['table'])]))
        self.assertIn('table_header_review',self.rules(result))
        self.assertTrue(any(f['classification']=='semantic_review' for f in result['findings'] if f['rule']=='table_header_review'))

    def test_empty_alt_is_handoff_question_not_automatic_image_failure(self):
        result=self.audit(dom([node('m','main'),node('img','img',attributes={'alt':''})]))
        self.assertFalse(any(f['rule']=='empty_alt' for f in result['findings']))
        self.assertEqual(result['handoffs'][0]['owner_skill'],'013')
        self.assertEqual(result['handoffs'][0]['question'],'decorative_or_informative')

    def test_stale_or_unready_dom_does_not_return_current_findings(self):
        for override in [{'captured_at':'2020-01-01T00:00:00Z'},{'readiness':'pending'}]:
            result=self.audit(dom([node('h','h1')],**override))
            self.assertEqual(result['findings'],[]);self.assertTrue(result['gaps'])

    def test_issue_id_stable_and_elements_separate(self):
        data=dom([node('m','main'),node('a','button'),node('b','button')])
        first=self.audit(data);second=self.audit(data)
        ids=[x['issue_id'] for x in first['findings'] if x['rule']=='control_name_missing']
        self.assertEqual(len(set(ids)),2)
        self.assertEqual([x['issue_id'] for x in first['findings']],[x['issue_id'] for x in second['findings']])
