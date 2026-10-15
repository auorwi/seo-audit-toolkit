import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
try:from recheck import checks as c
except ImportError:c=None
class Checks(unittest.TestCase):
 def setUp(self):self.assertIsNotNone(c,'Recheck deterministic evaluator missing')
 def check(self,values,rule,complete=None):return c.evaluate(values,rule,complete_fields=complete or [])
 def test_http_200_allowed(self):self.assertEqual(self.check({'status':200},{'field':'status','op':'in','expected':[200]})['status'],'passed')
 def test_http_403_fails(self):self.assertEqual(self.check({'status':403},{'field':'status','op':'in','expected':[200]})['status'],'failed')
 def test_bool_not_http_int(self):self.assertEqual(self.check({'status':True},{'field':'status','op':'in','expected':[1]})['status'],'failed')
 def test_exact_entity_required(self):self.assertEqual(self.check({'h1':['BTCUSDT']},{'field':'h1','op':'equals','expected':['EURCAD']})['status'],'failed')
 def test_blank_title_fails(self):self.assertEqual(self.check({'title':'  '},{'field':'title','op':'nonempty'})['status'],'failed')
 def test_missing_field_not_proof_empty(self):self.assertEqual(self.check({},{'field':'title','op':'nonempty'})['status'],'inconclusive')
 def test_none_field_not_proof_empty(self):self.assertEqual(self.check({'title':None},{'field':'title','op':'nonempty'})['status'],'inconclusive')
 def test_case_sensitive_country(self):self.assertEqual(self.check({'title':'Brazil'},{'field':'title','op':'contains','expected':'brazil'})['status'],'failed')
 def test_positive_excerpt_can_prove_present(self):self.assertEqual(self.check({'body_excerpt':'error message'},{'field':'body_excerpt','op':'contains','expected':'error'})['status'],'passed')
 def test_absence_in_excerpt_inconclusive(self):self.assertEqual(self.check({'body_excerpt':'good'},{'field':'body_excerpt','op':'not_contains','expected':'error'})['status'],'inconclusive')
 def test_absence_in_complete_field_passes(self):self.assertEqual(self.check({'title':'good'},{'field':'title','op':'not_contains','expected':'error'},['title'])['status'],'passed')
 def test_present_error_fails_even_truncated(self):self.assertEqual(self.check({'body_excerpt':'error'},{'field':'body_excerpt','op':'not_contains','expected':'error'})['status'],'failed')
 def test_json_object_cannot_be_treated_as_string(self):self.assertEqual(self.check({'title':{'x':'good'}},{'field':'title','op':'contains','expected':'good'})['status'],'inconclusive')
 def test_no_eval_operator(self):
  with self.assertRaises(ValueError):self.check({'status':200},{'field':'status','op':'eval','expected':'1+1'})
 def test_empty_search_term_rejected(self):
  with self.assertRaises(ValueError):self.check({'title':'x'},{'field':'title','op':'contains','expected':''})
 def test_nested_field_not_guessed(self):self.assertEqual(self.check({'a':{'title':'x'}},{'field':'title','op':'nonempty'})['status'],'inconclusive')
 def test_nonfinite_expected_rejected(self):
  with self.assertRaises(ValueError):self.check({'status':200},{'field':'status','op':'equals','expected':float('nan')})
 def test_both_observed_and_expected_retained(self):
  r=self.check({'title':'x'},{'field':'title','op':'equals','expected':'y'});self.assertEqual(r['observed'],'x');self.assertEqual(r['expected'],'y')
