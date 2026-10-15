from support import MediaTest
URL='https://bingx.com/en/learn/article/example'
class ExtractTests(MediaTest):
    def extract(self,html,**kw):return self.module('extract').extract_html(html,URL,**kw)
    def test_img_source_resolved(self):self.assertEqual(self.extract('<img src="/media/a.png">')['images'][0]['src_url'],'https://bingx.com/media/a.png')
    def test_empty_alt_distinct_from_missing(self):
        rows=self.extract('<img src="a" alt=""><img src="b">')['images'];self.assertTrue(rows[0]['alt_present']);self.assertEqual(rows[0]['alt'],'');self.assertFalse(rows[1]['alt_present']);self.assertIsNone(rows[1]['alt'])
    def test_does_not_invent_visible_purpose(self):
        row=self.extract('<img src="a" alt="">')['images'][0];self.assertEqual(row['visibility'],'unknown');self.assertEqual(row['purpose'],'unknown')
    def test_picture_sources_associated(self):
        row=self.extract('<picture><source srcset="a.webp 1x, b.webp 2x" type="image/webp" media="(min-width: 800px)"><img src="fallback.png"></picture>')['images'][0]
        self.assertEqual(len(row['picture_sources']),1);self.assertEqual(len(row['picture_sources'][0]['candidates']),2);self.assertEqual(row['picture_sources'][0]['media'],'(min-width: 800px)')
    def test_source_after_img_not_used_for_that_img(self):self.assertEqual(self.extract('<picture><img src="a"><source srcset="b 2x"></picture>')['images'][0]['picture_sources'],[])
    def test_picture_without_img_gap(self):self.assertTrue(any(g['reason']=='picture_missing_img' for g in self.extract('<picture><source srcset="a.webp"></picture>')['gaps']))
    def test_srcset_and_sizes_retained(self):
        row=self.extract('<img src="a" srcset="b 300w, c 600w" sizes="50vw">')['images'][0];self.assertEqual(row['sizes'],'50vw');self.assertEqual(len(row['srcset']['candidates']),2)
    def test_raw_source_not_current_src(self):self.assertIsNone(self.extract('<img src="a" srcset="b 2x">')['images'][0]['current_src'])
    def test_base_url_applied(self):self.assertEqual(self.extract('<head><base href="https://cdn.example/path/"></head><img src="a.png">')['images'][0]['src_url'],'https://cdn.example/path/a.png')
    def test_only_first_base_used(self):self.assertEqual(self.extract('<base href="/a/"><base href="/b/"><img src="c.png">')['images'][0]['src_url'],'https://bingx.com/a/c.png')
    def test_script_fake_img_ignored(self):self.assertEqual(self.extract('<script>let s="<img src=\"fake.png\">"</script>')['images'],[])
    def test_template_media_not_active(self):self.assertEqual(self.extract('<template><img src="fake.png"></template>')['images'],[])
    def test_noscript_retains_separate_context(self):self.assertEqual(self.extract('<noscript><img src="fallback.png"></noscript>')['images'][0]['context'],'noscript')
    def test_video_src_and_poster(self):
        row=self.extract('<video src="movie.mp4" poster="poster.webp" controls></video>')['videos'][0];self.assertTrue(row['controls']);self.assertTrue(row['src_url'].endswith('/movie.mp4'));self.assertTrue(row['poster_url'].endswith('/poster.webp'))
    def test_video_source_list(self):
        row=self.extract('<video><source src="movie.webm" type="video/webm"><source src="movie.mp4" type="video/mp4"></video>')['videos'][0];self.assertEqual(len(row['sources']),2)
    def test_iframe_not_assumed_video(self):
        row=self.extract('<iframe src="https://example.org/map" title="Map"></iframe>')['embeds'][0];self.assertEqual(row['purpose'],'unknown');self.assertEqual(row['title'],'Map')
    def test_iframe_srcdoc_not_fake_external_resource(self):self.assertIsNone(self.extract('<iframe srcdoc="hello"></iframe>')['embeds'][0]['src_url'])
    def test_embed_object_source(self):
        rows=self.extract('<embed src="player"><object data="viewer"></object>')['embeds'];self.assertEqual(len(rows),2);self.assertTrue(rows[1]['src_url'].endswith('/viewer'))
    def test_metadata_image_kept_separate(self):
        r=self.extract('<head><meta property="og:image" content="/social.png"></head>');self.assertEqual(r['images'],[]);self.assertEqual(r['metadata_images'][0]['url'],'https://bingx.com/social.png')
    def test_empty_src_not_page_itself(self):self.assertIsNone(self.extract('<img src="">')['images'][0]['src_url'])
    def test_width_height_loading_kept(self):
        row=self.extract('<img src="a" width="320" height="200" loading="lazy">')['images'][0];self.assertEqual((row['width_attribute'],row['height_attribute'],row['loading']),('320','200','lazy'))
    def test_element_limit_retains_partial_coverage(self):self.assertEqual(self.extract('<div><img src="a"><img src="b"></div>',max_nodes=2)['coverage']['nodes'],'partial')
    def test_duplicate_attribute_visible(self):self.assertTrue(any(g['reason']=='duplicate_media_attribute' for g in self.extract('<img src="a" src="b">')['gaps']))
    def test_resource_occurrences_not_lost_to_url_dedup(self):self.assertEqual(len(self.extract('<img src="a"><img src="a">')['images']),2)
    def test_poster_resource_role(self):self.assertTrue(any(r['role']=='video_poster' for r in self.extract('<video poster="/a.png"></video>')['resource_refs']))
