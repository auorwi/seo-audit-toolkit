from support import MediaTest
BASE='https://bingx.com/en/page'
class SrcsetTests(MediaTest):
    def parse(self,value):return self.module('srcset').parse_srcset(value,BASE)
    def test_density_candidates(self):
        r=self.parse('/small.jpg 1x, /big.jpg 2x');self.assertEqual([x['url'] for x in r['candidates']],['https://bingx.com/small.jpg','https://bingx.com/big.jpg']);self.assertEqual(r['candidates'][1]['density'],'2')
    def test_width_candidates(self):self.assertEqual([x['width'] for x in self.parse('a.png 320w, b.png 1280w')['candidates']],[320,1280])
    def test_relative_url_resolution(self):self.assertEqual(self.parse('../img.png 1x')['candidates'][0]['url'],'https://bingx.com/img.png')
    def test_data_uri_comma_not_separator(self):
        r=self.parse('data:image/png;base64,AAAA 1x, /big.png 2x');self.assertEqual(len(r['candidates']),2);self.assertEqual(r['candidates'][0]['url'],'data:image/png;base64,AAAA')
    def test_comma_inside_ordinary_url_not_split_without_whitespace(self):self.assertEqual(len(self.parse('/a,b.png 1x')['candidates']),1)
    def test_trailing_url_comma_delimits_descriptorless_source(self):self.assertEqual(len(self.parse('/a.png, /b.png 2x')['candidates']),2)
    def test_descriptorless_density_one(self):self.assertEqual(self.parse('/a.png')['candidates'][0]['density'],'1')
    def test_zero_width_rejected(self):self.assertEqual(self.parse('/a.png 0w')['candidates'],[])
    def test_negative_density_rejected(self):self.assertEqual(self.parse('/a.png -1x')['candidates'],[])
    def test_duplicate_descriptor_on_one_candidate_rejected(self):self.assertEqual(self.parse('/a.png 1x 2x')['candidates'],[])
    def test_width_and_density_same_candidate_rejected(self):self.assertEqual(self.parse('/a.png 320w 2x')['candidates'],[])
    def test_unknown_descriptor_flagged(self):self.assertTrue(self.parse('/a.png 99q')['gaps'])
    def test_duplicate_density_across_candidates_diagnostic(self):self.assertTrue(any(g['reason']=='duplicate_descriptor' for g in self.parse('/a.png 1x, /b.png 1x')['gaps']))
    def test_mixed_descriptor_types_diagnostic(self):self.assertTrue(any(g['reason']=='mixed_width_density_descriptors' for g in self.parse('/a.png 320w, /b.png 2x')['gaps']))
    def test_float_density(self):self.assertEqual(self.parse('/a.png 1.5x')['candidates'][0]['density'],'1.5')
    def test_empty_no_candidates(self):self.assertEqual(self.parse('')['candidates'],[])
    def test_javascript_url_not_fetchable(self):self.assertEqual(self.parse('javascript:alert(1) 1x')['candidates'],[])
    def test_never_claim_actual_selection(self):self.assertIsNone(self.parse('/a.png 320w, /b.png 640w')['selected_url'])
    def test_zero_density_browser_parse_preserved_but_authoring_flagged(self):
        r=self.parse('/a.png 0x');self.assertEqual(r['candidates'][0]['density'],'0');self.assertTrue(any(g['reason']=='nonpositive_density_authoring' for g in r['gaps']))
    def test_parens_comma_not_fake_candidate(self):
        r=self.parse('/a.png calc(1x, 2x), /b.png 2x');self.assertEqual([c['url'] for c in r['candidates']],['https://bingx.com/b.png'])
    def test_extreme_density_does_not_crash(self):self.assertEqual(self.parse('/a.png 1e999999999x')['candidates'],[])
    def test_density_not_rounded_by_default_decimal_context(self):
        value='1.1234567890123456789012345678901';self.assertEqual(self.parse('/a.png '+value+'x')['candidates'][0]['density'],value)
