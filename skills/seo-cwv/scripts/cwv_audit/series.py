"""Repeated comparable laboratory measurements, with no best-run selection."""
import statistics,math
from .shared import url_id
from .metrics import rating

def summarize_lab(runs,minimum=3):
    if type(minimum) is not int or minimum<3:raise ValueError('at_least_three_valid_runs_required')
    groups={};excluded=[];seen=set()
    for r in runs:
        identity=r.get('evidence',{}).get('sha256') or r.get('run_id')
        if not identity:excluded.append({'reason':'run_identity_missing','run':r});continue
        if identity in seen:excluded.append({'reason':'duplicate_run_evidence','run':r});continue
        seen.add(identity)
        if not r.get('valid_measurement') or not r.get('comparable'):excluded.append({'reason':'invalid_or_incomparable_measurement','run':r});continue
        key=(url_id(r['requested_url']),r['device'],r['environment_key'],url_id(r['final_url']))
        groups.setdefault(key,[]).append(r)
    output=[]
    for (url,device,environment,final),items in sorted(groups.items()):
        metrics={}
        for name in ['LCP','CLS','TBT','FCP','SI','TTFB','INP']:
            values=[r['metrics'].get(name) for r in items];values=[v for v in values if type(v) in {int,float} and math.isfinite(v) and v>=0]
            median=statistics.median(values) if values else None
            metrics[name]={'median':median,'min':min(values) if values else None,'max':max(values) if values else None,'n':len(values),'sufficient':len(values)>=minimum,'rating':rating(name,median) if name!='INP' else 'not_measured_by_navigation_lighthouse'}
        suitable=all(r.get('environment_quality',{}).get('suitable_for_regression') is True for r in items)
        output.append({'requested_url':url,'final_url':final,'device':device,'environment_key':environment,'n':len(items),'sufficient':len(items)>=minimum,'suitable_for_regression':suitable,'environment_statuses':sorted({r.get('environment_quality',{}).get('status','environment_data_missing') for r in items}),'metrics':metrics,'runs':items,'statistic':'median_of_all_valid_comparable_runs','field_assessment':'not_available_from_laboratory'})
    return {'groups':output,'excluded':excluded,'minimum_valid_runs':minimum,'all_attempts':len(runs)}

def compare_lab(baseline,current,*,relative_budget=0.1,absolute_budgets=None):
    if not math.isfinite(relative_budget) or relative_budget<0:raise ValueError('invalid_relative_budget')
    budgets=absolute_budgets or {'LCP':300,'CLS':0.02,'TBT':100}
    if any(type(v) not in {int,float} or not math.isfinite(v) or v<0 for v in budgets.values()):raise ValueError('invalid_absolute_budget')
    key=lambda g:(g['requested_url'],g['final_url'],g['device'],g['environment_key'])
    previous={key(g):g for g in baseline['groups']};out={'comparisons':[],'gaps':[]}
    for g in current['groups']:
        old=previous.get(key(g))
        if not old or not old['sufficient'] or not g['sufficient']:out['gaps'].append({'url':g['requested_url'],'device':g['device'],'reason':'comparable_complete_baseline_missing'});continue
        if not old.get('suitable_for_regression') or not g.get('suitable_for_regression'):out['gaps'].append({'url':g['requested_url'],'device':g['device'],'reason':'host_environment_not_suitable_for_regression'});continue
        comparisons={}
        for metric,absolute in budgets.items():
            a=old['metrics'].get(metric,{});b=g['metrics'].get(metric,{})
            if not a.get('sufficient') or not b.get('sufficient'):continue
            before,after=a['median'],b['median'];delta=after-before;required=max(absolute,before*relative_budget)
            comparisons[metric]={'baseline_median':before,'current_median':after,'delta':delta,'relative_change':delta/before if before else None,'absolute_budget':absolute,'relative_budget':relative_budget,'status':'regressed' if delta>required else 'improved' if -delta>required else 'within_budget'}
        out['comparisons'].append({'requested_url':g['requested_url'],'device':g['device'],'environment_key':g['environment_key'],'metrics':comparisons})
    return out
