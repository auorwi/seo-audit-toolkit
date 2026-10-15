"""Review recorded resource bytes and HTTP facts; signatures never prove decoding."""
import re
from urllib.parse import urlsplit
from .shared import fresh,moment
from crawlability.common import header_pairs

def sniff(prefix):
    if prefix.startswith(b'\x89PNG\r\n\x1a\n'):return 'image/png'
    if prefix.startswith(b'\xff\xd8\xff'):return 'image/jpeg'
    if prefix.startswith((b'GIF87a',b'GIF89a')):return 'image/gif'
    if len(prefix)>=14 and prefix.startswith(b'BM'):return 'image/bmp'
    if len(prefix)>=12 and prefix[:4]==b'RIFF' and prefix[8:12]==b'WEBP':return 'image/webp'
    if len(prefix)>=12 and prefix[4:8]==b'ftyp':
        brands=[prefix[i:i+4] for i in range(8,min(len(prefix),64),4)]
        if any(b in {b'avif',b'avis'} for b in brands):return 'image/avif'
        if prefix[8:12] in {b'mp41',b'mp42',b'isom',b'iso2',b'avc1',b'M4V '}:return 'video/mp4'
    text=prefix[:65536].decode('utf-8-sig',errors='replace').lstrip()
    text=re.sub(r'^(?:(?:<\?xml\b[^>]*\?>|<!--.*?-->)\s*)+','',text,flags=re.I|re.S)
    if re.match(r'<svg(?:\s|>)',text,re.I):return 'image/svg+xml'
    if re.match(r'<(?:!doctype\s+html|html|head|body|title|script)(?:\s|>)',text,re.I):return 'text/html'
    if text.startswith('#EXTM3U'):return 'application/vnd.apple.mpegurl'
    return None

def review_resource(row, *, expected_kind, at, max_age_hours=24):
    moment(at)
    if expected_kind not in {'image','video','embed_document'}:raise ValueError('unsupported_media_kind')
    result={'status':'invalid_response_metadata','url':row.get('url'),'expected_kind':expected_kind,'decoded_verified':False,'http_status':row.get('status'),'detected_type':None,'content_type':None}
    try:scheme=urlsplit(row['url']).scheme
    except (KeyError,ValueError,TypeError):return result
    if scheme=='data':return {**result,'status':'inline_resource_requires_browser'}
    if scheme=='blob':return {**result,'status':'session_resource_requires_browser'}
    if scheme not in {'http','https'}:return result
    if not fresh(row.get('captured_at'),at,max_age_hours):return {**result,'status':'stale_response'}
    if row.get('error') or row.get('status') is None:return {**result,'status':'request_failed','error':row.get('error')}
    status=row['status']
    if type(status) is not int or not 100<=status<=599 or not row.get('source'):return result
    if row.get('method')!='GET':return {**result,'status':'headers_only'}
    if status in {404,410}:return {**result,'status':'resource_not_found'}
    if status in {401,403,429}:return {**result,'status':'access_limited'}
    if status>=500:return {**result,'status':'server_error'}
    if 300<=status<400:return {**result,'status':'redirect_unverified'}
    if not 200<=status<300:return {**result,'status':'http_status_review'}
    try:headers=header_pairs(row.get('headers',[]))
    except ValueError:return result
    if status==206 and not any(k=='content-range' and re.fullmatch(r'bytes 0-[0-9]+/(?:[0-9]+|\*)',v.strip()) for k,v in headers):return {**result,'status':'partial_range_uninspected'}
    types={v.split(';',1)[0].strip().lower() for k,v in headers if k=='content-type'}
    if len(types)>1:return {**result,'status':'conflicting_content_types'}
    mime=next(iter(types),None);result['content_type']=mime
    if row.get('body_decoded') is not True and any(k=='content-encoding' and v.strip().lower() not in {'','identity'} for k,v in headers):return {**result,'status':'encoded_body_uninspected'}
    prefix=row.get('body_prefix')
    if not isinstance(prefix,bytes) or not prefix:return {**result,'status':'empty_resource_body' if prefix==b'' and row.get('body_complete') is True else 'body_unobserved'}
    detected=sniff(prefix);result['detected_type']=detected;result['prefix_bytes_observed']=len(prefix)
    if expected_kind=='embed_document':return {**result,'status':'embed_response_observed','playback_verified':False}
    if detected=='text/html':return {**result,'status':'html_instead_of_media'}
    if detected is None:return {**result,'status':'unrecognized_media_prefix'}
    if expected_kind=='image':
        if not detected.startswith('image/'):return {**result,'status':'unexpected_resource_type'}
        if mime in {None,'','application/octet-stream','binary/octet-stream'}:return {**result,'status':'image_response_generic_mime'}
        if detected=='image/jpeg' and mime in {'image/jpg','image/pjpeg'}:return {**result,'status':'image_response_mime_alias'}
        return {**result,'status':'image_response_observed' if mime==detected else 'mime_signature_mismatch'}
    if detected=='application/vnd.apple.mpegurl':return {**result,'status':'video_playlist_observed','playback_verified':False}
    if detected.startswith('image/'):return {**result,'status':'unexpected_resource_type'}
    if detected=='video/mp4':return {**result,'status':'video_response_observed' if mime in {'video/mp4','application/octet-stream',None} else 'mime_signature_mismatch','playback_verified':False}
    return {**result,'status':'unrecognized_media_prefix'}
