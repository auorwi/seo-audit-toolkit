import json,subprocess,sys,tempfile
from pathlib import Path
from support import SemanticsTest,ROOT,URL,AT

class ScopePlanTests(SemanticsTest):
    def test_all_keeps_every_page_and_business_parameter(self):
        rows=[{'url':URL,'id':'P1','page_type':'列表'},
              {'url':'https://bingx.com/en/launchpad/detail?currency=78','id':'P2'},
              {'url':'https://bingx.com/en/launchpad/detail?currency=79','id':'C1','conditional':True}]
        plan=self.module('scope').build_plan(rows,mode='all',source='fixture',at=AT)
        self.assertEqual([r['url'] for r in plan['targets']],[URL,rows[1]['url'],rows[2]['url']])
        self.assertEqual(plan['count'],3)
        self.assertFalse(plan['whole_site_claim'])

    def test_subset_is_explicit_and_missing_selection_rejected(self):
        scope=self.module('scope');rows=[{'url':URL,'id':'P1'},{'url':'https://bingx.com/en/learn','id':'P2'}]
        plan=scope.build_plan(rows,mode='subset',ids=['P2'],source='fixture',at=AT)
        self.assertEqual([r['url'] for r in plan['targets']],['https://bingx.com/en/learn'])
        with self.assertRaises(ValueError):scope.build_plan(rows,mode='subset',ids=['P3'],source='fixture',at=AT)
        with self.assertRaises(ValueError):scope.build_plan(rows,mode='subset',source='fixture',at=AT)
        with self.assertRaises(ValueError):scope.build_plan(rows,mode='all',ids=['P1'],source='fixture',at=AT)

    def test_single_exactly_one_and_invalid_inputs_never_disappear(self):
        scope=self.module('scope')
        self.assertEqual(scope.build_plan([],mode='single',urls=[URL],source='user',at=AT)['count'],1)
        for urls in [[URL,'https://bingx.com/en/learn'],['https://example.com/a'],['http://bingx.com/en']]:
            with self.assertRaises(ValueError):scope.build_plan([],mode='single',urls=urls,source='user',at=AT)
        with self.assertRaises(ValueError):scope.build_plan([{'url':URL},{'url':'broken'}],mode='all',source='fixture',at=AT)

    def test_plan_cli_emits_every_page_before_any_collection(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);source=root/'list.json';source.write_text(json.dumps([{'url':f'https://bingx.com/en/price/coin-{i}','page_type':'币种'} for i in range(114)]))
            script=ROOT/'scripts/plan_scope.py';self.assertTrue(script.exists(),'missing preflight scope command')
            run=subprocess.run([sys.executable,str(script),'--mode','all','--input',str(source),'--output',str(root/'plan')],capture_output=True,text=True)
            self.assertEqual(run.returncode,0,run.stderr)
            plan=json.loads((root/'plan/scope.json').read_text());preview=(root/'plan/scope-preview.md').read_text()
            self.assertEqual(plan['count'],114)
            self.assertIn('https://bingx.com/en/price/coin-113',preview)
            self.assertEqual(len(plan['targets']),114)
            self.assertFalse((root/'plan/dom.html').exists())

    def test_plan_integrity_detects_changed_targets(self):
        scope=self.module('scope');p=scope.build_plan([],mode='single',urls=[URL],source='user',at=AT)
        scope.validate_plan(p)
        p['targets'][0]['url']='https://bingx.com/en/learn'
        with self.assertRaises(ValueError):scope.validate_plan(p)
