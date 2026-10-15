"""Regression cases prompted by the actual Prologis Google live test, without treating fixtures as live evidence."""
import unittest
from test_audit import api,live,data,ui,AT,URL
from gsc_audit.audit import audit

class LiveTestFindings(unittest.TestCase):
    def observation(self,rule='rich_result_error'):
        return ui(report='live_test',kind='live_test',count_unit='items',reported_total=1,rows=[{'url':URL,'device':'MOBILE','reason_key':rule,'reason_label':"Invalid floating point number in property 'price'",'quote':"Invalid floating point number in property 'price'"}])
    def test_live_rich_error_retained_and_referred_without_indexing_claim(self):
        r=audit(data(self.observation(),live()),at=AT)
        self.assertEqual(len(r['findings']),1)
        self.assertEqual(r['findings'][0]['classification'],'live_test_observation')
        self.assertEqual(r['findings'][0]['report'],'rich_results')
        self.assertEqual(r['referrals'][0]['owner_skill'],'008')
        self.assertEqual(r['coverage']['indexed_url_observations'],0)
        self.assertFalse(r['checks'][0]['google_fixed'])
        self.assertFalse(r['findings'][0]['underlying_defect_confirmed'])
    def test_historical_server_error_remains_alongside_live_schema_error(self):
        r=audit(data(api(),live(),self.observation()),at=AT)
        self.assertEqual({f['rule'] for f in r['findings']},{'server_error','rich_result_error'})
        self.assertEqual(r['checks'][0]['comparison'],'historical_error_not_reproduced')
        self.assertEqual(len(r['referrals']),2)
    def test_unknown_live_issue_retained_for_review_not_indexed(self):
        r=audit(data(self.observation('unknown_live_issue')),at=AT)
        self.assertEqual(len(r['findings']),1)
        self.assertEqual(r['findings'][0]['report'],'live_test')
        self.assertEqual(r['findings'][0]['classification'],'live_test_observation')
        self.assertEqual(r['coverage']['indexed_url_observations'],0)
    def test_live_available_remains_non_issue(self):
        self.assertEqual(audit(data(self.observation('available')),at=AT)['findings'],[])
    def test_same_live_and_index_rich_issue_uses_same_id_and_both_modes(self):
        past=ui(report='rich_results',count_unit='items',rows=self.observation()['data']['rows']);past['id']='historical'
        for order in [(past,self.observation()),(self.observation(),past)]:
            r=audit(data(*order),at=AT)
            self.assertEqual(len(r['findings']),1)
            self.assertEqual(len(r['findings'][0]['evidence']),2)
            self.assertEqual(set(r['findings'][0]['observation_modes']),{'engine_observation','live_test_observation'})
            self.assertEqual(r['findings'][0]['classification'],'mixed_platform_observation')
            self.assertEqual(len(r['referrals']),1)

class HumanLiveEvidence(unittest.TestCase):
    def test_human_report_shows_only_matching_url_row_quotes(self):
        import tempfile
        from pathlib import Path
        from gsc_audit.report import write_report
        o=LiveTestFindings().observation()
        o['data']['rows'].append({'url':URL+'/unrelated','device':'MOBILE','reason_key':'available','reason_label':'unrelated text','quote':'unrelated text'})
        r=audit(data(o),at=AT)
        with tempfile.TemporaryDirectory() as t:
            write_report(Path(t),r,[])
            import html
            s=html.unescape((Path(t)/'report.md').read_text())
            self.assertIn("Invalid floating point number in property 'price'",s)
            self.assertNotIn('unrelated text',s)

class UIIndexedEnhancements(unittest.TestCase):
    def test_ui_inspection_keeps_enhancement_rows_and_index_snapshot(self):
        o=ui(report='url_inspection',inspection=api(verdict='PASS',pageFetchState='SUCCESSFUL')['data'],rows=LiveTestFindings().observation()['data']['rows'])
        r=audit(data(o,live()),at=AT)
        self.assertEqual(r['coverage']['indexed_url_observations'],1)
        self.assertEqual(len(r['findings']),1)
        self.assertEqual(r['findings'][0]['report'],'rich_results')
        self.assertEqual(r['findings'][0]['classification'],'engine_observation')
        self.assertEqual(r['referrals'][0]['owner_skill'],'008')

if __name__=='__main__':unittest.main()
