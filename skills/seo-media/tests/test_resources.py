from support import MediaTest
AT='2026-09-16T23:00:00Z'
PNG=b'\x89PNG\r\n\x1a\n'+b'\0'*24
def response(**kw):return {'url':'https://static-app.bb-os.com/image.png','method':'GET','status':200,'headers':[['content-type','image/png']],'captured_at':AT,'source':'actual response','body_prefix':PNG,'body_complete':False,'body_decoded':True,**kw}
class ResourceTests(MediaTest):
    def check(self,row=None,kind='image'):return self.module('resources').review_resource(row or response(),expected_kind=kind,at=AT)
    def test_png_signature_observed_not_decode_proven(self):
        r=self.check();self.assertEqual(r['status'],'image_response_observed');self.assertFalse(r['decoded_verified'])
    def test_404_missing_resource(self):self.assertEqual(self.check(response(status=404))['status'],'resource_not_found')
    def test_410_removed_resource(self):self.assertEqual(self.check(response(status=410))['status'],'resource_not_found')
    def test_403_access_restriction_not_deadlink(self):self.assertEqual(self.check(response(status=403))['status'],'access_limited')
    def test_429_access_restriction_not_deadlink(self):self.assertEqual(self.check(response(status=429))['status'],'access_limited')
    def test_500_server_error(self):self.assertEqual(self.check(response(status=503))['status'],'server_error')
    def test_302_requires_target(self):self.assertEqual(self.check(response(status=302))['status'],'redirect_unverified')
    def test_head_not_get_proof(self):self.assertEqual(self.check(response(method='HEAD'))['status'],'headers_only')
    def test_html_with_image_mime_is_html_problem(self):self.assertEqual(self.check(response(body_prefix=b'<!doctype html><html>error</html>'))['status'],'html_instead_of_media')
    def test_html_mime_image_signature_is_header_mismatch(self):self.assertEqual(self.check(response(headers=[['content-type','text/html']]))['status'],'mime_signature_mismatch')
    def test_iframe_html_normal(self):self.assertEqual(self.check(response(headers=[['content-type','text/html']],body_prefix=b'<html>player</html>'),kind='embed_document')['status'],'embed_response_observed')
    def test_svg_with_xml_preamble_not_html(self):
        r=self.check(response(headers=[['content-type','image/svg+xml']],body_prefix=b'<?xml version="1.0"?><svg xmlns="http://www.w3.org/2000/svg"><path/></svg>'));self.assertEqual(r['status'],'image_response_observed')
    def test_extension_not_authoritative(self):self.assertEqual(self.check(response(url='https://static-app.bb-os.com/no-extension?format=png'))['status'],'image_response_observed')
    def test_jpeg_extension_html_not_pass(self):self.assertEqual(self.check(response(url='https://bingx.com/a.jpg',body_prefix=b'<html>not image</html>'))['status'],'html_instead_of_media')
    def test_empty_complete_body_not_valid_image(self):self.assertEqual(self.check(response(body_prefix=b'',body_complete=True))['status'],'empty_resource_body')
    def test_missing_prefix_not_corrupt_by_guess(self):self.assertEqual(self.check(response(body_prefix=b''))['status'],'body_unobserved')
    def test_unknown_signature_not_assume_broken(self):self.assertEqual(self.check(response(body_prefix=b'unknown format'))['status'],'unrecognized_media_prefix')
    def test_generic_mime_keeps_image_detection(self):self.assertEqual(self.check(response(headers=[['content-type','application/octet-stream']]))['status'],'image_response_generic_mime')
    def test_conflicting_content_types_not_choose_one(self):self.assertEqual(self.check(response(headers=[['content-type','image/png'],['Content-Type','text/html']]))['status'],'conflicting_content_types')
    def test_compressed_unprocessed_prefix_not_sniffed(self):self.assertEqual(self.check(response(body_decoded=False,headers=[['content-type','image/png'],['content-encoding','gzip']]))['status'],'encoded_body_uninspected')
    def test_stale_response_not_current(self):self.assertEqual(self.check(response(captured_at='2025-01-01T00:00:00Z'))['status'],'stale_response')
    def test_network_error_not_http_site_error(self):self.assertEqual(self.check(response(status=None,error='timeout'))['status'],'request_failed')
    def test_range_image_response_possible(self):self.assertEqual(self.check(response(status=206,headers=[['content-type','image/png'],['content-range','bytes 0-31/1000']]))['status'],'image_response_observed')
    def test_hls_playlist_not_html_player(self):self.assertEqual(self.check(response(headers=[['content-type','application/vnd.apple.mpegurl']],body_prefix=b'#EXTM3U\n#EXT-X-VERSION:3'),kind='video')['status'],'video_playlist_observed')
    def test_mp4_not_image(self):self.assertEqual(self.check(response(headers=[['content-type','video/mp4']],body_prefix=b'\0\0\0\x18ftypmp42'+b'\0'*20))['status'],'unexpected_resource_type')
    def test_data_uri_does_not_need_http_status(self):self.assertEqual(self.check(response(url='data:image/png;base64,AA==',status=None))['status'],'inline_resource_requires_browser')
    def test_blob_not_fetchable_outside_browser(self):self.assertEqual(self.check(response(url='blob:https://bingx.com/abc',status=None))['status'],'session_resource_requires_browser')
    def test_nonzero_range_not_sniffed_as_file_prefix(self):self.assertEqual(self.check(response(status=206,headers=[['content-type','image/png'],['content-range','bytes 100-131/1000']]))['status'],'partial_range_uninspected')
    def test_missing_range_start_not_assumed_zero(self):self.assertEqual(self.check(response(status=206))['status'],'partial_range_uninspected')
    def test_unsupported_scheme_not_http_proof(self):self.assertEqual(self.check(response(url='file:///tmp/a.png'))['status'],'invalid_response_metadata')
    def test_jpeg_legacy_mime_alias_not_wrong_content(self):self.assertEqual(self.check(response(headers=[['content-type','image/jpg']],body_prefix=b'\xff\xd8\xff\x00'))['status'],'image_response_mime_alias')
