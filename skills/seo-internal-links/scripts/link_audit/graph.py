"""Observed directed graph: source deduplication, scoped shortest paths, no orphan proof."""
import math
from collections import deque
from .shared import url_id,moment,fresh

def build_graph(captures,assets,seeds,*,at,max_age_hours=168,depth_hint=4):
    moment(at)
    if not isinstance(depth_hint,int) or isinstance(depth_hint,bool) or depth_hint<0:raise ValueError('invalid_depth_hint')
    if not math.isfinite(max_age_hours) or max_age_hours<=0:raise ValueError('invalid_freshness_window')
    inventory={url_id(x['url'] if isinstance(x,dict) else x) for x in assets}
    if not inventory or not isinstance(seeds,dict) or not seeds:raise ValueError('explicit_inventory_and_seeds_required')
    normalized={}
    for name,urls in seeds.items():
        if not isinstance(name,str) or not name or not isinstance(urls,list) or not urls:raise ValueError('invalid_seed_group')
        normalized[name]=sorted({url_id(u) for u in urls})
    ids={};latest={}
    for c in captures:
        key=c['snapshot_id']
        if key in ids and ids[key]!=c:raise ValueError('conflicting_capture_identity')
        ids[key]=c
    for c in ids.values():
        key=(url_id(c['url']),c['representation'],c.get('entry_mode','unknown'))
        if key not in latest or moment(c['captured_at'])>moment(latest[key]['captured_at']):latest[key]=c
    result={'at':at,'nodes':{},'edges':[],'paths':{},'depth_hints':[],'gaps':[],
        'coverage':{'full_site':False,'engine_discovery_proven':False,'inventory_assets':len(inventory),'observed_source_pages':0,'excluded_conditional_links':0,'excluded_interaction_captures':0,'raw_edge_occurrences':0,'unique_edges':0},'selected_snapshots':[]}
    nodes=set(inventory);sources=set();edges={}
    for seed_urls in normalized.values():nodes.update(seed_urls)
    for key,c in sorted(latest.items()):
        source=key[0];result['selected_snapshots'].append(c['snapshot_id'])
        if c.get('state','completed')!='completed' or not fresh(c.get('captured_at'),at,max_age_hours) or (c['representation']=='rendered_html' and c.get('readiness')!='ready'):
            result['gaps'].append({'url':source,'snapshot_id':c['snapshot_id'],'reason':'latest_capture_not_current_ready'});continue
        if c.get('discovery_mode')=='interaction_only':result['coverage']['excluded_interaction_captures']+=1;continue
        sources.add(source);nodes.add(source)
        for link in c.get('links',[]):
            if link.get('conditional_noscript'):result['coverage']['excluded_conditional_links']+=1;continue
            if not link.get('http_link') or not link.get('internal') or not link.get('target'):continue
            target=url_id(link['target'])
            if source==target:continue
            nodes.add(target);edge=edges.setdefault((source,target),{'source':source,'target':target,'occurrences':[]})
            edge['occurrences'].append({'snapshot_id':c['snapshot_id'],'document_sha256':c.get('document_sha256'),'captured_at':c['captured_at'],'representation':c['representation'],'entry_mode':c.get('entry_mode'),'source':c.get('source'),**link})
    outgoing={};incoming={}
    for key,edge in sorted(edges.items()):
        source,target=key;outgoing.setdefault(source,set()).add(target);incoming.setdefault(target,set()).add(source)
        edge['all_observed_links_nofollow']=all('nofollow' in x.get('rel',[]) for x in edge['occurrences']);result['edges'].append(edge)
    roots={x for group in normalized.values() for x in group}
    for url in sorted(nodes):
        inbound=sorted(incoming.get(url,set()))
        result['nodes'][url]={'url':url,'inventory_member':url in inventory,'inbound_source_count':len(inbound),'observed_inbound_sources':inbound,'outgoing_observed':url in sources,
            'status':'observed_inbound' if inbound else 'declared_seed' if url in roots else 'no_observed_inbound_candidate'}
    for name,group in sorted(normalized.items()):
        paths={u:{'depth':None,'path':None} for u in sorted(nodes)};queue=deque()
        for u in group:
            paths[u]={'depth':0,'path':[u]};queue.append(u)
            if u not in sources:result['gaps'].append({'reason':'seed_source_not_observed','seed_group':name,'url':u})
        while queue:
            source=queue.popleft()
            for target in sorted(outgoing.get(source,set())):
                if paths[target]['depth'] is not None:continue
                paths[target]={'depth':paths[source]['depth']+1,'path':paths[source]['path']+[target]};queue.append(target)
        for u,p in paths.items():
            if p['depth'] is not None and p['depth']>depth_hint:result['depth_hints'].append({'url':u,'seed_group':name,**p,'threshold':depth_hint,'classification':'review_hint','limitation':'Observed graph path only; threshold is not a ranking rule.'})
        result['paths'][name]=paths
    result['coverage'].update(observed_source_pages=len(sources),raw_edge_occurrences=sum(len(e['occurrences']) for e in result['edges']),unique_edges=len(edges))
    return result
