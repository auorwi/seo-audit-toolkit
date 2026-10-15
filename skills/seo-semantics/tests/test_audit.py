import copy
from support import SemanticsTest,URL,AT
from test_rules import dom,node
from test_tool_reports import report,axe_rule

class SemanticAuditTests(SemanticsTest):
    def source(self,**kw):return dom([],snapshot_id='initial1',representation='source_elements',readiness=None,**kw)
    def audit(self,captures=None,reports=None,targets=None):
        return self.module('audit').audit(captures if captures is not None else [self.source(),dom([node('m','main'),node('h','h1','Prices')])],
            reports if reports is not None else [report('nu'),report()],targets or [URL],at=AT)

    def test_matching_current_tools_are_separate_from_semantic_review(self):
        result=self.audit();self.assertEqual(result['scope'],[URL]);self.assertEqual(result['coverage']['usable_tool_runs'],2)
        self.assertFalse(result['coverage']['full_accessibility_certification'])
        self.assertTrue(result['pending_reviews'])

    def test_nu_messages_group_by_problem_preserving_each_location(self):
        tool=report('nu');tool['payload']['messages']=[{'type':'error','message':'Attribute hid not allowed','firstLine':1,'firstColumn':5},{'type':'error','message':'Attribute hid not allowed','firstLine':1,'firstColumn':400}]
        result=self.audit(reports=[tool,report()]);items=[f for f in result['findings'] if f['rule']=='nu-message']
        self.assertEqual(len(items),1);self.assertEqual(len(items[0]['evidence']),2)
        self.assertEqual(items[0]['classification'],'html_conformance_error')

    def test_axe_incomplete_is_not_counted_as_violation(self):
        tool=report();tool['payload']['incomplete']=[axe_rule('bypass')]
        result=self.audit(reports=[report('nu'),tool])
        item=next(f for f in result['findings'] if f['rule']=='bypass')
        self.assertEqual(item['classification'],'manual_review')
        self.assertEqual(result['coverage']['confirmed_accessibility_observations'],0)

    def test_media_checker_findings_are_handoffs_not_duplicate_006_findings(self):
        tool=report();tool['payload']['violations']=[axe_rule('image-alt')]
        result=self.audit(reports=[report('nu'),tool])
        self.assertFalse(any(f['rule']=='image-alt' for f in result['findings']))
        self.assertEqual(result['handoffs'][0]['owner_skill'],'013')

    def test_wrong_document_checker_result_not_used_even_when_fresh(self):
        tool=report(document_sha256='b'*64,input_sha256='b'*64);tool['payload']['violations']=[axe_rule()]
        result=self.audit(reports=[report('nu'),tool])
        self.assertFalse(any(f['rule']=='button-name' for f in result['findings']))
        self.assertTrue(any(g['reason']=='checker_not_current_document' for g in result['gaps']))

    def test_latest_checker_failure_does_not_fall_back_to_old_pass(self):
        failed=report(state='timeout',checked_at='2026-09-17T00:30:00Z',capture_id='new-failure')
        result=self.audit(reports=[report('nu'),report(),failed])
        self.assertEqual(result['coverage']['usable_tool_runs'],1)
        self.assertTrue(result['gaps'])

    def test_latest_unready_dom_does_not_use_old_stable_document(self):
        latest=dom([node('h','h1')],snapshot_id='new',captured_at='2026-09-17T00:30:00Z',readiness='pending')
        result=self.audit(captures=[self.source(),dom([node('m','main')]),latest])
        self.assertEqual(result['coverage']['ready_documents'],0)
        self.assertFalse(any(f['rule']=='empty_heading' for f in result['findings']))

    def test_missing_nu_explicit_gap_and_selected_axe_only_scope(self):
        result=self.audit(reports=[report()]);self.assertTrue(any(g.get('tool')=='nu' for g in result['gaps']))
        selected=self.audit(reports=[report()],targets=[{'url':URL,'required_tools':['axe']}])
        self.assertFalse(any(g.get('tool')=='nu' for g in selected['gaps']))
        self.assertEqual(selected['coverage']['requested_tools'][URL],['axe'])

    def test_old_document_remains_gap_after_fresh_tool_rerun(self):
        result=self.audit(captures=[self.source(),dom([node('m','main')],captured_at='2020-01-01T00:00:00Z')])
        self.assertEqual(result['coverage']['ready_documents'],0);self.assertTrue(result['gaps'])

    def test_unknown_tool_or_empty_scope_rejected(self):
        with self.assertRaises(ValueError):self.audit(targets=[{'url':URL,'required_tools':['unknown']}])
        with self.assertRaises(ValueError):self.module('audit').audit([],[],[],at=AT)

    def test_conflicting_capture_id_cannot_silently_overwrite_evidence(self):
        first=dom([node('m','main')]);other=copy.deepcopy(first);other['document_sha256']='b'*64
        with self.assertRaises(ValueError):self.audit(captures=[first,other])

    def test_duplicate_input_not_double_counted_and_id_stable(self):
        tool=report();tool['payload']['violations']=[axe_rule()]
        first=self.audit(reports=[report('nu'),tool,tool]);second=self.audit(reports=[report('nu'),tool])
        self.assertEqual([f['issue_id'] for f in first['findings']],[f['issue_id'] for f in second['findings']])
        self.assertEqual(len([f for f in first['findings'] if f['rule']=='button-name']),1)
