"""Conservative URL identity: business semantics are never canonicalized away."""

import sys as _site_sys
from pathlib import Path as _SitePath
_site_dependency=_SitePath(__file__).resolve().parents[3]/'seo-crawlability/scripts'
if str(_site_dependency) not in _site_sys.path:_site_sys.path.insert(0,str(_site_dependency))
from crawlability.site import get_profile,site_host,site_origin,allowed_hosts,require_url,brand_name,business_profile
from crawlability.site import in_scope as policy_in_scope

import re
from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit, urlunsplit

SENSITIVE = {"access_token", "refresh_token", "token", "id_token", "password",
             "passwd", "secret", "api_key", "apikey", "session", "sessionid",
             "authorization", "email", "auth_code"}
LOCALES = set("en en-us zh-cn zh-tw zh-hk zh-tc ja ja-jp ko ko-kr ru ru-ru es es-es pt pt-br fr fr-fr de de-de it it-it tr tr-tr vi vi-vn th th-th id id-id ar ar-ar uk pl nl fa hi bn cs ro hu sv fil km my ta ur kk".split())


def normalize_url(value, base=None):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("empty_url")
    value = value.strip()
    if re.search(r"[\x00-\x20\x7f\\]", value):
        raise ValueError("unsafe_url_characters")
    value = urljoin(base, value) if base else value
    try:
        p = urlsplit(value)
        if p.scheme.lower() not in {"http", "https"} or not p.hostname:
            raise ValueError("http_url_required")
        if p.username is not None or p.password is not None:
            raise ValueError("url_credentials_not_allowed")
        host = p.hostname.lower()
        port = p.port
    except (ValueError, UnicodeError) as e:
        raise ValueError("invalid_url") from e
    if not p.netloc.isascii():raise ValueError('Unicode hostnames are not supported; use explicit ASCII punycode A-labels')
    if ":" in host:
        host = "[" + host + "]"
    if port and port != (443 if p.scheme.lower() == "https" else 80):
        host += ":" + str(port)
    fragment = p.fragment if p.fragment.startswith(("/", "!/")) else ""
    return urlunsplit((p.scheme.lower(), host, p.path or "/", p.query, fragment))


def redact_url(value):
    try:
        p = urlsplit(value)
        pairs = [(k, "[REDACTED]" if k.lower() in SENSITIVE else v)
                 for k, v in parse_qsl(p.query, keep_blank_values=True)]
        host = p.netloc.rsplit("@", 1)[-1]
        return urlunsplit((p.scheme, host, p.path, urlencode(pairs), ""))
    except (ValueError, TypeError):
        return "[invalid URL]"


def in_scope(value, allowed_hosts):
    try:
        p = urlsplit(normalize_url(value))
        return (policy_in_scope(value) and p.hostname in {h.lower() for h in allowed_hosts}
                and p.port in (None, 80 if p.scheme == "http" else 443)
                and not any(k.lower() in SENSITIVE for k, _ in parse_qsl(p.query)))
    except ValueError:
        return False


# Group only observed instances of known public routes. Unknown paths stay literal.
PATTERNS = [
    (r"/price/page/(?P<page>\d+)", "/price/page/{page}"),
    (r"/price/(?P<asset>[^/]+)/historical-data", "/price/{asset}/historical-data"),
    (r"/price/(?P<asset>[^/]+)", "/price/{asset}"),
    (r"/price-prediction/(?P<asset>[^/]+)", "/price-prediction/{asset}"),
    (r"/how-to-buy/(?P<asset>[^/]+)/(?P<country>[^/]+)", "/how-to-buy/{asset}/{country}"),
    (r"/how-to-buy/(?P<asset>[^/]+)", "/how-to-buy/{asset}"),
    (r"/converter/(?P<asset>[^/]+)/(?P<currency>[^/]+)", "/converter/{asset}/{currency}"),
    (r"/spot/(?P<pair>[^/]+)", "/spot/{pair}"),
    (r"/futures/(?P<product>[^/]+)/(?P<pair>[^/]+)", "/futures/{product}/{pair}"),
    (r"/support/articles/(?P<article>[^/]+)", "/support/articles/{article}"),
    (r"/support/categories/(?P<category>[^/]+)", "/support/categories/{category}"),
    (r"/learn/article/(?P<article>[^/]+)", "/learn/article/{article}"),
    (r"/learn/(?P<section>[^/]+)/(?P<article>[^/]+)", "/learn/{section}/{article}"),
    (r"/news/(?P<section>[^/]+)/(?P<article>[^/]+)", "/news/{section}/{article}"),
    (r"/blog/(?P<article>[^/]+)", "/blog/{article}"),
]
STATIC = {"", "/", "/about", "/download", "/price", "/how-to-buy", "/converter",
          "/CopyTrading", "/CopyTrading/leaderboard", "/CopyTrading/leaderBoard",
          "/market", "/market/all", "/market/favorite", "/market/new-listings",
          "/learn", "/news", "/blog", "/support", "/login", "/register",
          "/xpool", "/launchpad", "/robots.txt", "/sitemap.xml"}


def classify(value):
    p = urlsplit(normalize_url(value))
    if business_profile() != 'bingx':
        for row in get_profile().get('route_patterns', []):
            match=re.fullmatch(row['pattern'],p.path)
            if match:
                return {'host':p.hostname,'locale':row.get('locale',''),'template':row['template'],'entities':match.groupdict(),'classified':True,'kind':'page'}
        kind='technical' if p.path.endswith(('.xml','.xml.gz')) or p.path=='/robots.txt' else 'page'
        return {'host':p.hostname,'locale':'','template':p.path,'entities':{},'classified':False,'kind':kind}
    bits = p.path.split("/")
    locale = bits[1] if len(bits) > 1 and bits[1] in LOCALES else ""
    prefix = "/{locale}" if locale else ""
    path = "/" + "/".join(bits[2:]) if locale else p.path
    path = path.rstrip("/")
    template, entities, classified = prefix + path, {}, path in STATIC
    for pattern, replacement in PATTERNS:
        match = re.fullmatch(pattern, path)
        if match:
            template, entities, classified = prefix + replacement, match.groupdict(), True
            break
    pairs = dict(parse_qsl(p.query, keep_blank_values=True))
    if path in {"/xpool/detail", "/launchpad/detail"} and "currency" in pairs:
        template, entities, classified = prefix + path + "?currency={currency}", {"currency": pairs["currency"]}, True
    if path == "/CopyTrading" and "type" in pairs:
        template += "?type={type}"
        entities["type"] = pairs["type"]
    kind = "technical" if path.endswith((".xml", ".xml.gz")) or path == "/robots.txt" else "page"
    return {"host": p.hostname, "locale": locale, "template": template or "/",
            "entities": entities, "classified": classified, "kind": kind}
