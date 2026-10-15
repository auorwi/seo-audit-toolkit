"""Compose current scoped checks, evidence-supported issues and explicit gaps."""
import hashlib,math
from .shared import site_host,require_url,moment,url_id
from .comparison import check_pair
from .forecast import check_summary
from .calculator import check_trial,check_suite
from .claims import check_claim

CONFLICTS={'conflict','year_value_conflict','calculation_conflict','unit_conflict','direction_conflict','empty_template_field','unexpanded_placeholder','stale_data_live_claim','lifecycle_conflict','invalid_numeric_display'}
CANDIDATES={'possible_year_shift','potential_copy_conflict','precision_loss','display_rounding_boundary','possible_truncation'}
GAPS={'insufficient_data','incomparable','ambiguous_table','summary_year_not_covered','interaction_not_applied'}
FIXES={
 'pair':'先统一资产、字段定义、单位和时间基准；再核对数据源及模板格式化逻辑。流通量、总量与最大供应量分别显示，不能强制改成相同值。',
 'forecast':'按明确年份与增长情景生成表格和摘要，复用同一计算结果；复查基准年及索引偏移。仅修复表达一致性，不承诺预测准确。',
 'calculator':'核对实际输入事件、正反换算单位与汇率更新；使用十进制定点计算和足够显示精度。先查可复现的输入输出，不能由现象直接认定后端根因。',
 'claim':'依据字段原文和对应市场的已验证状态修正文案、模板变量或数据更新时间；营销按钮与可交易状态分开，不把单一接口失败视为全站下架。'}

def audit(inputs, *, at, max_age_hours=24):
    moment(at)
    for row in inputs['scope']:require_url(row['url'])
    if not math.isfinite(max_age_hours) or max_age_hours<=0:raise ValueError('invalid_freshness_window')
    findings={};results=[];gaps=list(inputs.get('gaps',[]));performed=set();calculators={}
    for check in inputs['checks']:
        kind=check['kind'];p=check['payload'];url=url_id(check['url'])
        try:
            if kind=='pair':r=check_pair(p['left'],p['right'],at=at,max_age_hours=max_age_hours)
            elif kind=='forecast':r=check_summary(p['table'],p['summary'],at=at,max_age_hours=max_age_hours)
            elif kind=='calculator':
                r=check_trial(p,at=at,max_age_hours=max_age_hours);calculators.setdefault((url,p.get('asset_id'),p.get('quote_unit')),[]).append(p)
            elif kind=='claim':r=check_claim(p,at=at,max_age_hours=max_age_hours)
            else:raise ValueError('unknown_check_kind')
        except (ValueError,KeyError,TypeError) as e:gaps.append({'url':url,'check_id':check['check_id'],'reason':'check_input_invalid','detail':str(e)});continue
        evidence={'check':check,'result':r};results.append(evidence);status=r['status']
        if status in GAPS:gaps.append({'url':url,'check_id':check['check_id'],'reason':status,'detail':r});continue
        performed.add((url,kind))
        if status not in CONFLICTS|CANDIDATES:continue
        dimension='summary-year-'+str(p['summary']['year']) if kind=='forecast' else check['check_id']
        identity='content-'+hashlib.sha256((site_host()+'|012|'+url+'|'+kind+'|'+dimension).encode()).hexdigest()[:24]
        if identity not in findings:findings[identity]={'issue_id':identity,'owner_skill':'012','url':url,'rule':status,'check_id':check['check_id'],'observed_at':at,
          'classification':'evidence_supported_conflict' if status in CONFLICTS else 'needs_review',
          'recommendation':FIXES[kind], 'retest':'同一URL、资产、情景、单位和显示精度重新取证；换算器测试1/10/1000及正反方向。保留修复前后证据，未复现不自动关闭。','evidence':[]}
        findings[identity]['evidence'].append(evidence)
        if status in CONFLICTS:findings[identity].update(classification='evidence_supported_conflict',rule=status)
    suites=[]
    for (url,asset,quote),rows in calculators.items():
        suite=check_suite(rows,at=at,max_age_hours=max_age_hours);suites.append({'url':url,'asset_id':asset,'quote_unit':quote,**suite})
        if not suite['coverage_complete']:
            performed.discard((url,'calculator'));gaps.append({'url':url,'reason':'calculator_matrix_incomplete','missing_cases':suite['missing_cases']})
    required={(url_id(row['url']),kind) for row in inputs['scope'] for kind in row['kinds']}
    for url,kind in sorted(required-performed):gaps.append({'url':url,'kind':kind,'reason':'scoped_check_not_performed'})
    return {'schema_version':1,'configured_site':site_host(),'skill':'012','at':at,'scope':inputs['scope'],'findings':list(findings.values()),'checks':results,'calculator_suites':suites,'gaps':gaps,
      'coverage':{'declared_checks':len(required),'performed_declared_checks':len(required&performed),'accepted_reviews':len(inputs['checks']),
                  'declared_checks_complete':bool(required) and required<=performed and not gaps,'full_site_proven':False,
                  'market_rate_accuracy_verified':False,'forecast_accuracy_verified':False},
      'limitations':['数值语义映射由具名证据复核提供，哈希只证明本地证据未改变。','页面自洽不证明行情真实或预测会实现；外部行情需同资产、市场、计价单位和时点。','未执行的检查保留缺口，历史问题不因本轮消失自动关闭。']}
