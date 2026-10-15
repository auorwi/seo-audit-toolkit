from support import MediaTest
from copy import deepcopy
AT='2026-09-16T23:00:00Z';URL='https://bingx.com/en/'
def sample(**kw):
    row={'slot':'img#hero','tag':'img','current_src':'https://bingx.com/bad.png','complete':True,'natural_width':0,'natural_height':0,
         'error_event_src':'https://bingx.com/bad.png','decode':{'result':'rejected','current_src':'https://bingx.com/bad.png'},'captured_at':AT,'alt_present':True,'alt':'hero'}
    return {'snapshot_id':'a','requested_url':URL,'url':URL,'device':'desktop','captured_at':AT,'readiness':'ready','media':[row],'responses':[],'gaps':[],**kw}
def inputs(capture=None):return {'scope':[{'url':URL,'devices':['desktop']}],'captures':[capture or sample()],'reviews':{},'gaps':[]}
class AuditTests(MediaTest):
    def check(self,data=None):return self.module('audit').audit(data or inputs(),at=AT)
    def first(self,result):self.assertEqual(len(result['findings']),1);return result['findings'][0]
    def test_actual_browser_failure_is_confirmed(self):
        f=self.first(self.check());self.assertEqual(f['rule'],'browser_image_failure');self.assertEqual(f['classification'],'confirmed')
    def test_unknown_purpose_remains_gap(self):self.assertIn('purpose_unreviewed',str(self.check()['gaps']))
    def test_repeated_captures_same_issue_one_record(self):
        data=inputs();data['captures'].append(sample(snapshot_id='b'));r=self.check(data);self.assertEqual(len(r['findings']),1);self.assertEqual(len(r['findings'][0]['evidence']),2)
    def test_mobile_same_problem_aggregates_with_context(self):
        data=inputs();data['scope'][0]['devices'].append('mobile');data['captures'].append(sample(snapshot_id='b',device='mobile'));r=self.check(data);self.assertEqual(len(r['findings']),1);self.assertEqual({x['device'] for x in r['findings'][0]['evidence']},{'desktop','mobile'})
    def test_missing_mobile_scope_not_completed(self):
        data=inputs();data['scope'][0]['devices'].append('mobile');self.assertEqual(self.check(data)['coverage']['captured_declared_variants'],1);self.assertFalse(self.check(data)['coverage']['declared_checks_complete'])
    def test_unready_page_not_used_to_confirm_issue(self):self.assertEqual(self.check(inputs(sample(readiness='unknown')))['findings'],[])
    def test_wrong_landing_not_audited_as_requested_page(self):self.assertEqual(self.check(inputs(sample(url='https://bingx.com/zh-tc/')))['findings'],[])
    def test_stale_capture_excluded(self):self.assertEqual(self.check(inputs(sample(captured_at='2024-01-01T00:00:00Z')))['findings'],[])
    def test_out_of_scope_not_counted(self):self.assertEqual(self.check(inputs(sample(requested_url='https://bingx.com/en/price/bitcoin',url='https://bingx.com/en/price/bitcoin')))['findings'],[])
    def test_bad_decode_alone_candidate(self):
        data=inputs();data['captures'][0]['media'][0]['error_event_src']=None;self.assertEqual(self.first(self.check(data))['classification'],'candidate')
    def test_known_decorative_decoded_can_complete_scoped_check(self):
        data=inputs();row=data['captures'][0]['media'][0];row['decode']['result']='fulfilled';row['error_event_src']=None;row['alt']='';data['reviews']={'a':{'img#hero':{'purpose':'decorative'}}};r=self.check(data);self.assertTrue(r['coverage']['declared_checks_complete']);self.assertFalse(r['coverage']['full_site_proven']);self.assertEqual(r['findings'],[])
    def test_browser_loaded_separate_403_does_not_override(self):
        data=inputs();row=data['captures'][0]['media'][0];row.update(natural_width=100,natural_height=100,error_event_src=None,decode={'result':'fulfilled','current_src':row['current_src']});data['captures'][0]['responses']=[{'url':row['current_src'],'status':403,'method':'GET','captured_at':AT,'source':'separate HTTP fetch','headers':[]}];r=self.check(data);self.assertEqual(r['findings'],[]);self.assertIn('access_limited',str(r['gaps']))
    def test_same_browser_404_response_findable_even_without_error_event(self):
        data=inputs();data['captures'][0]['media'][0].update(error_event_src=None,decode={'result':'not_attempted'});data['captures'][0]['responses']=[{'url':'https://bingx.com/bad.png','status':404,'method':'GET','captured_at':AT,'source':'actual browser response','headers':[]}];r=self.check(data);self.assertTrue(any(f['rule']=='media_resource_not_found' for f in r['findings']))
    def test_different_resource_response_not_attached(self):
        data=inputs();data['captures'][0]['responses']=[{'url':'https://bingx.com/other.png','status':404,'method':'GET','captured_at':AT,'source':'actual browser response','headers':[]}];self.assertEqual(len(self.check(data)['findings']),1)
    def test_resource_references_unselected_are_not_claimed_verified(self):
        data=inputs();data['captures'][0]['declared_resource_count']=800;r=self.check(data);self.assertFalse(r['coverage']['all_declared_resources_verified'])
    def test_invalid_media_row_keeps_other_results(self):
        data=inputs();data['captures'][0]['media'].append({'tag':'img'});r=self.check(data);self.assertEqual(len(r['findings']),1);self.assertIn('invalid_media_row',str(r['gaps']))
    def test_stable_identity_does_not_change_with_time_or_bytes(self):
        a=self.first(self.check())['issue_id'];data=inputs();data['captures'][0]['media'][0]['current_src']='https://bingx.com/new-bad.png';data['captures'][0]['media'][0]['error_event_src']='https://bingx.com/new-bad.png';data['captures'][0]['media'][0]['decode']['current_src']='https://bingx.com/new-bad.png';self.assertEqual(a,self.first(self.check(data))['issue_id'])
    def test_unloaded_lazy_is_gap_not_issue(self):
        data=inputs();data['captures'][0]['media'][0].update(complete=False,in_viewport=False,loading='lazy',decode={'result':'not_attempted'});self.assertEqual(self.check(data)['findings'],[])
    def test_record_replay_idempotent_and_absence_does_not_close(self):
        import tempfile
        from pathlib import Path
        self.module('audit');from crawlability.ledger import record,history
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'issues.sqlite';r=self.check();self.first(r);record(p,r);record(p,r);self.assertEqual(len(history(p)),1);self.assertEqual(history(p)[0]['sightings'],1);r['findings']=[];record(p,r);self.assertEqual(history(p)[0]['status'],'open')
    def test_declared_candidates_reported_without_fake_resource_checks(self):
        data=inputs();data['captures'][0]['declarations']={'resource_refs':[{'url':'https://bingx.com/unselected.png','kind':'image','role':'picture_candidate'}],'gaps':[]};r=self.check(data);self.assertEqual(r['declaration_checks'][0]['unselected_resource_urls'],['https://bingx.com/unselected.png'])
    def test_invalid_srcset_declaration_gap_not_lost(self):
        data=inputs();data['captures'][0]['declarations']={'resource_refs':[],'gaps':[{'reason':'invalid_descriptor','source_path':'img[1]'}]};self.assertIn('invalid_descriptor',str(self.check(data)['gaps']))
