import tempfile,copy
from support import IntegrityTest
from test_adapters import ManifestFixture
from test_calculator import trial
from test_comparison import AT

class ActionBindingTests(IntegrityTest):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.f=ManifestFixture(self.tmp.name)
        self.before=copy.deepcopy(self.f.capture);self.before['snapshot_id']='before'
        for c in [self.before,self.f.capture]:
            c['fields']={k:{'present':True,'visible':True,'count':1,'text':v,'value':v if k=='input' else None} for k,v in {'input':'10','output':'20.00','rate':'2.00','input_unit':'bitcoin','output_unit':'EUR'}.items()}
        self.before['fields']['input']['value']='1';self.before['fields']['output']['text']='2.00'
        p=trial();p.update(before_evidence_id='before',after_evidence_id='s1',rate_evidence_id='s1',action_id='a1')
        self.f.check.update(kind='calculator',payload=p,citations=[{'snapshot_id':'s1','field':k,'quote':v} for k,v in {'input':'10','output':'20.00','rate':'2.00'}.items()])
        self.f.review['snapshot_bindings']['before']=self.before['document_sha256']
        self.action={'action_id':'a1','source':'actual browser fill; no submit','before_snapshot':'before','after_snapshot':'s1','before_sha256':self.before['document_sha256'],'after_sha256':self.f.capture['document_sha256'],'status':'completed','requested_input':'10','applied_input':'10','direction':'asset_to_quote','started_at':AT,'finished_at':AT}
    def load(self):
        self.f.manifest['actions']=[self.f.save('action.json',self.action)];path=self.f.write()
        import json
        data=json.loads(path.read_text());data['captures'].append(self.f.save('before.json',self.before));path.write_text(json.dumps(data))
        return self.module('adapters').load_manifest(path,at=AT)
    def test_actual_action_binding_accepted(self):self.assertEqual(len(self.load()['checks']),1)
    def test_missing_action(self):self.f.check['payload']['action_id']='none';self.assertEqual(self.load()['checks'],[])
    def test_failed_action_cannot_be_promoted(self):self.action['status']='failed';self.assertEqual(self.load()['checks'],[])
    def test_applied_input_mismatch(self):self.action['applied_input']='1';self.assertEqual(self.load()['checks'],[])
    def test_actual_field_input_mismatch(self):self.f.capture['fields']['input']['value']='1';self.assertEqual(self.load()['checks'],[])
    def test_before_id_not_bound(self):self.f.check['payload']['before_evidence_id']='missing';self.assertEqual(self.load()['checks'],[])
    def test_rate_changed_not_false(self):self.before['fields']['rate']['text']='3.00';self.assertEqual(self.load()['checks'],[])
    def test_direction_mismatch(self):self.action['direction']='quote_to_asset';self.assertEqual(self.load()['checks'],[])
    def test_wrong_output_unit_mapping(self):self.f.capture['fields']['output_unit']['text']='USD';self.assertEqual(self.load()['checks'],[])
    def test_missing_before_review_binding(self):self.f.review['snapshot_bindings'].pop('before');self.assertEqual(self.load()['checks'],[])
    def test_calculator_output_in_input_value_is_evidence(self):
        self.f.capture['fields']['output']['value']='20.00';self.f.capture['fields']['output']['text']='';self.assertEqual(len(self.load()['checks']),1)
