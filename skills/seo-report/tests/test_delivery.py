import copy, importlib, json, pathlib, sys, tempfile, unittest, xml.etree.ElementTree as ET
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'scripts'))
try:
 from seo_report import delivery
except ImportError:delivery=None
class DeliveryTests(unittest.TestCase):
 def setUp(self):
  self.assertIsNotNone(delivery,'delivery missing');self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=pathlib.Path(self.tmp.name)
  self.issue={'issue_id':'x','rule':'route','url':'https://bingx.com/a?a=1&b=2','source_skill':'016','category':'review','status':'open','seen_in_run':True,'first_seen':'2026-09-17T01:00:00Z','last_seen':'2026-09-17T01:00:00Z','finding':{'classification':'review','recommendation':'<check> & fix','evidence':[{'quote':'actual'}]},'source':{'sha256':'a'*64,'path':'source.json'},'recheck':{'status':'failed'},'recheck_at':None}
  self.report={'run_id':'weekly-1','at':'2026-09-17T04:00:00Z','mode':'existing_evidence_consolidation','sources':[{'skill':'016','at':'2026-09-17T01:00:00Z','sha256':'a'*64,'path':'source.json','coverage':{'full_site':False},'gaps':[{'reason':'mobile'}],'input_gaps':[],'limitations':[],'finding_count':1,'platform_reports':[]}],'issues':[self.issue],'counts':{'review':1},'missing_skills':['001'],'source_report_window':['a','b'],'orphan_rechecks':[],'notes':['历史结果重排']}
 def test_xml_valid_and_escaped(self):
  docs=delivery.documents(self.report)
  for d in docs.values():
   for s in d['sections']:ET.fromstring(s['xml'])
  self.assertIn('&lt;check&gt;',json.dumps(docs))
 def test_report_historical_label(self):self.assertIn('现有审查结果汇总',str(delivery.documents(self.report)))
 def test_ledger_has_exact_id(self):self.assertIn('x',delivery.documents(self.report)['ledger']['sections'][0]['xml'])
 def test_report_contains_gaps(self):self.assertIn('mobile',str(delivery.documents(self.report)['report']))
 def test_report_preserves_source_hash(self):self.assertIn('a'*64,str(delivery.documents(self.report)))
 def test_same_issue_only_once_in_ledger(self):
  docs=delivery.documents(self.report);self.assertEqual(sum(s['xml'].count('ID: x;') for s in docs['ledger']['sections']),1)
 def test_deterministic_sections(self):self.assertEqual(delivery.documents(self.report),delivery.documents(copy.deepcopy(self.report)))
 def test_inventory_numbers_not_summed(self):self.assertNotIn('受影响页面总数',str(delivery.documents(self.report)))
 def test_csv_formula_escape(self):self.assertEqual(delivery.csv_safe('=SUM(1)'),"'=SUM(1)");self.assertEqual(delivery.csv_safe('https://x'),'https://x')
 def test_local_outputs(self):
  delivery.write_outputs(self.report,self.root/'out');self.assertTrue((self.root/'out/report.json').is_file());self.assertTrue((self.root/'out/issues.csv').is_file());self.assertTrue((self.root/'out/report.md').is_file())
 def test_existing_output_rejected(self):
  delivery.write_outputs(self.report,self.root/'out')
  with self.assertRaises(ValueError):delivery.write_outputs(self.report,self.root/'out')
 def test_links_not_invented(self):self.assertNotIn('https://fcnb',str(delivery.documents(self.report)))
