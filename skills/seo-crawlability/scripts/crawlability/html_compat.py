"""Attribute-context character references, consistently on Python 3.10+.

Keep the interpreter's HTML tokenizer and recovery/CDATA behavior. Older parsers
apply text-context unescaping to attribute values; dispatch corrected values from
its exact raw start tag instead. Callbacks are scoped to this parser instance and
restored even if a consumer raises. No standard-library globals are changed.
"""
import re
from html import unescape
from html.entities import html5
from html.parser import HTMLParser as _StdHTMLParser, attrfind_tolerant, tagfind_tolerant

_REFERENCE=re.compile(r'&(#(?:[xX][0-9a-fA-F]+|[0-9]+);?|[A-Za-z][A-Za-z0-9]*;?)')
_ABSENT=object()


def unescape_attribute(value):
    """Named refs without ';' followed by ASCII alnum or '=' remain literal."""
    def replace(match):
        token=match.group(1)
        if token.startswith('#'):return unescape(match.group(0))
        following=value[match.end():match.end()+1]
        if not token.endswith(';') and following and (following in '=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'):
            return match.group(0)
        return html5.get(token,match.group(0))
    return _REFERENCE.sub(replace,value)


def _attributes(raw):
    # Use the same lexical patterns as the running stdlib parser: preserve every
    # attribute, its order, duplicate names, and valueless/empty distinctions.
    tag=tagfind_tolerant.match(raw,1)
    cursor=tag.end();result=[]
    while cursor<len(raw):
        found=attrfind_tolerant.match(raw,cursor)
        if found is None:break
        name,assignment,value=found.group(1,2,3)
        if not assignment:value=None
        else:
            if len(value)>=2 and value[0] in "\"'" and value[-1]==value[0]:value=value[1:-1]
            value=unescape_attribute(value)
        result.append((name.lower(),value));cursor=found.end()
    return result


class HTMLParser(_StdHTMLParser):
    def parse_starttag(self,index):
        saved={name:self.__dict__.get(name,_ABSENT) for name in ('handle_starttag','handle_startendtag')}
        def correct(callback):
            def dispatch(tag,attrs):
                return callback(tag,_attributes(self.get_starttag_text()))
            return dispatch
        for name in saved:setattr(self,name,correct(getattr(self,name)))
        try:return super().parse_starttag(index)
        finally:
            for name,value in saved.items():
                if value is _ABSENT:self.__dict__.pop(name,None)
                else:setattr(self,name,value)
