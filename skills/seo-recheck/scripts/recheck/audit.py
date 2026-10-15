"""Conservative repair verdicts for explicitly enumerated acceptance cases."""
import sys as _site_sys
from pathlib import Path as _SitePath
_site_dependency=_SitePath(__file__).resolve().parents[3]/'seo-crawlability/scripts'
if str(_site_dependency) not in _site_sys.path:_site_sys.path.insert(0,str(_site_dependency))
from crawlability.site import site_host
from collections import defaultdict
import json
from .evidence import moment
from .checks import evaluate

def case_result(case,deployment_at):
 baseline=case.get('baseline');before=evaluate(baseline['values'],case['predicate'],complete_fields=baseline['complete_fields']) if baseline else None
 gaps=list(case['gaps']);attempts=[];times=defaultdict(set)
 for cap in case['after']:
  reason=None
  if baseline and moment(cap['captured_at'])<=moment(baseline['captured_at']):reason='not_newer_than_baseline'
  if deployment_at and moment(cap['captured_at'])<moment(deployment_at):reason='before_deployment'
  if reason:gaps.append(reason);continue
  verdict=evaluate(cap['values'],case['predicate'],complete_fields=cap['complete_fields']);attempt={**verdict,'captured_at':cap['captured_at'],'source':cap['source'],'navigation_at':cap.get('navigation_at'),'kind':cap['kind']};attempts.append(attempt);times[moment(cap['captured_at'])].add(json.dumps([verdict['status'],verdict['observed']],sort_keys=True,ensure_ascii=False))
 conflict=any(len(v)>1 for v in times.values());passed=sum(v['status']=='passed' for v in attempts);failed=sum(v['status']=='failed' for v in attempts)
 current='inconclusive'
 if conflict:gaps.append('same_time_conflicting_results')
 elif failed:current='failed'
 elif passed>=case['repetitions'] and len(times)>=case['repetitions'] and all(v['status']=='passed' for v in attempts):current='passed'
 elif passed:current='partial_pass'
 if len(times)<case['repetitions']:gaps.append('insufficient_independent_repetitions')
 status=current
 if current=='passed':
  if case['role']=='symptom' and (not before or before['status']!='failed'):gaps.append('original_failure_not_reproduced');status='inconclusive'
  if not deployment_at:gaps.append('deployment_time_unavailable');status='inconclusive'
  if case['device']=='UNKNOWN' or case['js']=='UNKNOWN':gaps.append('unknown_environment');status='inconclusive'
  if any(a['kind']=='dom' and (not a['navigation_at'] or (deployment_at and moment(a['navigation_at'])<moment(deployment_at)) or (baseline and moment(a['navigation_at'])<=moment(baseline['captured_at']))) for a in attempts):gaps.append('fresh_navigation_unverified');status='inconclusive'
  if case['gaps'] and status=='passed':status='partial_pass'
 if baseline and deployment_at and moment(baseline['captured_at'])>=moment(deployment_at):gaps.append('baseline_not_before_deployment');status='failed' if current=='failed' else 'inconclusive'
 return {'case_id':case['id'],'role':case['role'],'url':case['url'],'device':case['device'],'js':case['js'],'entry':case['entry'],'predicate':case['predicate'],'required_repetitions':case['repetitions'],'current_status':current,'status':status,'baseline':{'source':baseline['source'],'captured_at':baseline['captured_at'],'result':before} if baseline else None,'attempts':attempts,'gaps':sorted(set(gaps))}

def audit(plan,*,at):
 moment(at);rechecks=[]
 for issue in plan['issues']:
  cases=[case_result(c,issue['deployment_at']) for c in issue['cases']];states=[c['status'] for c in cases];gaps=[]
  if 'failed' in states:status='failed'
  elif all(s=='passed' for s in states):status='passed'
  elif any(s in {'passed','partial_pass'} for s in states):status='partial_pass'
  else:status='inconclusive'
  if status=='passed' and issue['scope_type']!='url':status='partial_pass';gaps.append('original_scope_not_fully_verified')
  engines=[]
  for ref in issue.get('engine_reports',[]):
   report=ref['report'];url=issue['original'].get('url');matching=[c for c in report.get('checks',[]) if c.get('url')==url]
   backend_modes={'engine_snapshot','engine_live','engine_observation','recommendation_observation','historical_scan_observation','live_test_observation'}
   reported=any(f.get('issue_id')==issue['issue_id'] and f.get('classification')!='reviewed_public_observation' and not any(e.get('mode')=='public_dom' for e in f.get('evidence',[])) and any(e.get('mode') in backend_modes for e in f.get('evidence',[])) for f in report.get('findings',[]))
   estate='issue_still_reported' if reported else 'snapshot_available_clearance_unverified' if matching else 'exact_url_not_checked'
   engines.append({'platform':ref['platform'],'source':ref['source'],'captured_report_at':report['at'],'status':estate,'checks':matching,'post_deployment_crawl_verified':False,'note':'报告采集时点不等于爬虫/数据库更新时间；环境保持原值，不能据此证明问题已清除。'})
  rechecks.append({'engine_observations':engines,'issue_id':issue['issue_id'],'rule':issue['original'].get('rule'),'owner_skill':issue['original'].get('owner_skill'),'original_url':issue['original'].get('url'),'source_report':issue['source_report'],'scope_type':issue['scope_type'],'deployment_at':issue['deployment_at'],'status':status,'repair_verified':status=='passed','cases':cases,'gaps':gaps,'engine_state':'platform_observations_available_clearance_unverified' if engines else 'requires_platform_recheck','engine_recovery_confirmed':False,'source_ledger_modified':False})
 complete=len(rechecks)==plan['declared_issues'] and not plan['gaps'] and all(r['status'] in {'passed','failed'} and all(not c['gaps'] for c in r['cases']) for r in rechecks)
 return {'configured_site':site_host(),'skill_id':'017','version':'1.0.0','at':at,'run_kind':plan['run_kind'],'rechecks':rechecks,'gaps':plan['gaps'],'coverage':{'declared_issues':plan['declared_issues'],'loaded_issues':len(rechecks),'cases':sum(len(r['cases']) for r in rechecks),'complete':complete,'all_site_verified':False},'limitations':['仅按声明验收用例判断；默认不更改原专项问题台账。','部署时间未知时，当前检查通过也不证明修复已部署。','模板/未知范围的抽样通过不关闭整个范围。','引擎恢复必须另行执行014–016；线上通过不清除历史平台状态。']}
