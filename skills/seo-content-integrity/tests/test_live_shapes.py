from support import IntegrityTest
from test_comparison import AT,observation
from test_claims import claim

class LiveShapeTests(IntegrityTest):
    def pair(self):return [observation('62.8B',concept='circulating_supply',unit='XRP',temporal_kind='same_snapshot_assertions',snapshot_id='s1',data_at=None),observation('99,985,622,230.00',concept='circulating_supply',unit='XRP',temporal_kind='same_snapshot_assertions',snapshot_id='s1',data_at=None)]
    def test_same_snapshot_can_show_internally_conflicting_claims(self):self.assertEqual(self.module('comparison').check_pair(*self.pair(),at=AT)['status'],'conflict')
    def test_different_snapshots_cannot_bypass_live_time(self):
        a,b=self.pair();b['snapshot_id']='s2';self.assertEqual(self.module('comparison').check_pair(a,b,at=AT)['status'],'incomparable')
    def test_snapshot_id_required(self):
        a,b=self.pair();a.pop('snapshot_id');b.pop('snapshot_id');self.assertEqual(self.module('comparison').check_pair(a,b,at=AT)['status'],'incomparable')
    def test_malformed_e_numeric_output(self):self.assertEqual(self.module('claims').check_claim(claim('numeric_display',raw='E',expected_numeric=True),at=AT)['status'],'invalid_numeric_display')
    def test_placeholder_not_malformed_numeric_bug(self):self.assertEqual(self.module('claims').check_claim(claim('numeric_display',raw='--',expected_numeric=True),at=AT)['status'],'insufficient_data')
    def test_localized_numeric_not_false_error(self):self.assertEqual(self.module('claims').check_claim(claim('numeric_display',raw='0,00010',expected_numeric=True,decimal_mark=',',group_mark='.'),at=AT)['status'],'consistent')
    def test_non_numeric_display_raw_requires_citation(self):
        import tempfile
        from test_adapters import ManifestFixture
        with tempfile.TemporaryDirectory() as tmp:
            f=ManifestFixture(tmp);p=claim('numeric_display',raw='E',expected_numeric=True);p.pop('change');f.check.update(kind='claim',payload=p)
            self.assertEqual(self.module('adapters').load_manifest(f.write(),at=AT)['checks'],[])
    def test_same_snapshot_statement_id_must_refer_actual_capture(self):
        import tempfile
        from test_adapters import ManifestFixture
        with tempfile.TemporaryDirectory() as tmp:
            f=ManifestFixture(tmp)
            for row in f.check['payload'].values():row.update(temporal_kind='same_snapshot_assertions',snapshot_id='invented',data_at=None)
            self.assertEqual(self.module('adapters').load_manifest(f.write(),at=AT)['checks'],[])
