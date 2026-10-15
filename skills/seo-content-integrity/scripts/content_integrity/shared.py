"""Use established evidence/time primitives without executing skill 003."""

import sys as _site_sys
from pathlib import Path as _SitePath
_site_dependency=_SitePath(__file__).resolve().parents[3]/'seo-crawlability/scripts'
if str(_site_dependency) not in _site_sys.path:_site_sys.path.insert(0,str(_site_dependency))
from crawlability.site import get_profile,site_host,site_origin,allowed_hosts,in_scope,require_url,brand_name,business_profile
import sys
from pathlib import Path
root=Path(__file__).resolve().parents[3]/'seo-crawlability/scripts'
if not (root/'crawlability/common.py').is_file():raise ImportError('Requires sibling seo-crawlability')
if str(root) not in sys.path:sys.path.insert(0,str(root))
from crawlability.common import url_id,moment,fresh
