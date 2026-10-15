"""Actual Bing Sitemap UI can list www and non-www together; preserve observations without expanding declared checks."""
import unittest
import test_evidence as h
class RelatedHostEvidence(unittest.TestCase):
 setUp=h.Evidence.setUp;load=h.Evidence.load
 def prepare(self,url):
  self.doc.pop('inspection');self.doc['report']='sitemaps';self.raw+='\n'+url+'\nSuccess\n';self.doc['rows']=[{'url':url,'url_quote':url,'reason_key':'valid','reason_label':'Success','quote':'Success'}]
 def test_www_sitemap_reported_in_selected_root_site_retained(self):
  self.prepare('https://www.bingx.com/sitemap.xml');d=self.load();self.assertEqual(len(d['observations']),1);r=d['observations'][0]['data']['rows'][0];self.assertTrue(r['outside_site_prefix']);self.assertEqual(r['url'],'https://www.bingx.com/sitemap.xml');self.assertEqual(len(d['scope']),1)
 def test_unrelated_host_rejected_even_if_quoted(self):
  self.prepare('https://evil.test/sitemap.xml');self.assertEqual(self.load()['observations'],[])
 def test_deceptive_related_host_rejected(self):
  self.prepare('https://www.bingx.com.evil.test/sitemap.xml');self.assertEqual(self.load()['observations'],[])
 def test_related_row_does_not_expand_manifest_scope(self):
  self.scope=[{'url':'https://www.bingx.com/en','device':'UNKNOWN'}]
  with self.assertRaises(ValueError):self.load()
if __name__=='__main__':unittest.main()
