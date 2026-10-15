import tempfile
from pathlib import Path
from support import CrawlTest, AT

class LedgerTests(CrawlTest):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name)/'issues.sqlite'

    def result(self,at=AT,findings=None):
        return {'at':at,'scope':['https://bingx.com/en'],'findings':findings if findings is not None else [{'issue_id':'crawl-a','rule':'noindex','url':'https://bingx.com/en','agent':'Googlebot','evidence':{'status':200},'observed_at':at}]}

    def test_repeated_issue_updates_history_instead_of_duplicate_issue(self):
        ledger=self.module('ledger')
        ledger.record(self.path,self.result());ledger.record(self.path,self.result('2026-09-17T12:00:00Z'))
        rows=ledger.history(self.path)
        self.assertEqual(len(rows),1);self.assertEqual(rows[0]['sightings'],2)
        self.assertEqual(rows[0]['first_seen'],AT);self.assertEqual(rows[0]['last_seen'],'2026-09-17T12:00:00Z')

    def test_identical_rerun_is_idempotent(self):
        ledger=self.module('ledger')
        a=ledger.record(self.path,self.result());b=ledger.record(self.path,self.result())
        self.assertEqual(a,b);self.assertEqual(ledger.history(self.path)[0]['sightings'],1)

    def test_absence_from_later_sample_does_not_auto_resolve(self):
        ledger=self.module('ledger');ledger.record(self.path,self.result())
        ledger.record(self.path,self.result('2026-09-17T12:00:00Z',[]))
        self.assertEqual(ledger.history(self.path)[0]['status'],'open')

    def test_out_of_order_import_keeps_latest_payload_and_chronological_bounds(self):
        ledger=self.module('ledger');new=self.result('2026-09-17T12:00:00Z')
        new['findings'][0]['evidence']={'status':503}
        ledger.record(self.path,new);ledger.record(self.path,self.result())
        row=ledger.history(self.path)[0]
        self.assertEqual(row['payload']['evidence']['status'],503)
        self.assertEqual(row['first_seen'],AT)

    def test_different_engine_issue_remains_separate(self):
        ledger=self.module('ledger');result=self.result()
        result['findings'].append({**result['findings'][0],'issue_id':'crawl-b','agent':'Bingbot'})
        ledger.record(self.path,result);self.assertEqual(len(ledger.history(self.path)),2)

    def test_invalid_report_cannot_partially_modify_history(self):
        ledger=self.module('ledger');ledger.record(self.path,self.result())
        bad=self.result('bad-timestamp')
        with self.assertRaises(ValueError):ledger.record(self.path,bad)
        self.assertEqual(ledger.history(self.path)[0]['sightings'],1)
