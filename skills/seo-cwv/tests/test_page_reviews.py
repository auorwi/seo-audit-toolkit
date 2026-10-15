import base64,copy,hashlib
from support import CWVTest,URL,AT
from test_series import run

PIXEL=base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aZ1kAAAAASUVORK5CYII=')
def review(**kw):
    return {'run_id':'r1','lhr_sha256':'a'*64,'requested_url':URL,'final_url':URL,
        'screenshot_sha256':hashlib.sha256(PIXEL).hexdigest(),'reviewed_at':AT,
        'reviewer':'Codex','method':'codex_screenshot_review','status':'valid',
        'expected_content':'Bitcoin price page','visible_evidence':'Bitcoin heading and price chart',
        'reason':'Target page is visible at end of capture; not a loading sequence review.',**kw}
def raw():return {'fullPageScreenshot':{'screenshot':{'data':'data:image/png;base64,'+base64.b64encode(PIXEL).decode()}}}
def measured(**kw):return run(1,run_id='r1',evidence={'sha256':'a'*64},attempt_finished_at=AT,**kw)

class PageReviewTests(CWVTest):
    def apply(self,rev=None,r=None,lhr=None):return self.module('reviews').apply_review(r or measured(),lhr or raw(),rev or review())
    def test_valid_review_attaches_business_evidence(self):
        r=self.apply();self.assertEqual(r['page_content_validity'],'reviewed_valid');self.assertTrue(r['valid_measurement']);self.assertEqual(r['page_review']['visible_evidence'],'Bitcoin heading and price chart')
    def test_wrong_business_content_excludes_preserved_metrics(self):
        r=self.apply(review(status='invalid',visible_evidence='Verify you are human',reason='A bot challenge replaces the requested page.'));self.assertFalse(r['valid_measurement']);self.assertEqual(r['exclusion'],'business_page_invalid');self.assertEqual(r['metrics']['LCP'],3000)
    def test_inconclusive_does_not_certify_business_page(self):self.assertEqual(self.apply(review(status='inconclusive'))['page_content_validity'],'reviewed_inconclusive')
    def test_wrong_screenshot_rejected(self):
        with self.assertRaises(ValueError):self.apply(review(screenshot_sha256='b'*64))
    def test_wrong_lhr_binding_rejected(self):
        with self.assertRaises(ValueError):self.apply(review(lhr_sha256='b'*64))
    def test_wrong_run_rejected(self):
        with self.assertRaises(ValueError):self.apply(review(run_id='another'))
    def test_wrong_final_page_rejected(self):
        with self.assertRaises(ValueError):self.apply(review(final_url='https://bingx.com/en/'))
    def test_review_before_measurement_rejected(self):
        with self.assertRaises(ValueError):self.apply(review(reviewed_at='2020-01-01T00:00:00Z'))
    def test_empty_visible_evidence_rejected(self):
        with self.assertRaises(ValueError):self.apply(review(visible_evidence='  '))
    def test_metrics_only_method_rejected(self):
        with self.assertRaises(ValueError):self.apply(review(method='automatic_score'))
    def test_valid_review_cannot_promote_runtime_failure(self):self.assertFalse(self.apply(r=measured(valid_measurement=False))['valid_measurement'])
    def test_missing_screenshot_rejected(self):
        with self.assertRaises(ValueError):self.apply(lhr={'fullPageScreenshot':{}})
