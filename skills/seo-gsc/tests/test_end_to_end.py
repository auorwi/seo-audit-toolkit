"""End-to-end declared comparisons, complete scoped runs, and HTML-safe reporting."""
import unittest,tempfile,json,hashlib,sys,subprocess
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from gsc_audit.adapters import load_manifest
from gsc_audit.audit import audit
from gsc_audit.report import write_report
from test_audit import api,live,data,AT,URL,PROP
import test_ui_inspection as ui_helpers
class EndToEnd(unittest.TestCase):
    def test_complete_scoped_pair_does_not_mean_complete_seo(self):
        r=audit(data(api(verdict='PASS',pageFetchState='SUCCESSFUL'),live()),at=AT);self.assertTrue(r['coverage']['declared_checks_complete']);self.assertFalse(r['coverage']['full_site_proven']);self.assertFalse(r['checks'][0]['current_content_verified'])
    def test_performance_comparison_connects_manifest_to_report(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);refs=[]
            for id,start,end,c in [('before','2026-09-01','2026-09-07',10),('after','2026-09-08','2026-09-14',5)]:
                d={'kind':'analytics_api','property':PROP,'captured_at':'2026-09-16T23:00:00Z','http_status':200,'request':{'siteUrl':PROP,'startDate':start,'endDate':end,'dimensions':['page']},'response':{'rows':[{'keys':[URL],'clicks':c,'impressions':100,'ctr':c/100,'position':3}],'responseAggregationType':'byPage'}}
                b=json.dumps(d).encode();(root/(id+'.json')).write_bytes(b);refs.append({'id':id,'path':id+'.json','sha256':hashlib.sha256(b).hexdigest(),'kind':'analytics_api'})
            m={'schema_version':1,'property':PROP,'scope':[{'url':URL,'device':'MOBILE'}],'evidence':refs,'comparisons':[{'before':'before','after':'after'}]};(root/'manifest.json').write_text(json.dumps(m))
            result=audit(load_manifest(root/'manifest.json',at=AT),at=AT);self.assertEqual(len(result['performance_comparisons']),1);delta=result['performance_comparisons'][0]['result'];self.assertEqual(delta['matched_rows'][0]['clicks_delta'],-5);self.assertFalse(delta['sitewide_change_proven'])
            write_report(root/'out',result,[]);self.assertIn('-5',(root/'out/report.md').read_text())
    def test_cli_success_outputs_zero_only_for_declared_scope(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);refs=[]
            docs=[{'kind':'inspection_api','property':PROP,'captured_at':'2026-09-16T23:00:00Z','http_status':200,'request':{'siteUrl':PROP,'inspectionUrl':URL},'response':{'inspectionResult':{'indexStatusResult':{'verdict':'PASS','pageFetchState':'SUCCESSFUL','crawledAs':'MOBILE','lastCrawlTime':'2026-09-01T00:00:00Z'}}}}, {'kind':'live_http','property':PROP,'captured_at':'2026-09-16T23:30:00Z','url':URL,'final_url':URL,'device':'MOBILE','method':'GET','status':200,'source_description':'controlled integration fixture; not live BingX'}]
            for i,d in enumerate(docs):
                b=json.dumps(d).encode();p=str(i)+'.json';(root/p).write_bytes(b);refs.append({'id':str(i),'path':p,'kind':d['kind'],'sha256':hashlib.sha256(b).hexdigest()})
            m={'schema_version':1,'property':PROP,'scope':[{'url':URL,'device':'MOBILE'}],'evidence':refs};(root/'manifest.json').write_text(json.dumps(m));cmd=[sys.executable,str(Path(__file__).resolve().parents[1]/'scripts/audit_gsc.py'),'--manifest',str(root/'manifest.json'),'--state',str(root/'state'),'--output',str(root/'out'),'--at',AT]
            r=subprocess.run(cmd,capture_output=True,text=True);self.assertEqual(r.returncode,0,r.stderr);self.assertFalse(json.loads(r.stdout)['coverage']['full_site_proven'])
    def test_unknown_fetch_is_gap_not_complete(self):
        r=audit(data(api(verdict='PASS',pageFetchState='FUTURE_STATE'),live()),at=AT);self.assertFalse(r['coverage']['declared_checks_complete'])
    def test_raw_markup_escaped_in_human_report(self):
        r=audit(data(api(coverageState='<script>alert(1)</script>'),live()),at=AT)
        with tempfile.TemporaryDirectory() as t:
            write_report(Path(t),r,[]);self.assertNotIn('<script>',(Path(t)/'report.md').read_text())
class UIDate(unittest.TestCase):
    setUp=ui_helpers.UIInspection.setUp;load=ui_helpers.UIInspection.load
    def test_ui_unknown_index_verdict_is_gap(self):
        self.doc['inspection']['fields']['verdict']['value']='VERDICT_UNSPECIFIED'
        x=self.load();r=audit(x,at=AT);self.assertIn('index_verdict_unavailable',str(r['gaps']))
    def test_url_inspection_does_not_require_unavailable_report_date(self):
        x=self.load();self.assertEqual(len(x['observations']),1);self.assertNotIn('report_data_date_unavailable',x['observations'][0]['data']['gaps'])
if __name__=='__main__':unittest.main()
