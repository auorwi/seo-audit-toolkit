from support import SemanticsTest,URL

class ElementTests(SemanticsTest):
    def parse(self,html,**kw):return self.module('elements').parse_html(html,URL,**kw)
    def node(self,result,tag):return next(n for n in result['nodes'] if n['tag']==tag)

    def test_headings_keep_nested_text_and_entities(self):
        result=self.parse('<h1>Bit<span>coin</span> &amp; Markets</h1>')
        self.assertEqual(self.node(result,'h1')['source_text'],'Bitcoin & Markets')

    def test_script_style_template_text_not_mixed_into_heading(self):
        result=self.parse('<h1>BTC<script>wrong()</script><style>.bad{}</style><template>Wrong</template></h1>')
        self.assertEqual(self.node(result,'h1')['source_text'],'BTC')
        self.assertTrue(self.node(result,'template')['inert_hint'])

    def test_source_locations_and_paths_disambiguate_duplicate_ids(self):
        result=self.parse('<main>\n<h1 id="same">A</h1>\n<h1 id="same">B</h1></main>')
        headings=[n for n in result['nodes'] if n['tag']=='h1']
        self.assertEqual([n['location']['line'] for n in headings],[2,3])
        self.assertNotEqual(headings[0]['source_path'],headings[1]['source_path'])
        self.assertEqual(headings[1]['source_path'],'main:nth-of-type(1) > h1:nth-of-type(2)')
        self.assertNotIn('selector',headings[0])

    def test_hidden_is_inherited_but_css_visibility_remains_unknown(self):
        result=self.parse('<div hidden><h1>Mobile</h1></div><h2 class="hidden-by-css">Desktop</h2>')
        self.assertTrue(self.node(result,'h1')['hidden_hint'])
        self.assertEqual(self.node(result,'h2')['visibility'],'unknown')

    def test_aria_hidden_does_not_mean_visually_hidden(self):
        result=self.parse('<div aria-hidden="true"><h1>Visible maybe</h1></div>')
        heading=self.node(result,'h1')
        self.assertTrue(heading['aria_hidden_hint']);self.assertFalse(heading['hidden_hint'])
        self.assertEqual(heading['visibility'],'unknown')

    def test_inert_disables_interaction_but_does_not_erase_visible_source_text(self):
        result=self.parse('<div inert><h1>Still visible</h1></div>')
        heading=self.node(result,'h1')
        self.assertTrue(heading['inert_hint']);self.assertEqual(heading['source_text'],'Still visible')

    def test_source_accessible_name_not_invented_from_visible_text(self):
        result=self.parse('<button aria-labelledby="x">Buy</button><span id="x">Other label</span>')
        button=self.node(result,'button');self.assertIsNone(button['accessible_name'])
        self.assertEqual(button['attributes']['aria-labelledby'],'x')

    def test_void_elements_do_not_swallow_following_nodes(self):
        result=self.parse('<main><img alt=""><h1>A</h1><input id="q"><label for="q">Search</label></main>')
        main=self.node(result,'main')
        self.assertEqual(self.node(result,'h1')['parent_id'],main['node_id'])
        self.assertEqual(self.node(result,'label')['attributes']['for'],'q')

    def test_duplicate_attributes_keep_first_value_and_raw_pairs(self):
        result=self.parse('<a href="/en/price" href="javascript:bad()">Coins</a>')
        anchor=self.node(result,'a')
        self.assertEqual(anchor['attributes']['href'],'/en/price')
        self.assertEqual(anchor['attribute_pairs'],[['href','/en/price'],['href','javascript:bad()']])

    def test_preserves_list_and_table_ancestry(self):
        result=self.parse('<ul><li>One</li></ul><table role="presentation"><tr><th scope="col">Asset</th></tr></table>')
        li=self.node(result,'li');self.assertEqual(li['ancestor_tags'],['ul'])
        self.assertEqual(self.node(result,'th')['attributes']['scope'],'col')
        self.assertEqual(self.node(result,'table')['attributes']['role'],'presentation')

    def test_empty_alt_and_missing_alt_are_distinct(self):
        images=[n for n in self.parse('<img alt=""><img>')['nodes'] if n['tag']=='img']
        self.assertEqual(images[0]['attributes']['alt'],'')
        self.assertNotIn('alt',images[1]['attributes'])

    def test_node_limit_marks_partial_without_silently_certifying_absence(self):
        result=self.parse('<div>A</div><h1>B</h1>',max_nodes=1)
        self.assertEqual(len(result['nodes']),1);self.assertEqual(result['coverage']['nodes'],'partial')

    def test_text_limit_marks_element_truncation(self):
        result=self.parse('<h1>abcdef</h1>',max_text_chars=3)
        self.assertEqual(self.node(result,'h1')['source_text'],'abc')
        self.assertTrue(self.node(result,'h1')['text_truncated'])

    def test_invalid_limits_rejected(self):
        for kw in [{'max_nodes':0},{'max_text_chars':-1}]:
            with self.assertRaises(ValueError):self.parse('<main/>',**kw)

    def test_unclosed_markup_remains_source_evidence_not_html5_dom(self):
        result=self.parse('<p>First<div>Second')
        self.assertEqual(result['representation'],'source_elements')
        self.assertFalse(result['html5_dom_parser']);self.assertEqual(result['url'],URL)

    def test_source_snippet_is_actual_start_tag(self):
        result=self.parse('<iframe title="Project video" src="/embed"></iframe>')
        self.assertEqual(self.node(result,'iframe')['snippet'],'<iframe title="Project video" src="/embed">')
