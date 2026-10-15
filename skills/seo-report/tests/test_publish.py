import copy, pathlib, sys, tempfile, unittest, xml.etree.ElementTree as ET
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'scripts'))
try:
 from seo_report import publish
except ImportError:publish=None
class Remote:
 """In-memory remote documents with mutable block IDs; no real API assertions."""
 def __init__(self):self.docs={};self.writes=0;self.fail=None
 def call(self,action,**kw):
  if action=='fetch':return self.docs[kw['url']]
  self.writes+=1
  if action=='create':
   url='https://test.feishu.cn/docx/'+str(len(self.docs)+1);self.docs[url]=self.ids(kw['xml']);result=url
  elif action=='insert':
   url=kw['url'];self.docs[url]+=self.ids(kw['xml']);result=None
  elif action=='replace':
   url=kw['url'];root=ET.fromstring('<r>'+self.docs[url]+'</r>');old=next(e for e in root if e.get('id')==kw['block_id']);i=list(root).index(old);root.remove(old);root.insert(i,ET.fromstring(self.ids(kw['xml'])));self.docs[url]=''.join(ET.tostring(e,encoding='unicode') for e in root);result=None
  else:raise AssertionError(action)
  if self.fail==action:self.fail=None;raise TimeoutError('ambiguous after commit')
  return result
 def ids(self,xml):
  root=ET.fromstring('<r>'+xml+'</r>')
  for i,e in enumerate(root):e.set('id',f'b{self.writes}-{i}')
  return ''.join(ET.tostring(e,encoding='unicode') for e in root)
class PublishTests(unittest.TestCase):
 def setUp(self):
  self.assertIsNotNone(publish,'publisher missing');self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=pathlib.Path(self.tmp.name);self.remote=Remote()
  self.doc={'key':'ledger','title':'Test','mutable':True,'sections':[{'key':'group-a','xml':'<p>original &amp; content</p>'}]}
 def runpub(self):return publish.publish_document(self.doc,self.root,self.remote)
 def test_create_and_readback(self):
  url=self.runpub();self.assertIn('original',self.remote.docs[url]);self.assertEqual(self.remote.writes,2)
 def test_repeat_no_write(self):
  self.runpub();n=self.remote.writes;self.runpub();self.assertEqual(n,self.remote.writes)
 def test_mutable_update_replaces_not_duplicates(self):
  url=self.runpub();self.doc['sections'][0]['xml']='<p>new</p>';self.runpub();self.assertIn('new',self.remote.docs[url]);self.assertNotIn('original',self.remote.docs[url]);self.assertEqual(len(self.remote.docs),1)
 def test_preserves_manual_blocks(self):
  url=self.runpub();self.remote.docs[url]+='<p id="manual">manual</p>';self.doc['sections'][0]['xml']='<p>new</p>';self.runpub();self.assertIn('manual',self.remote.docs[url])
 def test_manual_edit_generated_block_stops(self):
  url=self.runpub();self.remote.docs[url]=self.remote.docs[url].replace('original','useredit')
  with self.assertRaises(ValueError):self.runpub()
 def test_uncertain_create_never_duplicates(self):
  self.remote.fail='create'
  with self.assertRaises(TimeoutError):self.runpub()
  with self.assertRaises(ValueError):self.runpub()
  self.assertEqual(len(self.remote.docs),1);self.assertEqual(self.remote.writes,1)
 def test_adopt_after_uncertain_create(self):
  self.remote.fail='create'
  with self.assertRaises(TimeoutError):self.runpub()
  url=next(iter(self.remote.docs));publish.adopt(self.doc['key'],url,self.root,self.remote);self.assertEqual(self.runpub(),url);self.assertEqual(len(self.remote.docs),1)
 def test_adopt_wrong_marker(self):
  self.remote.docs['https://test.feishu.cn/docx/other']='<p id="x">unrelated</p>'
  with self.assertRaises(ValueError):publish.adopt('ledger','https://test.feishu.cn/docx/other',self.root,self.remote)
 def test_uncertain_insert_recovers_by_full_readback(self):
  self.remote.fail='insert'
  with self.assertRaises(TimeoutError):self.runpub()
  n=self.remote.writes;self.runpub();self.assertEqual(n,self.remote.writes)
 def test_uncertain_replace_recovers(self):
  self.runpub();self.doc['sections'][0]['xml']='<p>new</p>';self.remote.fail='replace'
  with self.assertRaises(TimeoutError):self.runpub()
  n=self.remote.writes;self.runpub();self.assertEqual(n,self.remote.writes)
 def test_marker_alone_insufficient(self):
  url=self.runpub();self.remote.docs[url]=self.remote.docs[url].replace('original &amp; content','')
  with self.assertRaises(ValueError):self.runpub()
 def test_duplicate_markers_rejected(self):
  url=self.runpub();root=ET.fromstring('<r>'+self.remote.docs[url]+'</r>');self.remote.docs[url]+=ET.tostring(list(root)[-1],encoding='unicode')
  with self.assertRaises(ValueError):self.runpub()
 def test_immutable_run_cannot_change(self):
  self.doc['mutable']=False;self.runpub();self.doc['sections'][0]['xml']='<p>changed</p>'
  with self.assertRaises(ValueError):self.runpub()
 def test_unknown_pending_insert_not_retried(self):
  self.remote.fail='insert'
  with self.assertRaises(TimeoutError):self.runpub()
  url=next(iter(self.remote.docs));root=ET.fromstring('<r>'+self.remote.docs[url]+'</r>');root.remove(list(root)[-1]);self.remote.docs[url]=''.join(ET.tostring(e,encoding='unicode') for e in root)
  n=self.remote.writes
  with self.assertRaises(ValueError):self.runpub()
  self.assertEqual(n,self.remote.writes)
 def test_cli_error_envelope(self):
  with self.assertRaises(ValueError):publish.parse_response(0,'{"ok":false,"error":{}}')
 def test_cli_nonzero(self):
  with self.assertRaises(ValueError):publish.parse_response(1,'{"ok":true,"data":{}}')
 def test_cli_partial_failure(self):
  with self.assertRaises(ValueError):publish.parse_response(0,'{"ok":true,"data":{"result":"partial_success"}}')
 def test_cli_ok(self):self.assertEqual(publish.parse_response(0,'{"ok":true,"data":{"x":1}}'),{'x':1})
 def test_bad_doc_url(self):
  with self.assertRaises(ValueError):publish.adopt('ledger','https://evil.example/docx/1',self.root,self.remote)
 def test_single_root_section_required(self):
  self.doc['sections'][0]['xml']='<p>a</p><p>b</p>'
  with self.assertRaises(ValueError):self.runpub()
