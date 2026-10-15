"""Inspect each acquired XML file; never treat parse failure as an empty list."""
import gzip
import io
import re
import xml.etree.ElementTree as ET
from collections import defaultdict
from datetime import datetime, timezone
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

NS = "http://www.sitemaps.org/schemas/sitemap/0.9"
SENSITIVE = {"token", "access_token", "refresh_token", "password", "passwd", "secret", "api_key", "apikey", "session", "sessionid", "email", "authorization", "id_token", "auth_code"}

def date(value):
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}(?:T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2}))?", value):
        raise ValueError("invalid_timestamp")
    return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=timezone.utc) if len(value)==10 else datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)

def safe_url(value):
    try:
        p = urlsplit(value)
        query = urlencode([(k, "[REDACTED]" if k.lower() in SENSITIVE else v) for k,v in parse_qsl(p.query, keep_blank_values=True)])
        return urlunsplit((p.scheme, p.netloc.rsplit("@",1)[-1], p.path, query, ""))
    except (ValueError, TypeError):
        return "[invalid URL]"

def identity(value):
    if not isinstance(value, str) or not value or len(value)>=2048 or re.search(r'[\x00-\x20\x7f\\<>"\x27]|%(?![0-9A-Fa-f]{2})', value):
        raise ValueError("invalid_url")
    p = urlsplit(value)
    if p.scheme.lower() not in {"http", "https"} or not p.hostname or p.username is not None or p.password is not None:
        raise ValueError("invalid_url")
    port = p.port
    if not p.netloc.isascii():raise ValueError('Unicode hostnames are not supported; use explicit ASCII punycode A-labels')
    host = p.hostname.lower()
    host = '['+host+']' if ':' in host else host
    if port is not None and port != (443 if p.scheme.lower()=="https" else 80):
        host += ':'+str(port)
    return urlunsplit((p.scheme.lower(), host, p.path or '/', p.query, p.fragment))

class NoDTD(ET.TreeBuilder):
    def doctype(self, name, pubid, system):
        raise ValueError("doctype")

def inspect_xml(body, document_url, at, max_bytes=52_428_800):
    clock = date(at)
    result = {"url": document_url, "kind": "unknown", "entries": [], "findings": [], "parsed_complete": False, "uncompressed_bytes": None}
    def flag(rule, value=None, position=None):
        result["findings"].append({"rule": rule, "url": document_url, "value": value, "position": position})
    try:
        if body.startswith(b'\x1f\x8b'):
            with gzip.GzipFile(fileobj=io.BytesIO(body)) as stream:
                body = stream.read(max_bytes+1)
    except (OSError, EOFError):
        flag("sitemap_gzip_invalid")
        return result
    result["uncompressed_bytes"] = len(body)
    if len(body)>max_bytes:
        flag("sitemap_size_limit", {"observed_at_least":len(body), "limit":max_bytes})
        return result
    try:
        text = body.decode('utf-8-sig')
        encoding = re.search(r'<\?xml[^>]*encoding=[\x22\x27]([^\x22\x27]+)', text, re.I)
        if encoding and encoding.group(1).lower() not in {'utf-8','utf8'}:
            flag("sitemap_encoding", encoding.group(1))
    except UnicodeDecodeError:
        text = ""
        flag("sitemap_encoding", "not_utf8")
    if re.match(r'\s*(?:<!doctype\s+html|<html\b)', text, re.I):
        flag("sitemap_not_xml", "html_response")
        return result
    try:
        root = ET.fromstring(body, parser=ET.XMLParser(target=NoDTD()))
    except ValueError:
        flag("sitemap_doctype")
        return result
    except ET.ParseError:
        flag("sitemap_xml_invalid")
        return result
    local = root.tag.split('}')[-1]
    if local not in {'urlset','sitemapindex'}:
        flag("sitemap_not_xml", local)
        return result
    result['kind'] = 'index' if local=='sitemapindex' else 'urlset'
    result['parsed_complete'] = True
    prefix = root.tag[:-len(local)]
    if prefix != '{'+NS+'}':
        flag("sitemap_namespace", prefix)
        result['parsed_complete'] = False
    expected_tag = 'sitemap' if local=='sitemapindex' else 'url'
    if not len(root):flag('sitemap_empty',0)
    if len(root)>50000:
        flag("sitemap_entry_limit", len(root))
    seen=defaultdict(list)
    for position,item in enumerate(root,1):
        if item.tag != prefix+expected_tag:
            flag("sitemap_structure", item.tag, position)
            result['parsed_complete']=False
            continue
        locs=item.findall(prefix+'loc')
        if len(locs)!=1:
            flag("sitemap_loc_count", len(locs), position)
            result['parsed_complete']=False
            continue
        raw=(locs[0].text or '').strip()
        try:
            url=identity(raw)
        except (ValueError, UnicodeError):
            flag("sitemap_loc_invalid", safe_url(raw), position)
            result['parsed_complete']=False
            continue
        p=urlsplit(url)
        if any(k.lower() in SENSITIVE for k,_ in parse_qsl(p.query,keep_blank_values=True)):
            flag("sitemap_sensitive_url", safe_url(url), position)
            result['parsed_complete']=False
            continue
        if p.fragment:
            flag("sitemap_fragment", url, position)
        lastmods=item.findall(prefix+'lastmod')
        lastmod=(lastmods[0].text or '') if lastmods else None
        if len(lastmods)>1:
            flag("lastmod_duplicate", len(lastmods), position)
        if lastmod is not None:
            try:
                parsed=date(lastmod)
                if parsed>clock:
                    flag("lastmod_future", lastmod, position)
            except ValueError:
                flag("lastmod_invalid", lastmod, position)
        result['entries'].append({'url':url,'raw_url':raw,'lastmod':lastmod,'position':position})
        seen[url].append(position)
    for url,positions in seen.items():
        if len(positions)>1:
            flag("sitemap_duplicate_entry", {'url':url,'positions':positions})
    return result
