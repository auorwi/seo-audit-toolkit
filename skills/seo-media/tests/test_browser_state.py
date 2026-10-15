from support import MediaTest
AT='2026-09-16T23:00:00Z'
def image(**kw):
    return {'captured_at':AT,'current_src':'https://bingx.com/a.png','src_attribute':'/a.png',
            'complete':True,'natural_width':640,'natural_height':320,'loading':'eager',
            'in_viewport':True,'decode':{'result':'not_attempted'},**kw}
class BrowserStateTests(MediaTest):
    def check(self,row=None):return self.module('browser_state').review_image(row if row is not None else image(),at=AT)
    def test_dimensions_are_load_evidence_not_decode_probe(self):
        r=self.check();self.assertEqual(r['status'],'loaded_dimensions_observed');self.assertFalse(r['decode_verified'])
    def test_complete_true_zero_dimensions_not_success(self):
        r=self.check(image(natural_width=0,natural_height=0));self.assertEqual(r['status'],'zero_dimensions_unresolved')
    def test_decode_fulfilled_bound_to_current_source(self):
        r=self.check(image(decode={'result':'fulfilled','current_src':'https://bingx.com/a.png'}));self.assertEqual(r['status'],'decoded');self.assertTrue(r['decode_verified'])
    def test_svg_zero_dimensions_can_decode(self):
        r=self.check(image(natural_width=0,natural_height=0,decode={'result':'fulfilled','current_src':'https://bingx.com/a.png'}));self.assertEqual(r['status'],'decoded')
    def test_old_source_decode_not_bind_new_source(self):
        self.assertEqual(self.check(image(decode={'result':'fulfilled','current_src':'https://bingx.com/old.png'}))['status'],'decode_source_mismatch')
    def test_decode_rejected_alone_does_not_prove_permanent_breakage(self):
        self.assertEqual(self.check(image(decode={'result':'rejected','current_src':'https://bingx.com/a.png'}))['status'],'decode_rejected')
    def test_error_event_and_broken_state_confirm_browser_failure(self):
        r=self.check(image(natural_width=0,natural_height=0,error_event_src='https://bingx.com/a.png'));self.assertEqual(r['status'],'browser_image_failure')
    def test_error_event_for_previous_source_not_current_failure(self):
        self.assertEqual(self.check(image(error_event_src='https://bingx.com/old.png'))['status'],'loaded_dimensions_observed')
    def test_empty_image_complete_is_not_broken_resource(self):
        self.assertEqual(self.check(image(current_src='',src_attribute='',natural_width=0,natural_height=0))['status'],'no_selected_resource')
    def test_lazy_offscreen_pending_not_broken(self):
        self.assertEqual(self.check(image(complete=False,natural_width=0,natural_height=0,loading='lazy',in_viewport=False))['status'],'lazy_deferred')
    def test_lazy_visible_pending_is_pending(self):
        self.assertEqual(self.check(image(complete=False,natural_width=0,natural_height=0,loading='lazy'))['status'],'loading')
    def test_eager_offscreen_pending_not_lazy_deferred(self):
        self.assertEqual(self.check(image(complete=False,in_viewport=False))['status'],'loading')
    def test_stale_observation_not_current(self):self.assertEqual(self.check(image(captured_at='2024-01-01T00:00:00Z'))['status'],'stale_observation')
    def test_boolean_dimensions_rejected(self):self.assertEqual(self.check(image(natural_width=True))['status'],'invalid_observation')
    def test_negative_dimension_rejected(self):self.assertEqual(self.check(image(natural_height=-1))['status'],'invalid_observation')
    def test_unknown_complete_not_coerced(self):self.assertEqual(self.check(image(complete='true'))['status'],'invalid_observation')
    def test_missing_geometry_kept_unknown(self):
        r=image();del r['natural_width'];self.assertEqual(self.check(r)['status'],'invalid_observation')
    def test_nonfinite_dimensions_rejected(self):self.assertEqual(self.check(image(natural_width=float('nan')))['status'],'invalid_observation')
    def test_selected_data_uri_can_be_loaded(self):self.assertEqual(self.check(image(current_src='data:image/png;base64,AA=='))['status'],'loaded_dimensions_observed')
    def test_natural_width_not_reported_as_encoded_pixel_width(self):
        r=self.check(image(dpr=2));self.assertIsNone(r['encoded_pixel_width']);self.assertEqual(r['natural_width_css_pixels'],640)
    def test_probe_timeout_is_gap_not_broken(self):
        self.assertEqual(self.check(image(decode={'result':'timeout','current_src':'https://bingx.com/a.png'}))['status'],'decode_timeout')
    def test_failed_decode_different_source_is_mismatch(self):
        self.assertEqual(self.check(image(decode={'result':'rejected','current_src':'https://bingx.com/old.png'}))['status'],'decode_source_mismatch')
