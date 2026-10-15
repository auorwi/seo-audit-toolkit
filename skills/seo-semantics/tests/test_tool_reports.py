import copy
from support import SemanticsTest,URL,AT

def report(tool='axe',**kw):
    payload={'url':URL,'testEngine':{'name':'axe-core','version':'4.10.3'},'violations':[],'incomplete':[],'passes':[],'inapplicable':[]}
    if tool=='nu':payload={'messages':[]}
    return {'tool':tool,'url':URL,'checked_at':'2026-09-17T00:00:00Z','source':'actual checker run',
        'capture_id':'capture-1','document_sha256':'a'*64,'input_sha256':'a'*64,'checker_version':'4.10.3' if tool=='axe' else '26.9.17',
        'state':'completed','representation':'rendered_dom' if tool=='axe' else 'initial_html','readiness':'ready','payload':payload,**kw}

def axe_rule(id='button-name',**kw):
    return {'id':id,'impact':'critical','description':'Button must have name','help':'Name buttons',
        'helpUrl':'https://dequeuniversity.com/rules/axe/4.10/button-name','tags':['wcag2a'],
        'nodes':[{'target':['#main > button'],'html':'<button></button>','failureSummary':'Fix name','any':[],'all':[],'none':[]}],**kw}

class ToolReportTests(SemanticsTest):
    def parse(self,data):return self.module('tool_reports').normalize_tool_report(data,at=AT)

    def test_axe_violation_keeps_element_and_accessibility_category(self):
        data=report();data['payload']['violations']=[axe_rule()]
        result=self.parse(data);self.assertEqual(result['status'],'usable')
        self.assertEqual(len(result['observations']),1)
        row=result['observations'][0]
        self.assertEqual(row['category'],'accessibility_violation');self.assertEqual(row['target'],['#main > button'])
        self.assertEqual(row['html'],'<button></button>');self.assertEqual(row['owner_skill'],'006')
        self.assertNotIn('ranking_penalty',row)

    def test_incomplete_is_manual_review_not_confirmed_violation(self):
        data=report();data['payload']['incomplete']=[axe_rule('color-contrast')]
        result=self.parse(data)
        self.assertEqual(result['observations'][0]['category'],'manual_review')
        self.assertTrue(result['coverage']['manual_review_required'])

    def test_empty_results_do_not_certify_whole_page_accessibility(self):
        result=self.parse(report())
        self.assertEqual(result['observations'],[])
        self.assertFalse(result['coverage']['full_accessibility_certification'])
        self.assertTrue(result['coverage']['manual_review_required'])

    def test_missing_result_arrays_are_evidence_gap(self):
        data=report();del data['payload']['incomplete']
        result=self.parse(data);self.assertEqual(result['status'],'evidence_gap');self.assertEqual(result['observations'],[])

    def test_axe_passes_count_rules_but_do_not_hide_incomplete(self):
        data=report();data['payload']['passes']=[axe_rule('label')];data['payload']['incomplete']=[axe_rule('button-name')]
        result=self.parse(data);self.assertEqual(result['coverage']['passed_rules'],1)
        self.assertEqual(len(result['observations']),1)

    def test_shadow_iframe_target_path_not_flattened(self):
        data=report();data['payload']['violations']=[axe_rule(nodes=[{'target':['#frame',['#host','button']],'html':'<button/>','failureSummary':'name'}])]
        self.assertEqual(self.parse(data)['observations'][0]['target'],['#frame',['#host','button']])

    def test_image_alt_handoff_preserves_evidence_without_second_owner(self):
        data=report();data['payload']['violations']=[axe_rule('image-alt')]
        row=self.parse(data)['observations'][0]
        self.assertEqual(row['owner_skill'],'013');self.assertEqual(row['category'],'accessibility_violation')
        self.assertTrue(row['handoff']);self.assertTrue(row['target'])

    def test_multiple_h1_best_practice_not_indexing_failure(self):
        data=report();data['payload']['violations']=[axe_rule('page-has-heading-one',tags=['best-practice'])]
        row=self.parse(data)['observations'][0]
        self.assertEqual(row['category'],'accessibility_best_practice')
        self.assertEqual(row['tags'],['best-practice'])

    def test_nu_error_and_warning_keep_source_positions(self):
        data=report('nu');data['payload']['messages']=[{'type':'error','message':'Element div not allowed here','firstLine':4,'lastLine':4,'firstColumn':2,'lastColumn':8,'extract':'<ul><div>x</div></ul>'},{'type':'info','subType':'warning','message':'Consider adding a heading'}]
        result=self.parse(data);self.assertEqual(result['status'],'usable')
        self.assertEqual([x['category'] for x in result['observations']],['html_conformance_error','html_conformance_warning'])
        self.assertEqual(result['observations'][0]['location']['firstLine'],4)
        self.assertEqual(result['observations'][0]['html'],'<ul><div>x</div></ul>')

    def test_nu_clean_result_is_only_html_checker_result(self):
        result=self.parse(report('nu'));self.assertEqual(result['status'],'usable');self.assertEqual(result['observations'],[])
        self.assertFalse(result['coverage']['full_accessibility_certification'])

    def test_nu_fatal_execution_message_not_page_violation(self):
        data=report('nu');data['payload']['messages']=[{'type':'non-document-error','message':'Cannot read input'}]
        result=self.parse(data);self.assertEqual(result['status'],'evidence_gap');self.assertEqual(result['observations'],[])

    def test_wrong_document_hash_rejects_report(self):
        result=self.parse(report(input_sha256='b'*64));self.assertEqual(result['status'],'evidence_gap')
        self.assertEqual(result['observations'],[])

    def test_axe_wrong_url_is_not_assigned_to_requested_page(self):
        data=report();data['payload']['url']='https://bingx.com/en/other'
        self.assertEqual(self.parse(data)['status'],'evidence_gap')

    def test_axe_initial_html_is_not_claimed_as_actual_rendered_audit(self):
        self.assertEqual(self.parse(report(representation='initial_html'))['status'],'evidence_gap')

    def test_unready_dom_not_accepted_as_stable_semantics(self):
        self.assertEqual(self.parse(report(readiness='pending'))['status'],'evidence_gap')

    def test_stale_future_and_invalid_time_are_gaps(self):
        for t in ['2020-01-01T00:00:00Z','2027-01-01T00:00:00Z','not-time']:
            self.assertEqual(self.parse(report(checked_at=t))['status'],'evidence_gap')

    def test_tool_timeout_and_missing_version_do_not_pass(self):
        for kw in [{'state':'timeout'},{'checker_version':''},{'capture_id':''}]:
            self.assertEqual(self.parse(report(**kw))['status'],'evidence_gap')

    def test_axe_reported_version_must_match_capture_metadata(self):
        self.assertEqual(self.parse(report(checker_version='9.9.9'))['status'],'evidence_gap')

    def test_malformed_nodes_or_messages_are_not_empty_success(self):
        for tool,payload in [('axe',{'violations':[axe_rule(nodes='invalid')]}),('nu',{'messages':'invalid'})]:
            data=report(tool);data['payload'].update(payload)
            self.assertEqual(self.parse(data)['status'],'evidence_gap')

    def test_invalid_hash_is_gap_even_if_both_hashes_match(self):
        self.assertEqual(self.parse(report(input_sha256='abc',document_sha256='abc'))['status'],'evidence_gap')

    def test_input_data_remains_unchanged(self):
        data=report();data['payload']['violations']=[axe_rule()];before=copy.deepcopy(data)
        self.parse(data);self.assertEqual(data,before)

    def test_changed_dom_after_checker_cannot_be_marked_completed(self):
        result=self.parse(report(after_sha256='b'*64))
        self.assertEqual(result['status'],'evidence_gap')
        self.assertEqual(result['observations'],[])

    def test_matching_after_hash_remains_usable(self):
        self.assertEqual(self.parse(report(after_sha256='a'*64))['status'],'usable')
