"""One page, one actionable checklist; raw findings and issue IDs remain intact."""
import json
from html import escape
from . import shared
from crawlability.report import md

# Only common tag structure belongs in the user-facing checklist.
# Other checker results remain in report.json for evidence review.
RULE_TEXT={
 'main_landmark_missing':'缺少 main 主内容标签。',
 'landmark-one-main':'main 主内容区域需要确认。',
 'page-has-heading-one':'未找到 H1 主标题。',
 'navigation_without_crawlable_href':'页面跳转入口缺少有效的 a[href] 链接。',
 'list_structure_review':'li 与 ul/ol 列表容器的关系不正确，需确认。',
 'list':'ul/ol 列表包含不正确的子元素。',
 'listitem':'li 缺少正确的列表容器。',
 'table_header_review':'数据表缺少正确表头，需确认。',
 'heading_level_review':'标题层级存在跳级，需确认。',
 'heading-order':'标题层级存在跳级，需确认。',
 'empty_heading':'标题标签内容为空。',
 'empty-heading':'标题标签内容为空。',
}
REVIEW_CLASSES={'manual_review','accessibility_best_practice','html_conformance_warning','html_conformance_info','semantic_review'}

def delivery_findings(findings):
    for finding in findings:
        evidence=finding.get('evidence',[])
        evidence=evidence if isinstance(evidence,list) else [evidence]
        reviews=[e for e in evidence if e.get('review',{}).get('recommendation')]
        if finding['classification']=='model_review' and reviews:
            for e in reviews:
                yield {**finding,'recommendation':e['review']['recommendation'],
                       'retest':e['review'].get('retest',finding['retest']),'evidence':[e]}
        else:yield finding

def page_checklist(result):
    rows={r['url']:r for r in result['rows']}
    targets={r['url']:r for r in result.get('scope_plan',{}).get('targets',[])}
    pending={r['url']:r for r in result['pending_reviews']}
    pages=[]
    for url in result['scope']:
        row=rows.get(url,{})
        gaps=[g for g in result['gaps']+result.get('input_gaps',[]) if g.get('url') in {url,None}]
        browser_state=row.get('browser_state') or ('captured' if row.get('rendered_capture') else 'not_checked')
        groups={}
        for f in delivery_findings(result['findings']):
            if f['url']!=url:continue
            if f['rule'] not in RULE_TEXT and f['classification']!='model_review':continue
            evidence=f.get('evidence',[]);evidence=evidence if isinstance(evidence,list) else [evidence]
            message=next((e.get('message') for e in evidence if e.get('message')),'')
            key=(f['rule'],f['classification'],message if f['rule']=='nu-message' else f['recommendation'] if f['classification']=='model_review' else '')
            if key not in groups:
                classification=f['classification'];status='needs_review' if classification in REVIEW_CLASSES else 'needs_change'
                if f['rule']=='navigation_without_crawlable_href':status='needs_change'
                text=RULE_TEXT.get(f['rule']) or next((e.get('review',{}).get('reason') for e in evidence if e.get('review',{}).get('reason')),f['recommendation'])
                groups[key]={'rule':f['rule'],'classification':classification,'status':status,'text':text,
                    'recommendation':f['recommendation'],'retest':f['retest'],'issue_ids':[],'occurrences':0,'examples':[]}
            item=groups[key]
            if f['issue_id'] not in item['issue_ids']:item['issue_ids'].append(f['issue_id'])
            item['occurrences']+=max(1,len(evidence))
            for e in evidence:
                element=e.get('element') or {}
                location=e.get('target') or e.get('location') or element.get('selector') or f.get('locator')
                if location and location not in item['examples'] and len(item['examples'])<2:item['examples'].append(location)
        topics=pending.get(url,{}).get('topics',[])
        pages.append({'url':url,'page_type':targets.get(url,{}).get('page_type') or url,
            'browser_state':browser_state,'status':'incomplete' if browser_state!='ready' or gaps or topics else 'scoped_checks_complete',
            'tools':row.get('tools',[]),'items':list(groups.values()),'gaps':gaps,'pending_topics':topics,
            'media_handoff_count':sum(h.get('url')==url for h in result['handoffs'])})
    return {'schema_version':1,'at':result['at'],'scope_id':result.get('scope_plan',{}).get('scope_id'),'pages':pages}

def render_checklist(output,result):
    data=page_checklist(result);pages=data['pages']
    (output/'page-checklist.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    summary=f"本次检查 {len(pages)} 个页面。"
    lines=['# HTML 标签检查','',summary,'']
    xml=['<title>HTML 标签检查</title>','<p>'+escape(summary)+'</p>']
    for i,page in enumerate(pages,1):
        title=f"{i}. {page['page_type']}"
        lines += ['## '+md(title),'',md(page['url']),'']
        xml += ['<h2>'+escape(title)+'</h2>','<p><a href="'+escape(page['url'],quote=True)+'">'+escape(page['url'])+'</a></p>']
        for item in page['items']:
            text=item['text']
            if item['status']=='needs_review' and '需确认' not in text:text+='（待确认）'
            lines.append('- [ ] '+md(text))
            xml.append('<checkbox done="false">'+escape(text)+'</checkbox>')
        note=''
        if page['browser_state']=='not_checked':note='未检查。'
        elif page['browser_state']!='ready':note='未完成：页面未就绪。'
        elif page['status']=='incomplete':note='未完成：还有标签待确认。'
        elif not page['items']:note='未发现标签问题。'
        if note:
            lines+=['',note];xml.append('<p>'+escape(note)+'</p>')
        lines.append('')
    (output/'report.md').write_text('\n'.join(lines),encoding='utf-8')
    (output/'report.feishu.xml').write_text('\n'.join(xml)+'\n',encoding='utf-8')
