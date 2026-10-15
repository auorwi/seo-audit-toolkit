import copy, hashlib, importlib, json, pathlib, sqlite3, sys, tempfile, unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'scripts'))
try:
 from seo_report import core
except ImportError:
 core=None
AT='2026-09-17T04:00:00Z'
class CoreTests(unittest.TestCase):
 def setUp(self):
  self.assertIsNotNone(core,'018 core not implemented')
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=pathlib.Path(self.tmp.name)
  self.report={'skill':'016','at':'2026-09-17T03:00:00Z','coverage':{'all_site_verified':False},'findings':[{'issue_id':'same','rule':'entity','url':'https://bingx.com/en/x?a=1','classification':'reviewed_public_observation','recommendation':'核实路由','evidence':[{'quote':'BTC'}]}],'gaps':[{'reason':'missing mobile'}]}
  self.man={'run_id':'weekly-1','at':AT,'site':'bingx.com','sources':[]}
 def source(self,data=None,name='a.json',skill='016'):
  b=json.dumps(data or self.report,ensure_ascii=False).encode();(self.root/name).write_bytes(b)
  e={'skill':skill,'path':name,'sha256':hashlib.sha256(b).hexdigest()};self.man['sources'].append(e);return e
 def load(self):
  p=self.root/'manifest.json';p.write_text(json.dumps(self.man));return core.load_manifest(p)
 def build(self):return core.aggregate(self.load(),self.root/'state')
 def test_accept(self):self.source();self.assertEqual(self.build()['issues'][0]['issue_id'],'same')
 def test_hash_tamper_valid_json(self):
  self.source();(self.root/'a.json').write_text('{}')
  with self.assertRaises(ValueError):self.load()
 def test_escape(self):
  self.source()['path']='../x.json'
  with self.assertRaises(ValueError):self.load()
 def test_symlink(self):
  self.source();(self.root/'a.json').unlink();(self.root/'a.json').symlink_to('/etc/hosts')
  with self.assertRaises(ValueError):self.load()
 def test_missing_source(self):
  self.source();(self.root/'a.json').unlink()
  with self.assertRaises(ValueError):self.load()
 def test_duplicate_json_key(self):
  e=self.source();b=b'{"skill":"016","skill":"015"}';(self.root/'a.json').write_bytes(b);e['sha256']=hashlib.sha256(b).hexdigest()
  with self.assertRaises(ValueError):self.load()
 def test_nonfinite(self):
  self.report['x']=float('nan');self.source()
  with self.assertRaises(ValueError):self.load()
 def test_mismatch_skill(self):
  self.source(skill='015')
  with self.assertRaises(ValueError):self.load()
 def test_unknown_skill(self):
  self.source(skill='999')
  with self.assertRaises(ValueError):self.load()
 def test_future_source(self):
  self.report['at']='2030-01-01T00:00:00Z';self.source()
  with self.assertRaises(ValueError):self.load()
 def test_naive_time(self):
  self.man['at']='2026-09-17';self.source()
  with self.assertRaises(ValueError):self.load()
 def test_secret_key(self):
  self.report['access_token']='private';self.source()
  with self.assertRaises(ValueError):self.load()
 def test_secret_url(self):
  self.report['findings'][0]['url']='https://bingx.com/?access_token=secret';self.source()
  with self.assertRaises(ValueError):self.load()
 def test_missing_id(self):
  del self.report['findings'][0]['issue_id'];self.source()
  with self.assertRaises(ValueError):self.load()
 def test_fixture_rejected(self):
  self.report['run_kind']='fixture';self.source()
  with self.assertRaises(ValueError):self.load()
 def test_empty_manifest_rejected(self):
  with self.assertRaises(ValueError):self.load()
 def test_idempotent(self):
  self.source();a=self.build();b=self.build();self.assertEqual(a,b)
  with sqlite3.connect(self.root/'state/ledger.sqlite') as db:self.assertEqual(db.execute('select count(*) from observations').fetchone()[0],1)
 def test_url_parameters_distinct(self):
  f=copy.deepcopy(self.report['findings'][0]);f.update(issue_id='other',url='https://bingx.com/en/x?a=2');self.report['findings'].append(f);self.source();self.assertEqual(len(self.build()['issues']),2)
 def test_collision_fails_before_ledger_mutation(self):
  f=copy.deepcopy(self.report['findings'][0]);f['url']='https://bingx.com/en/y';self.report['findings'].append(f);self.source()
  with self.assertRaises(ValueError):self.build()
 def test_no_absence_closure(self):
  self.source();self.build();self.man['sources']=[];r=copy.deepcopy(self.report);r['findings']=[];r['at']='2026-09-17T03:30:00Z';self.source(r,'b.json');out=self.build();self.assertEqual(len(out['issues']),1);self.assertEqual(out['issues'][0]['status'],'open');self.assertFalse(out['issues'][0]['seen_in_run'])
 def test_old_replay_not_latest(self):
  self.source();self.build();self.man['sources']=[];r=copy.deepcopy(self.report);r['at']='2026-09-17T03:30:00Z';r['findings'][0]['recommendation']='new';self.source(r,'b.json');self.build();self.man['sources']=[];self.source();out=self.build();self.assertEqual(out['issues'][0]['finding']['recommendation'],'new')
 def test_first_last_seen(self):
  self.source();self.build();self.man['sources']=[];r=copy.deepcopy(self.report);r['at']='2026-09-17T03:30:00Z';self.source(r,'b.json');out=self.build()['issues'][0];self.assertEqual(out['first_seen'],'2026-09-17T03:00:00Z');self.assertEqual(out['last_seen'],'2026-09-17T03:30:00Z')
 def test_same_time_conflict_rejected(self):
  self.source();r=copy.deepcopy(self.report);r['findings'][0]['recommendation']='different';self.source(r,'b.json')
  with self.assertRaises(ValueError):self.build()
 def test_gaps_not_confirmed(self):
  self.report['findings'][0]['classification']='evidence_gap';self.source();out=self.build();self.assertEqual(out['counts']['evidence_gap'],1);self.assertEqual(out['counts'].get('confirmed',0),0)
 def test_environment_limited_not_confirmed(self):
  self.report['findings'][0]['classification']='provisional_observation_environment_limited';self.source();self.assertEqual(self.build()['issues'][0]['category'],'environment_limited')
 def test_engine_observation_not_defect(self):
  self.report['findings'][0]['classification']='engine_observation';self.source();self.assertEqual(self.build()['issues'][0]['category'],'platform_observation')
 def test_classification_preserved(self):
  self.source();self.assertEqual(self.build()['issues'][0]['finding']['classification'],'reviewed_public_observation')
 def test_full_site_never_inferred(self):
  self.source();x=self.build();self.assertFalse(x['full_site_verified']);self.assertEqual(x['mode'],'existing_evidence_consolidation')
 def test_coverage_retained(self):
  self.source();self.assertEqual(self.build()['sources'][0]['coverage'],self.report['coverage'])
 def test_001_adapter(self):
  self.source({'url_count':10,'whole_site_total':None,'coverage_claim':'discovered_inventory_only','generated_at':'2026-09-16T12:00:00Z'},skill='001');x=self.build();self.assertEqual(x['sources'][0]['coverage']['url_count'],10);self.assertFalse(x['full_site_verified'])
 def test_002_id_adapter(self):
  self.report['skill']='002-sitemap';f=self.report['findings'][0];f['id']=f.pop('issue_id');f['certainty']='confirmed';del f['classification'];self.source(skill='002');self.assertEqual(self.build()['issues'][0]['category'],'confirmed')
 def add_recheck(self,status='failed',issue='same'):
  r={'skill_id':'017','at':'2026-09-17T03:45:00Z','rechecks':[{'issue_id':issue,'rule':'entity','original_url':'https://bingx.com/en/x?a=1','status':status,'repair_verified':status=='passed','engine_recovery_confirmed':False}]};self.source(r,'recheck.json','017')
 def test_recheck_attached(self):
  self.source();self.add_recheck();x=self.build();self.assertEqual(len(x['issues']),1);self.assertEqual(x['issues'][0]['recheck']['status'],'failed')
 def test_pass_does_not_auto_close(self):
  self.source();self.add_recheck('passed');self.assertEqual(self.build()['issues'][0]['status'],'open')
 def test_orphan_recheck(self):
  self.source();self.add_recheck(issue='other');x=self.build();self.assertEqual(len(x['orphan_rechecks']),1);self.assertEqual(len(x['issues']),1)
 def test_recheck_url_mismatch(self):
  self.source();self.report['findings'][0]['url']='https://bingx.com/en/y';self.man['sources']=[];self.source();self.add_recheck()
  with self.assertRaises(ValueError):self.build()
 def test_rule_collisions_across_runs(self):
  self.source();self.build();self.report['findings'][0]['rule']='different';self.man['sources']=[];self.source()
  with self.assertRaises(ValueError):self.build()
 def test_missing_skills_visible(self):
  self.source();self.assertIn('014',self.build()['missing_skills'])
 def test_no_sum_platform_totals(self):
  self.report['platform_reports']=[{'total':100,'unit':'rows'},{'total':100,'unit':'rows'}];self.source();x=self.build();self.assertNotIn('affected_page_total',x);self.assertEqual(x['sources'][0]['platform_reports'],self.report['platform_reports'])
