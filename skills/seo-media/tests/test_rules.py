from support import MediaTest
def img(**kw):return {'slot':'img#hero','tag':'img','alt_present':True,'alt':'Bitcoin chart','loading':'eager','visible':True,'in_viewport':True,**kw}
class RuleTests(MediaTest):
    def check(self,row=None,review=None):return self.module('rules').review_media(row or img(),review=review)
    def rules(self,row=None,review=None):return [r['rule'] for r in self.check(row,review)['findings']]
    def test_unknown_purpose_requires_review(self):self.assertIn('purpose_unreviewed',self.check()['gaps'])
    def test_decorative_empty_alt_no_error(self):self.assertEqual(self.rules(img(alt=''),{'purpose':'decorative'}),[])
    def test_decorative_missing_alt_has_semantics_referral(self):
        r=self.check(img(alt_present=False,alt=None),{'purpose':'decorative'});self.assertEqual(r['referrals'][0]['owner'],'006');self.assertEqual(r['findings'],[])
    def test_information_empty_alt_referred_to_006(self):
        r=self.check(img(alt=''),{'purpose':'informative'});self.assertEqual(r['referrals'][0]['rule'],'information_image_alt_empty')
    def test_functional_image_not_assume_alt_only_name(self):
        r=self.check(img(alt=''),{'purpose':'functional'});self.assertEqual(r['findings'],[]);self.assertIn('accessible_name_context',r['referrals'][0]['rule'])
    def test_information_named_no_false_error(self):self.assertEqual(self.rules(),[])
    def test_lazy_important_initial_image_risk_not_cwv_failure(self):
        r=self.check(img(loading='lazy'),{'purpose':'informative','important_initial':True});self.assertEqual(r['referrals'][0]['owner'],'011');self.assertEqual(r['findings'],[])
    def test_lazy_belowfold_not_initial_risk(self):
        r=self.check(img(loading='lazy',in_viewport=False),{'purpose':'informative','important_initial':True});self.assertEqual(r['referrals'],[])
    def test_missing_dimensions_not_cls_failure(self):self.assertEqual(self.rules(img(width_attribute=None,height_attribute=None),{'purpose':'informative'}),[])
    def test_css_essential_without_equivalent_needs_discoverability_fix(self):
        r=self.check({'slot':'div#hero::background','tag':'css','background_urls':['https://bingx.com/a.png']},{'purpose':'informative','important_initial':True,'image_search_target':True,'equivalent_img':False});self.assertEqual(r['findings'][0]['rule'],'essential_css_image_no_img_equivalent')
    def test_css_equivalent_image_no_duplicate_finding(self):
        self.assertEqual(self.rules({'tag':'css','background_urls':['https://bingx.com/a.png']},{'purpose':'informative','equivalent_img':True}),[])
    def test_css_unknown_equivalence_not_asserted_missing(self):
        r=self.check({'tag':'css','background_urls':['https://bingx.com/a.png']},{'purpose':'informative'});self.assertEqual(r['findings'],[]);self.assertIn('css_equivalent_img_unreviewed',r['gaps'])
    def test_css_decorative_no_google_images_issue(self):self.assertEqual(self.rules({'tag':'css','background_urls':['https://bingx.com/a.png']},{'purpose':'decorative'}),[])
    def test_video_auxiliary_not_forced_watchpage(self):self.assertEqual(self.rules({'tag':'video','poster':''},{'purpose':'auxiliary_video'}),[])
    def test_video_watch_without_thumbnail_is_candidate(self):
        r=self.check({'tag':'video','poster':''},{'purpose':'watch_video','representative_thumbnail':False});self.assertEqual(r['findings'][0]['classification'],'candidate')
    def test_video_poster_does_not_prove_indexed(self):
        r=self.check({'tag':'video','poster':'https://bingx.com/a.png'},{'purpose':'watch_video'});self.assertFalse(r['video_indexed_verified']);self.assertIn('thumbnail_fitness_unreviewed',r['gaps'])
    def test_video_error_is_browser_observation_not_indexing(self):
        r=self.check({'tag':'video','error_code':4},{'purpose':'auxiliary_video'});self.assertEqual(r['findings'][0]['rule'],'browser_video_error');self.assertFalse(r['playback_verified'])
    def test_video_ready_metadata_not_playback(self):
        r=self.check({'tag':'video','ready_state':1},{'purpose':'auxiliary_video'});self.assertFalse(r['playback_verified'])
    def test_iframe_unknown_not_assumed_video(self):
        r=self.check({'tag':'iframe','src':'https://example.com/embed'});self.assertNotIn('video_thumbnail_unavailable',str(r['findings']))
    def test_watch_iframe_requires_thumbnail_review_not_poster_attribute(self):
        r=self.check({'tag':'iframe'},{'purpose':'watch_video','representative_thumbnail':True});self.assertEqual(r['findings'],[])
    def test_invalid_purpose_not_used(self):self.assertIn('invalid_purpose',self.check(review={'purpose':'made-up'})['gaps'])
    def test_hidden_image_important_initial_not_used(self):
        self.assertEqual(self.check(img(loading='lazy',visible=False),{'purpose':'informative','important_initial':True})['referrals'],[])
    def test_video_aborted_not_resource_failure(self):
        r=self.check({'tag':'video','error_code':1},{'purpose':'auxiliary_video'});self.assertEqual(r['findings'],[]);self.assertIn('video_load_aborted',r['gaps'])
    def test_css_ui_gauge_not_required_to_be_search_image(self):
        r=self.check({'tag':'css','background_urls':['https://bingx.com/gauge.svg']},{'purpose':'informative','equivalent_img':False,'image_search_target':False});self.assertEqual(r['findings'],[])
    def test_css_unknown_search_intent_not_forced_to_img(self):
        r=self.check({'tag':'css','background_urls':['https://bingx.com/gauge.svg']},{'purpose':'informative','equivalent_img':False});self.assertEqual(r['findings'],[]);self.assertIn('css_image_search_intent_unreviewed',r['gaps'])
    def test_functional_css_icon_name_referred_to_semantics(self):
        r=self.check({'tag':'css','background_urls':['https://bingx.com/icon.svg']},{'purpose':'functional'});self.assertEqual(r['referrals'][0]['owner'],'006')
    def test_auxiliary_iframe_empty_title_referred_not_video_indexing_error(self):
        r=self.check({'tag':'iframe','title':''},{'purpose':'auxiliary_video'});self.assertEqual(r['findings'],[]);self.assertTrue(any(x['owner']=='006' and x['rule']=='iframe_accessible_name_context' for x in r['referrals']))
