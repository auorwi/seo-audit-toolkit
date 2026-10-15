"""Extract declarations and occurrences, keeping them distinct from browser observations."""
from collections import Counter
from .shared import parse_html
from .srcset import parse_srcset,resolve_resource

def extract_html(html,url,*,max_nodes=50000):
    parsed=parse_html(html,url,max_nodes=max_nodes);nodes=parsed['nodes'];by_id={n['node_id']:n for n in nodes}
    result={'url':parsed['url'],'source_sha256':parsed['source_sha256'],'images':[],'videos':[],'embeds':[],'metadata_images':[],'resource_refs':[],'gaps':[],'coverage':parsed['coverage'],'html5_dom_parser':False}
    base=parsed['url']
    for node in nodes:
        if node['tag']=='base' and 'href' in node['attributes'] and not node['inert_hint']:
            declared=resolve_resource(node['attributes']['href'],base)
            if declared and declared.startswith(('https://','http://')):base=declared
            else:result['gaps'].append({'reason':'unsupported_base_url','raw':node['attributes']['href']})
            break
    result['base_url']=base
    def ref(value,kind,role,node):
        if value:result['resource_refs'].append({'url':value,'kind':kind,'role':role,'node_id':node['node_id'],'source_path':node['source_path']})
    def srcset(raw,node):
        r=parse_srcset(raw or '',base)
        for gap in r['gaps']:result['gaps'].append({**gap,'node_id':node['node_id'],'source_path':node['source_path']})
        return r
    for index,node in enumerate(nodes):
        if node['inert_hint']:continue
        attrs=node['attributes'];tag=node['tag']
        if tag not in {'img','picture','video','iframe','embed','object','meta'}:continue
        duplicates=[key for key,count in Counter(p[0] for p in node['attribute_pairs']).items() if count>1]
        if duplicates:result['gaps'].append({'reason':'duplicate_media_attribute','node_id':node['node_id'],'attributes':duplicates})
        common={'node_id':node['node_id'],'source_path':node['source_path'],'tag':tag,'attributes':attrs,'snippet':node['snippet'],
                'visibility':'unknown','purpose':'unknown','context':'noscript' if 'noscript' in node['ancestor_tags'] else 'ordinary',
                'width_attribute':attrs.get('width'),'height_attribute':attrs.get('height'),'loading':attrs.get('loading'),'title':attrs.get('title')}
        if tag=='img':
            row={**common,'src_url':resolve_resource(attrs.get('src'),base),'src_raw':attrs.get('src'),'alt_present':'alt' in attrs,'alt':attrs.get('alt'),
                 'sizes':attrs.get('sizes'),'srcset':srcset(attrs.get('srcset'),node),'picture_sources':[],'current_src':None}
            parent=by_id.get(node['parent_id'])
            if parent and parent['tag']=='picture':
                for source in nodes[:index]:
                    if source['parent_id']==parent['node_id'] and source['tag']=='source':
                        a=source['attributes'];candidates=srcset(a.get('srcset'),source)
                        s={'node_id':source['node_id'],'media':a.get('media'),'type':a.get('type'),'sizes':a.get('sizes'),**candidates};row['picture_sources'].append(s)
                        for c in s['candidates']:ref(c['url'],'image','picture_candidate',source)
            ref(row['src_url'],'image','img_src',node)
            for c in row['srcset']['candidates']:ref(c['url'],'image','img_srcset_candidate',node)
            result['images'].append(row)
        elif tag=='picture':
            if not any(n['parent_id']==node['node_id'] and n['tag']=='img' for n in nodes):result['gaps'].append({'reason':'picture_missing_img','node_id':node['node_id'],'source_path':node['source_path']})
        elif tag=='video':
            row={**common,'src_url':resolve_resource(attrs.get('src'),base),'poster_url':resolve_resource(attrs.get('poster'),base),'controls':'controls' in attrs,
                 'autoplay':'autoplay' in attrs,'muted':'muted' in attrs,'preload':attrs.get('preload'),'sources':[],'current_src':None}
            for source in nodes:
                if source['parent_id']==node['node_id'] and source['tag']=='source':
                    a=source['attributes'];s={'node_id':source['node_id'],'url':resolve_resource(a.get('src'),base),'type':a.get('type'),'media':a.get('media')};row['sources'].append(s);ref(s['url'],'video','video_source_candidate',source)
            ref(row['src_url'],'video','video_src',node);ref(row['poster_url'],'image','video_poster',node);result['videos'].append(row)
        elif tag in {'iframe','embed','object'}:
            row={**common,'src_url':resolve_resource(attrs.get('data') if tag=='object' else attrs.get('src'),base),'srcdoc_present':'srcdoc' in attrs}
            ref(row['src_url'],'embed_document','embed_src',node);result['embeds'].append(row)
        elif tag=='meta':
            key=(attrs.get('property') or attrs.get('name') or '').lower()
            if key in {'og:image','og:image:url','og:image:secure_url','twitter:image','twitter:image:src'}:
                resource=resolve_resource(attrs.get('content'),base);result['metadata_images'].append({**common,'property':key,'url':resource});ref(resource,'image','metadata_image',node)
    return result
