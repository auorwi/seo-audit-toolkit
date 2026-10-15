import json,tempfile,xml.etree.ElementTree as ET
from pathlib import Path
from support import SemanticsTest,URL,AT

class PageChecklistTests(SemanticsTest):
    def test_missing_main_document_finding_can_be_delivered(self):
        from test_rules import dom,node
        result=self.module('audit').audit([dom([node('x','h1','Sample')])],[],[URL],at=AT)
        with tempfile.TemporaryDirectory() as t:
            self.module('report').write_report(t,result,[])
            data=json.loads((Path(t)/'page-checklist.json').read_text())
            self.assertTrue(any(i['rule']=='main_landmark_missing' for i in data['pages'][0]['items']))

    def test_distinct_bound_model_recommendations_survive_same_issue_id(self):
        result=self.result();f=self.finding('shared','model_semantic_review','model_review')
        f['recommendation']='Fix heading'
        f['evidence']=[{'review':{'topic':'heading_topic_hierarchy','recommendation':'Fix heading','retest':'Read headings'}},
                       {'review':{'topic':'list_and_table_purpose','recommendation':'Fix list','retest':'Read list'}}]
        result['findings']=[f]
        with tempfile.TemporaryDirectory() as t:
            self.module('report').write_report(t,result,[])
            data=json.loads((Path(t)/'page-checklist.json').read_text())
            items=data['pages'][0]['items']
            self.assertEqual({i['recommendation'] for i in items},{'Fix heading','Fix list'})
            self.assertTrue(all(i['issue_ids']==['shared'] for i in items))
    def result(self):
        other='https://bingx.com/en/learn'
        return {'at':AT,'scope':[URL,other], 'rows':[{'url':URL,'rendered_capture':'dom1','browser_state':'ready','tools':[{'tool':'axe','status':'usable'}]}],
            'coverage':{'requested_urls':2,'ready_documents':1,'usable_tool_runs':1,'full_accessibility_certification':False},
            'gaps':[{'url':other,'reason':'rendered_elements_missing'}], 'input_gaps':[], 'handoffs':[],
            'pending_reviews':[{'url':URL,'topics':['heading_topic_hierarchy'],'reviewed_topics':[]}],
            'findings':[self.finding('one','empty_heading'),self.finding('two','empty_heading'),self.finding('three','main_landmark_missing'),self.finding('four','heading_level_review','manual_review')]}

    def finding(self,id,rule,classification='accessibility_violation'):
        return {'issue_id':id,'url':URL,'rule':rule,'classification':classification,'owner_skill':'006','impact_domain':'accessibility','observed_at':AT,'recommendation':'Correct '+rule,'retest':'Check','evidence':[{'target':['#'+id],'message':'Actual '+rule,'html':'<div>untrusted</div>'}]}

    def test_one_page_one_solution_all_issues_and_unchecked_pages_retained(self):
        with tempfile.TemporaryDirectory() as t:
            self.module('report').write_report(t,self.result(),[])
            p=Path(t)/'page-checklist.json';self.assertTrue(p.exists(),'missing page-based solution output')
            pages=json.loads(p.read_text())['pages']
            self.assertEqual(len(pages),2);self.assertEqual(pages[0]['url'],URL)
            self.assertEqual(len(pages[0]['items']),3)
            self.assertEqual({id for item in pages[0]['items'] for id in item['issue_ids']},{'one','two','three','four'})
            self.assertTrue(any(i['status']=='needs_review' for i in pages[0]['items']))
            self.assertEqual(pages[1]['browser_state'],'not_checked')
            self.assertNotEqual(pages[1]['status'],'passed')

    def test_feishu_native_checkboxes_are_unchecked_and_page_text_escaped(self):
        result=self.result();result['findings'][0]['recommendation']='<script>&bad'
        with tempfile.TemporaryDirectory() as t:
            self.module('report').write_report(t,result,[])
            p=Path(t)/'report.feishu.xml';self.assertTrue(p.exists(),'missing Feishu native checkbox artifact')
            root=ET.fromstring('<root>'+p.read_text()+'</root>')
            self.assertEqual(len(root.findall('h2')),2)
            checks=root.findall('checkbox');self.assertEqual(len(checks),3)
            self.assertTrue(all(c.get('done')=='false' for c in checks))
            self.assertEqual(root.findall('.//script'),[])
            self.assertIn('未检查', ''.join(root.itertext()))

    def test_feishu_body_omits_raw_checker_location_objects(self):
        result=self.result()
        result['findings'][0]['evidence']=[{'message':'Actual finding','location':{'firstLine':4,'hiliteLength':12345}}]
        with tempfile.TemporaryDirectory() as t:
            self.module('report').write_report(t,result,[])
            xml=(Path(t)/'report.feishu.xml').read_text()
            self.assertNotIn('hiliteLength',xml)
            stored=json.loads((Path(t)/'report.json').read_text())
            self.assertEqual(stored['findings'][0]['evidence'][0]['location']['hiliteLength'],12345)

    def test_many_occurrences_compact_but_distinct_problems_not_truncated(self):
        result=self.result();result['findings']=[self.finding(str(i),'listitem') for i in range(40)]
        result['findings'].append(self.finding('last','empty-heading'))
        with tempfile.TemporaryDirectory() as t:
            self.module('report').write_report(t,result,[])
            p=Path(t)/'page-checklist.json';self.assertTrue(p.exists())
            data=json.loads(p.read_text());items=data['pages'][0]['items']
            self.assertEqual(len(items),2);self.assertEqual(len(items[0]['issue_ids']),40)
            self.assertEqual(items[1]['issue_ids'],['last'])
            self.assertLess(len((Path(t)/'report.md').read_text()),6000)
            self.assertEqual(len(json.loads((Path(t)/'report.json').read_text())['findings']),41)

    def test_unrelated_checker_noise_stays_in_evidence_only(self):
        result=self.result()
        for rule in ['color-contrast','button-name','meta-viewport','nu-message']:
            result['findings'].append(self.finding('extra-'+rule,rule))
        with tempfile.TemporaryDirectory() as t:
            self.module('report').write_report(t,result,[])
            text=(Path(t)/'report.feishu.xml').read_text()
            self.assertNotIn('color-contrast',text)
            self.assertNotIn('按对应源码',text)
            self.assertNotIn('可用校验器',text)
            self.assertNotIn('复测',text)
            self.assertEqual(len(json.loads((Path(t)/'report.json').read_text())['findings']),8)
            self.assertEqual(len(json.loads((Path(t)/'page-checklist.json').read_text())['pages'][0]['items']),3)

    def test_model_review_reports_problem_instead_of_long_solution(self):
        result=self.result();f=self.finding('review','model_semantic_review','model_review')
        f['evidence']=[{'review':{'reason':'H2 下直接使用 H4。','recommendation':'Long repair explanation','retest':'Long retest explanation'}}]
        result['findings']=[f]
        with tempfile.TemporaryDirectory() as t:
            self.module('report').write_report(t,result,[])
            text=(Path(t)/'report.feishu.xml').read_text()
            self.assertIn('H2 下直接使用 H4。',text)
            self.assertNotIn('Long repair',text)
            self.assertNotIn('Long retest',text)
