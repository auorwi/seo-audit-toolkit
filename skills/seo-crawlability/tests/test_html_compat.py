"""Attribute-context entities must not change URLs across supported Python versions."""
import html
from html.parser import HTMLParser as StdParser
from support import CrawlTest

class AttributeParsingTests(CrawlTest):
    def parser(self,*,empty=False):
        base=self.module('html_compat').HTMLParser
        class Recorder(base):
            def __init__(self):super().__init__(convert_charrefs=False);self.events=[]
            def handle_starttag(self,tag,attrs):self.events.append((tag,attrs,self.get_starttag_text()))
            def handle_endtag(self,tag):self.events.append(('end',tag))
        return Recorder()

    def test_ambiguous_named_entities_preserve_repeated_query_parameters(self):
        p=self.parser();raw='<a href="/list?currency=84&currency=85&copy=3&notit;=x&AMPx=z">'
        p.feed(raw)
        self.assertEqual(p.events,[('a',[('href','/list?currency=84&currency=85&copy=3&notit;=x&AMPx=z')],raw)])

    def test_valid_named_and_numeric_entities_decode_once(self):
        p=self.parser();p.feed('<a href="/list?a=1&amp;b=2&#38;c=3&#x26;d=4" title="&copy &copy; &#128; &#0; &amp;amp; &unknown;">')
        self.assertEqual(p.events[0][1],[('href','/list?a=1&b=2&c=3&d=4'),('title','© © € � &amp; &unknown;')])

    def test_duplicate_complete_attributes_unquoted_values_and_empty_tags_survive(self):
        p=self.parser();raw="<LINK HREF='/first?currency=84&currency=85' href=/last?a=1&amp;b=2 disabled empty='' data-note='x>y'/>"
        p.feed(raw)
        self.assertEqual(p.events[0],('link',[('href','/first?currency=84&currency=85'),('href','/last?a=1&b=2'),('disabled',None),('empty',''),('data-note','x>y')],raw))
        self.assertEqual(p.events[1],('end','link'))

    def test_chunked_input_keeps_exact_source_and_raw_script_text(self):
        p=self.parser();p.feed('<a href="/?curr');p.feed('ency=84&currency=85">')
        self.assertEqual(p.events[0][1],[('href','/?currency=84&currency=85')])
        self.assertEqual(p.events[0][2],'<a href="/?currency=84&currency=85">')
        base=self.module('html_compat').HTMLParser
        class Script(base):
            def __init__(self):super().__init__();self.text=[]
            def handle_data(self,data):self.text.append(data)
        script=Script();script.feed('<script>{"url":"/?currency=84&currency=85"}</script>')
        self.assertEqual(script.text,['{"url":"/?currency=84&currency=85"}'])

    def test_standard_library_and_instance_callbacks_are_not_modified(self):
        std_parse=StdParser.parse_starttag;std_unescape=html.unescape
        p=self.parser();before={name:p.__dict__.get(name) for name in ('handle_starttag','handle_startendtag')};p.feed('<a href="/?currency=84&currency=85">')
        self.assertIs(StdParser.parse_starttag,std_parse);self.assertIs(html.unescape,std_unescape)
        self.assertEqual({name:p.__dict__.get(name) for name in before},before)

    def test_callback_exception_restores_instance_overrides(self):
        p=self.parser()
        def reject(tag,attrs):raise ValueError('consumer rejection')
        p.handle_starttag=reject
        with self.assertRaisesRegex(ValueError,'consumer rejection'):p.feed('<a href="/?currency=84&currency=85">')
        self.assertIs(p.handle_starttag,reject);self.assertNotIn('handle_startendtag',p.__dict__)
