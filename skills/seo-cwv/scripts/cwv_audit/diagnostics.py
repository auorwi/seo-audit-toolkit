"""Retain resource/node evidence and per-audit estimates without inventing code causes."""
from .field import number
FIXES={
 'unused-javascript':'核对所列资源在实际入口和交互场景的覆盖；验证可延迟或拆分的代码后再修改，不把一次未执行等同可删除。',
 'unused-css-rules':'结合实际断点和交互检查未使用CSS，按组件或模板裁剪；避免删除其他设备需要的规则。',
 'render-blocking-resources':'核对已列阻塞资源与LCP依赖；按实际渲染路径调整加载顺序或关键CSS，不批量添加preload。',
 'render-blocking-insight':'依据具体阻塞资源与LCP时序评估内联关键CSS或延后非关键资源，再同条件复测。',
 'uses-optimized-images':'按实际显示尺寸压缩所列图片，并核对清晰度与替代格式支持；不要改变业务图片含义。',
 'uses-responsive-images':'给所列过大图片提供与显示尺寸匹配的srcset/sizes，并复测移动/桌面实际选图。',
 'uses-long-cache-ttl':'对可版本化静态资源核对缓存策略；动态行情或用户数据不能机械设置长期缓存。'}

def diagnose_lhr(lhr):
    out={'opportunities':[],'elements':[],'long_tasks':[],'gaps':[],'total_savings_ms':None,'estimate_note':'Per-audit estimates may overlap; not summed or guaranteed.'}
    if lhr.get('runtimeError'):out['gaps'].append('lighthouse_runtime_error');return out
    audits=lhr.get('audits',{})
    def walk(value,audit_id,path='$'):
        if isinstance(value,dict):
            if value.get('type')=='node' or ('selector' in value and 'snippet' in value):out['elements'].append({'audit_id':audit_id,'path':path,**value})
            for k,v in value.items():walk(v,audit_id,path+'.'+k)
        elif isinstance(value,list):
            for i,v in enumerate(value):walk(v,audit_id,path+f'[{i}]')
    for audit_id,a in audits.items():
        if not isinstance(a,dict) or a.get('scoreDisplayMode') in {'error','notApplicable','manual'}:continue
        detail=a.get('details',{});walk(detail,audit_id)
        if audit_id=='long-tasks':out['long_tasks'] += [{'audit_id':audit_id,**item} for item in detail.get('items',[]) if isinstance(item,dict)]
        ms=number(detail.get('overallSavingsMs'));size=number(detail.get('overallSavingsBytes'));raw_savings=a.get('metricSavings',{})
        savings={k:number(v) for k,v in raw_savings.items() if number(v) is not None} if isinstance(raw_savings,dict) else {}
        if not ((ms or 0)>0 or (size or 0)>0 or any(v>0 for v in savings.values())):continue
        resources=[]
        def resources_in(v,path='$'):
            if isinstance(v,dict):
                if isinstance(v.get('url'),str):resources.append({'path':path,**v})
                for k,child in v.items():resources_in(child,path+'.'+k)
            elif isinstance(v,list):
                for i,child in enumerate(v):resources_in(child,path+f'[{i}]')
        resources_in(detail)
        out['opportunities'].append({'audit_id':audit_id,'title':a.get('title'),'estimated_savings_ms':ms,'estimated_savings_bytes':size,'metric_savings':savings,'resources':resources,'details':detail,
            'recommendation':FIXES.get(audit_id,'按此审计项的实际节点/资源与时序核查，先验证触发条件与影响，再改对应模板；缺trace或源码时不宣称具体代码根因。'),'classification':'tool_estimate_requires_context_review'})
    if not out['elements']:out['gaps'].append('impact_element_evidence_missing')
    if not out['long_tasks']:out['gaps'].append('interaction_or_long_task_attribution_missing')
    return out
