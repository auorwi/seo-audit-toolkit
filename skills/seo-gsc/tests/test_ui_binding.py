"""Real UI text can contain prefix URLs and locale-dependent dates; bind exactly."""
import unittest,hashlib
import test_evidence as helpers
import test_ui_inspection as inspection_helpers

class UIBinding(unittest.TestCase):
    setUp=helpers.Evidence.setUp;add=helpers.Evidence.add;load=helpers.Evidence.load;ui=helpers.Evidence.ui
    def modify_source(self,d,old,new):
        p=self.root/d['source']['path'];p.write_text(p.read_text().replace(old,new));d['source']['sha256']=hashlib.sha256(p.read_bytes()).hexdigest()
    def test_url_prefix_is_not_the_observed_url(self):
        d=self.ui();self.modify_source(d,'https://bingx.com/en','https://bingx.com/english');d['rows'][0]['url_quote']='https://bingx.com/english';self.add(d);self.assertEqual(self.load()['observations'],[])
    def test_shortened_quote_cannot_hide_longer_source_url(self):
        d=self.ui();self.modify_source(d,'https://bingx.com/en','https://bingx.com/english');self.add(d);self.assertEqual(self.load()['observations'],[])
    def test_shortened_property_quote_cannot_hide_other_domain(self):
        d=self.ui();self.modify_source(d,'Property sc-domain:bingx.com','Property sc-domain:bingx.com.evil');self.add(d);self.assertEqual(self.load()['observations'],[])
    def test_queryless_url_not_evidenced_by_parameter_variant(self):
        d=self.ui();self.modify_source(d,'https://bingx.com/en','https://bingx.com/en?pair=BTC');d['rows'][0]['url_quote']='https://bingx.com/en?pair=BTC';self.add(d);self.assertEqual(self.load()['observations'],[])
    def test_domain_property_quote_needs_token_boundary(self):
        d=self.ui();self.modify_source(d,'Property sc-domain:bingx.com','Property sc-domain:bingx.com.evil');d['property_quote']='sc-domain:bingx.com.evil';self.add(d);self.assertEqual(self.load()['observations'],[])
    def test_numeric_us_date_with_explicit_order(self):
        d=self.ui();self.modify_source(d,'2026-09-04','9/4/26');d['report_date_quote']='9/4/26';d['report_date_format']='M/D/YY';self.add(d);r=self.load();self.assertEqual(len(r['observations']),1);self.assertEqual(r['observations'][0]['data']['report_date'],'2026-09-04')
    def test_numeric_uk_date_with_explicit_order(self):
        d=self.ui();self.modify_source(d,'2026-09-04','4/9/2026');d['report_date_quote']='4/9/2026';d['report_date_format']='D/M/YYYY';self.add(d);self.assertEqual(len(self.load()['observations']),1)
    def test_ambiguous_numeric_date_without_order_rejected(self):
        d=self.ui();self.modify_source(d,'2026-09-04','9/4/26');d['report_date_quote']='9/4/26';self.add(d);self.assertEqual(self.load()['observations'],[])
    def test_wrong_declared_order_mismatching_value_rejected(self):
        d=self.ui();self.modify_source(d,'2026-09-04','9/4/2026');d['report_date_quote']='9/4/2026';d['report_date_format']='D/M/YYYY';self.add(d);self.assertEqual(self.load()['observations'],[])
    def test_english_month_date(self):
        d=self.ui();self.modify_source(d,'2026-09-04','Sep 4, 2026');d['report_date_quote']='Sep 4, 2026';d['report_date_format']='MMM D, YYYY';self.add(d);self.assertEqual(len(self.load()['observations']),1)
    def test_chinese_date(self):
        d=self.ui();self.modify_source(d,'2026-09-04','2026年9月4日');d['report_date_quote']='2026年9月4日';d['report_date_format']='YYYY年M月D日';self.add(d);self.assertEqual(len(self.load()['observations']),1)
    def test_iso_prefix_not_equal_different_date(self):
        d=self.ui();self.modify_source(d,'2026-09-04','2026-09-040');d['report_date_quote']='2026-09-040';self.add(d);self.assertEqual(self.load()['observations'],[])

class InspectionBinding(unittest.TestCase):
    setUp=inspection_helpers.UIInspection.setUp;load=inspection_helpers.UIInspection.load
    def change_raw(self,old,new):
        p=self.root/'ui.txt';p.write_text(p.read_text().replace(old,new));self.doc['source']['sha256']=hashlib.sha256(p.read_bytes()).hexdigest()
    def test_inspection_url_must_be_exact(self):
        self.change_raw('https://bingx.com/en','https://bingx.com/english');self.doc['inspection']['url_quote']='https://bingx.com/english';self.assertEqual(self.load()['observations'],[])
    def test_shortened_inspection_quote_cannot_hide_source_url(self):
        self.change_raw('https://bingx.com/en','https://bingx.com/english');self.assertEqual(self.load()['observations'],[])
    def test_canonical_value_requires_matching_url_in_quote(self):
        self.doc['inspection']['fields']['googleCanonical']={'value':'https://bingx.com/en/another','quote':'https://bingx.com/en'};self.assertEqual(self.load()['observations'],[])
    def test_sitemap_each_value_requires_matching_url(self):
        self.doc['inspection']['fields']['sitemap']={'value':['https://bingx.com/en','https://bingx.com/en/missing-sitemap.xml'],'quote':'https://bingx.com/en'};self.assertEqual(self.load()['observations'],[])
    def test_observed_canonical_value_is_accepted(self):
        self.doc['inspection']['fields']['googleCanonical']={'value':'https://bingx.com/en','quote':'https://bingx.com/en'};self.assertEqual(len(self.load()['observations']),1)
if __name__=='__main__':unittest.main()
