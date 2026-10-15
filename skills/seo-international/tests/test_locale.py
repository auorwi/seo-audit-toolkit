from support import InternationalTest,ROOT

class LocaleTests(InternationalTest):
    def check(self,value):return self.module('locale').validate_locale(value)
    def test_registered_language(self):self.assertEqual(self.check('fr')['google_status'],'supported')
    def test_case_normalized(self):self.assertEqual(self.check('ZH-hant-tw')['normalized'],'zh-Hant-TW')
    def test_script_region(self):self.assertEqual(self.check('zh-Hans-US')['google_status'],'supported')
    def test_numeric_region_is_bcp_but_not_google(self):
        r=self.check('es-419');self.assertEqual(r['bcp_status'],'registered_subset');self.assertEqual(r['google_status'],'unsupported')
    def test_uk_not_iso_country(self):self.assertEqual(self.check('en-UK')['google_status'],'unsupported')
    def test_reserved_eu_not_google_region(self):self.assertEqual(self.check('en-EU')['google_status'],'unsupported')
    def test_un_not_google_region(self):self.assertEqual(self.check('en-UN')['google_status'],'unsupported')
    def test_unknown_language(self):self.assertEqual(self.check('xx')['bcp_status'],'invalid')
    def test_three_letter_language_not_google_profile(self):self.assertEqual(self.check('eng')['google_status'],'unsupported')
    def test_country_alone_is_language(self):self.assertEqual(self.check('be')['language'],'be')
    def test_unknown_script(self):self.assertEqual(self.check('zh-Zzzz')['google_status'],'review')
    def test_x_default(self):self.assertEqual(self.check('X-DEFAULT')['google_status'],'fallback')
    def test_private_use_needs_review(self):self.assertEqual(self.check('x-company')['bcp_status'],'review')
    def test_extension_not_declared_invalid(self):self.assertEqual(self.check('en-US-u-ca-gregory')['bcp_status'],'review')
    def test_deprecated_language(self):
        r=self.check('iw');self.assertEqual(r['preferred'],'he');self.assertEqual(r['google_status'],'review')
    def test_whitespace_rejected(self):self.assertEqual(self.check('en US')['bcp_status'],'invalid')
    def test_underscore_rejected(self):self.assertEqual(self.check('en_US')['bcp_status'],'invalid')
    def test_empty_rejected(self):self.assertEqual(self.check('')['bcp_status'],'invalid')
    def test_unknown_region(self):self.assertEqual(self.check('en-XX')['google_status'],'unsupported')
    def test_format_wrong_order(self):self.assertEqual(self.check('en-US-Latn')['bcp_status'],'review')
    def test_registry_provenance(self):
        r=self.check('ja');self.assertTrue(r['registry_date']);self.assertEqual(len(r['registry_sha256']),64)
    def test_bad_type_rejected(self):self.assertEqual(self.check(None)['bcp_status'],'invalid')
    def test_normal_english_region(self):self.assertEqual(self.check('en-GB')['google_status'],'supported')
    def test_unassigned_language_range_not_google(self):self.assertEqual(self.check('qaa')['google_status'],'unsupported')
