"""Element-level semantic reviews; do not invent search-index or compliance outcomes."""
import hashlib
import re
from .shared import site_host,moment,fresh,url_id

def audit_elements(capture,*,at,max_age_hours=168,purposes=None):
    moment(at);url=url_id(capture['url'])
    result={'url':url,'findings':[],'handoffs':[],'gaps':[],'reviewed_topics':[],'pending_reviews':['heading_topic_hierarchy','list_and_table_purpose','link_and_button_purpose']}
    gaps=set()
    if not fresh(capture.get('captured_at'),at,max_age_hours):gaps.add('current_snapshot_required')
    if not all(capture.get(key) for key in ('snapshot_id','source','document_sha256')):gaps.add('snapshot_provenance_required')
    if capture.get('representation')!='rendered_elements' or capture.get('readiness')!='ready':gaps.add('stable_rendered_elements_required')
    if gaps:result['gaps']=sorted(gaps);return result
    nodes=capture.get('nodes')
    if not isinstance(nodes,list):raise ValueError('element_list_required')
    if any(not isinstance(n,dict) or not n.get('node_id') or not isinstance(n.get('tag'),str) or not isinstance(n.get('attributes'),dict) for n in nodes):raise ValueError('invalid_element')
    ids={n['node_id']:n for n in nodes}
    if len(ids)!=len(nodes):raise ValueError('duplicate_element_id')
    complete=capture.get('coverage',{}).get('nodes')=='complete'
    if not complete:gaps.add('element_coverage')
    visible=[]
    for n in nodes:
        if n.get('visibility')=='visible':visible.append(n)
        elif n.get('visibility')!='hidden':gaps.add('visibility')
    valid_purposes={}
    for purpose in purposes or []:
        if purpose.get('snapshot_id')!=capture['snapshot_id'] or purpose.get('document_sha256')!=capture['document_sha256'] or purpose.get('node_id') not in ids or not purpose.get('source') or not fresh(purpose.get('checked_at'),at,max_age_hours):
            gaps.add('purpose_evidence_binding');continue
        valid_purposes[purpose['node_id']]=purpose
    def locator(n):
        if n is None:return {'document':url}
        return {k:n[k] for k in ('node_id','selector','source_path','location','snippet') if k in n}
    def add(rule,node,domain,recommendation,retest,classification='semantic_review'):
        loc=locator(node);anchor=loc.get('selector') or loc.get('source_path') or loc.get('node_id') or 'document'
        key=site_host()+'|006|'+url+'|'+rule+'|'+str(anchor)
        result['findings'].append({'issue_id':'semantic-'+hashlib.sha256(key.encode()).hexdigest()[:24],'url':url,'rule':rule,
            'owner_skill':'006','classification':classification,'impact_domain':domain,'locator':loc,'observed_at':at,
            'recommendation':recommendation,'retest':retest,'evidence':{'snapshot_id':capture['snapshot_id'],'document_sha256':capture['document_sha256'],
                'captured_at':capture['captured_at'],'source':capture['source'],'element':node}})
    mains=[n for n in visible if n['tag']=='main' or n['attributes'].get('role')=='main']
    if complete and capture.get('scope')=='document' and 'visibility' not in gaps and not mains:
        add('main_landmark_missing',None,'semantic_structure','为页面主要内容设置合适的main或main landmark，先核对实际布局和重复区域。','稳定页面的可访问树能定位主内容；不以此宣称影响收录。')
    navs=[n for n in visible if n['tag']=='nav' or n['attributes'].get('role')=='navigation']
    if len(navs)>1:
        for n in navs:
            if n.get('accessible_name') is None:gaps.add('accessible_names')
            elif not n['accessible_name'].strip():
                add('navigation_landmark_name_review',n,'accessibility','复核多个导航区域的用途；不同导航需要可理解的区分名称，相同用途/链接的重复导航不机械改名。','用可访问树及实际链接集合区分主导航、相关导航与页脚导航。')
    previous_heading=None
    for n in visible:
        tag=n['tag'];attrs=n['attributes'];name=n.get('accessible_name');text=n.get('text')
        if re.fullmatch('h[1-6]',tag):
            if text is not None and not text.strip() and name=='':
                add('empty_heading',n,'semantic_structure','填入准确反映下文主题的标题，或将纯占位容器改为合适元素。','在加载完成的DOM与可访问树中确认该标题有合理内容。')
            elif name is None and not text:gaps.add('accessible_names')
            level=int(tag[1])
            if previous_heading is not None and level>previous_heading+1:
                add('heading_level_review',n,'semantic_structure','结合页面主题与分节复核标题层级，避免只因视觉字号选择h标签。','按内容顺序阅读标题大纲，确认层级合理；跳级并非自动HTML不合规或索引失败。')
            previous_heading=level
        if tag in {'button','input','select','textarea','iframe'} or attrs.get('role') in {'button','textbox','combobox'}:
            if tag=='input' and attrs.get('type','').lower()=='hidden':continue
            if name is None:gaps.add('accessible_names')
            elif not name.strip():
                add('iframe_name_missing' if tag=='iframe' else 'control_name_missing',n,'accessibility',
                    '提供能说明用途的可访问名称；表单优先关联真实label，iframe使用明确标题并按实际可访问名称复核。',
                    '用可访问树及axe复查名称、用途和关联；不只看视觉文字。','accessibility_observation')
        purpose=valid_purposes.get(n['node_id'],{})
        navigation=attrs.get('role')=='link' or purpose.get('purpose')=='navigation'
        href=attrs.get('href','').strip()
        crawlable=tag=='a' and bool(href) and not href.lower().startswith(('javascript:','data:'))
        if navigation and not crawlable:
            add('navigation_without_crawlable_href',n,'seo_discovery','若实际用途是打开内容页，提供真实a[href]与可达目标；保留必要客户端行为。','核对原始/渲染链接目标与实际点击去向；动作控件仍用button。')
        if (tag=='li' or attrs.get('role')=='listitem') and complete:
            parent=ids.get(n.get('parent_id'))
            if parent is not None and parent['tag'] not in {'ul','ol','menu'} and parent['attributes'].get('role') not in {'list','group'}:
                add('list_structure_review',n,'semantic_structure','核对列表项与列表容器、分组的实际关系；HTML语法由Nu独立确认。','稳定DOM与可访问树中列表关系正确，避免纯视觉缩进冒充列表。')
        if tag=='table' and attrs.get('role') not in {'presentation','none'} and complete:
            def belongs(child):
                parent=child.get('parent_id');seen=set()
                while parent in ids and parent not in seen:
                    seen.add(parent);ancestor=ids[parent]
                    if ancestor['tag']=='table':return parent==n['node_id']
                    parent=ancestor.get('parent_id')
                return False
            cells=[child for child in nodes if child['tag'] in {'td','th'} and belongs(child)]
            if cells and not any(child['tag']=='th' for child in cells):
                add('table_header_review',n,'semantic_structure','先确认是数据表还是布局；数据表应有正确表头及关联，布局不应伪装数据表。','按实际内容核对th、scope/headers或等价可访问结构，不机械补表头。')
        if tag=='img' and ('alt' not in attrs or attrs['alt']==''):
            result['handoffs'].append({'owner_skill':'013','url':url,'locator':locator(n),'question':'decorative_or_informative',
                'alt_state':'missing' if 'alt' not in attrs else 'empty','snapshot_id':capture['snapshot_id'],'document_sha256':capture['document_sha256']})
    for review in capture.get('semantic_reviews',[]):
        bound=review.get('snapshot_id')==capture['snapshot_id'] and review.get('document_sha256')==capture['document_sha256']
        current=bool(review.get('source')) and fresh(review.get('checked_at'),at,max_age_hours)
        affected=review.get('nodes',[]);quotes=review.get('quotes',{})
        quoted=isinstance(affected,list) and bool(affected) and isinstance(quotes,dict) and all(
            identity in ids and isinstance(quotes.get(identity),str) and bool(quotes[identity].strip()) and quotes[identity] in (ids[identity].get('text') or '') for identity in affected)
        valid=bound and current and quoted and review.get('topic') in result['pending_reviews'] and review.get('status') in {'needs_change','looks_reasonable','unknown'}
        if not valid:gaps.add('semantic_review_evidence');continue
        if review.get('status')=='unknown':continue
        result['reviewed_topics'].append(review['topic'])
        if review['status']=='needs_change':
            if not all(review.get(k) for k in ('reason','recommendation','retest')):gaps.add('semantic_review_evidence');continue
            add('model_semantic_review',ids[affected[0]],'semantic_structure',review['recommendation'],review['retest'],'model_review')
            result['findings'][-1]['evidence']['review']=dict(review)
    result['reviewed_topics']=sorted(set(result['reviewed_topics']))
    result['gaps']=sorted(gaps)
    return result
