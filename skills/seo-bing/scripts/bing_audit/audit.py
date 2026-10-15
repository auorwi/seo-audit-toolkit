"""Join exact Bing URL observations while preserving historical, live-test and public clients."""
import hashlib,json
from .contracts import site_host,moment,fresh,url_id
OWNERS={'server_error':'003','http_4xx':'003','not_found':'003','access_limited':'003','fetch_failed':'003','robots_blocked':'003','important_url_robots_blocked':'003','noindex':'003','dns_error':'003','timeout':'003','redirect_301':'004','redirect_302':'004','meta_refresh':'004','canonical_mismatch':'004','discovered_not_crawled':'009','title_too_long':'007','title_missing':'007','description_missing':'007','multiple_h1':'006','h1_missing':'006','image_alt_missing':'013','sitemap_missing':'002','sitemap_error':'002','rich_result_error':'008'}
ADVICE={'title_too_long','multiple_h1','h1_missing','description_missing','title_missing','image_alt_missing','indexnow_not_submitted','sitemap_missing'}
BENIGN={'available','indexed','no_issues_detected','valid','submission_accepted','submitted','validation_passed'}
OWNERS.update(description_length_review='007',meta_language_missing='010')
ADVICE.update({'description_length_review','meta_language_missing'})
GUIDANCE={'003':'核对当前 HTTP、robots、索引指令与客户端差异；结合抓取时间查日志。通用 Failed 不等于 5xx，403 不证明全球用户均被阻断。','004':'核对 HTTP/meta/客户端跳转、canonical、语言与业务实体；保留原始参数及落点，不按 URL 相似认定等价。','005':'对照初始 HTML、稳定 DOM 和进入路径，保留内容加载缺口。','006':'按实际页面结构检查标题/语义；多个 H1 或工具建议不能单独证明索引阻断。','007':'对照实际 title/description、主题和搜索意图；长度告警需人工评审，不机械截断或直接当作未收录根因。','008':'核对当前结构化字段、可见事实和引擎模式；不补造价格或评分。','009':'结合重要页面的发现路径和抓取证据检查内链；已发现未抓取不单独证明抓取预算不足。','013':'检查实际图片用途和替代文本；装饰图和信息图分别处理。','002':'对照实际 Sitemap 与独立发布清单；后台未发现或提交成功都不证明文件完整性。','015':'保留平台原文与时间；核对当前站点与业务意图。IndexNow 未使用不是已证实的索引阻断；不自动提交、重扫或修改配置。'}

GUIDANCE['010']='核对 HTML lang、实际正文、hreflang 与语言路由；Meta Language 缺失建议不等于必须添加过时标记或页面被阻止索引。'

def latest(v):
 if not v:return []
 t=max(moment(x['captured_at']) for x in v);return [x for x in v if moment(x['captured_at'])==t]

def fetch_rule(i):
 c=i.get('http_status')
 if c in {301,302}:return 'redirect_'+str(c)
 if c and c>=500:return 'server_error'
 if c in {401,403,429}:return 'access_limited'
 if c in {404,410}:return 'not_found'
 if c and 400<=c<500:return 'http_4xx'
 if i.get('fetch_state')=='FAILED':return 'fetch_failed'
 if i.get('indexed') is False:return i.get('index_reason') or 'not_indexed'
 return None

def audit(inputs,*,at,max_age_hours=24):
 moment(at);fresh(at,at,max_age_hours);site=inputs['site'];scope=inputs['scope'];kind=inputs.get('run_kind','audit');gaps=list(inputs.get('gaps',[]));obs=[]
 for o in inputs['observations']:
  if o['site']!=site or not fresh(o['captured_at'],at,max_age_hours):gaps.append({'evidence_id':o['id'],'reason':'stale_future_or_site_mismatch'});continue
  obs.append(o)
  gaps.extend({'evidence_id':o['id'],'reason':g} for g in o['data'].get('gaps',[]))
 findings={};referrals={};indexed=[];live_tests=[];public=[];reports=[]
 def add(o,u,rule,mode):
  key=('bing-fixture-' if kind=='controlled_fixture' else 'bing-')+hashlib.sha256(json.dumps([site_host(),site,u,rule],ensure_ascii=False,separators=(',',':')).encode()).hexdigest()[:24];owner=OWNERS.get(rule,'015')
  classification='platform_recommendation' if rule in ADVICE else ('requires_review' if mode=='recommendation_observation' and rule not in OWNERS else mode)
  if rule in {'noindex','robots_blocked','redirect_301','redirect_302','canonical_mismatch'}:classification='requires_intent_review'
  if key not in findings:findings[key]={'issue_id':key,'owner_skill':'015','site':site,'url':u,'rule':rule,'classification':classification,'observation_modes':[],'index_blocking_proven':False,'underlying_defect_confirmed':False,'recommendation':GUIDANCE[owner],'retest':'同 URL 和客户端条件复核线上证据，再分别确认 Bing 索引快照与 Live URL；旧扫描/本轮缺席/当前200不自动关闭。','evidence':[]}
  f=findings[key]
  if mode not in f['observation_modes']:f['observation_modes'].append(mode);f['observation_modes'].sort()
  if len(f['observation_modes'])>1 and rule not in ADVICE and f['classification']!='requires_intent_review':f['classification']='mixed_platform_observation'
  if not any(e['evidence_id']==o['id'] for e in f['evidence']):f['evidence'].append({'evidence_id':o['id'],'captured_at':o['captured_at'],'mode':mode,'proof':o['proof'],'observation':o['data']})
  if owner!='015' and u:referrals[(owner,u,rule)]={'owner_skill':owner,'url':u,'reason':rule,'source_issue_id':key,'instruction':GUIDANCE[owner],'not_a_second_defect':True}
 for o in obs:
  d=o['data']
  if o['kind']=='live_http':public.append(o);continue
  reports.append({'evidence_id':o['id'],**d})
  if o['kind']=='bing_ui':
   report=d['report'];mode='live_test_observation' if report=='live_url' else ('historical_scan_observation' if report=='site_scan' else ('recommendation_observation' if report=='recommendations' else 'engine_observation'))
   for row in d.get('rows',[]):
    rule=row['reason_key']
    if rule not in BENIGN:add(o,row.get('url'),rule,mode)
   if d.get('inspection'):
    i=d['inspection'];wrapped={**o,'inspection':i}
    if report=='url_inspection':indexed.append(wrapped)
    else:live_tests.append(wrapped)
    rule=fetch_rule(i)
    if rule:add(o,i['url'],rule,mode)
  elif d['kind']=='url_info':
   rule=fetch_rule({'http_status':d['historical_http_status']})
   if rule:add(o,d['url'],rule,'engine_observation')
  elif d['kind']=='crawl_issues':
   for row in d['entries']:
    for reason in row['reasons']:add(o,row['url'],reason,'engine_observation')
 checks=[];paired=0
 def same(values,key):return len({json.dumps({k:v for k,v in x[key].items() if k!='field_bindings'},sort_keys=True) for x in values})<=1
 for s in scope:
  u=url_id(s['url']);dev=s['device'];eng=latest([o for o in indexed if o['inspection']['url']==u and o['inspection']['device']==dev]);now=latest([o for o in public if o['data']['url']==u and o['data']['device']==dev]);bt=latest([o for o in live_tests if o['inspection']['url']==u and o['inspection']['device']==dev])
  c={'url':u,'device':dev,'engine_evidence':[o['id'] for o in eng],'live_evidence':[o['id'] for o in now],'engine_live_evidence':[o['id'] for o in bt],'bing_fixed':False,'bingbot_live_verified':False,'current_content_verified':False,'client_comparability':'unproven','engine_live_http_status':bt[0]['inspection'].get('http_status') if len(bt)==1 else None}
  if not eng:status='index_snapshot_unavailable'
  elif not same(eng,'inspection'):status='conflicting_index_snapshots'
  elif not now:status='current_http_unavailable'
  elif not same(now,'data'):status='conflicting_public_observations'
  elif bt and not same(bt,'inspection'):status='conflicting_engine_live_observations'
  else:
   i=eng[0]['inspection'];p=now[0]['data'];code=p['status'];lc=bt[0]['inspection'].get('http_status') if bt else None;paired+=1
   c.update(indexed=i.get('indexed'),historical_http_status=i.get('http_status'),last_crawled=i.get('last_crawled'),public_http_status=code,public_final_url=p['final_url'])
   if p['final_url']!=u:status='different_landing_unverified'
   elif lc in {401,403,429} and code in {401,403,429}:status='engine_and_public_access_limited'
   elif code in {401,403,429}:status='current_access_limited'
   elif bt and (bt[0]['inspection'].get('fetch_state')=='FAILED' or (lc and lc>=400)) and 200<=code<300:status='engine_live_failure_public_http_success'
   elif i.get('http_status') and i['http_status']>=500 and code>=500:status='failure_reproduced_at_http_layer'
   elif i.get('http_status') in {404,410} and code in {404,410}:status='failure_reproduced_at_http_layer'
   elif i.get('http_status') and i['http_status']>=400 and 200<=code<300:status='historical_error_not_reproduced'
   elif i.get('fetch_state')=='FAILED' and 200<=code<300:status='historical_generic_failure_not_reproduced'
   else:status='observations_available_requires_specialist_review'
  c['comparison']=status;checks.append(c)
  if status not in {'historical_error_not_reproduced','historical_generic_failure_not_reproduced','failure_reproduced_at_http_layer','observations_available_requires_specialist_review'}:gaps.append({'url':u,'device':dev,'reason':status})
 return {'schema_version':1,'configured_site':site_host(),'skill':'015','run_kind':kind,'at':at,'site':site,'scope':scope,'observations':obs,'platform_reports':reports,'checks':checks,'findings':list(findings.values()),'referrals':list(referrals.values()),'gaps':gaps,'manifest_sha256':inputs.get('manifest_sha256'),
 'coverage':{'declared_variants':len(scope),'declared_urls':len({s['url'] for s in scope}),'index_snapshots':len({(o['inspection']['url'],o['inspection']['device']) for o in indexed}),'paired_variants':paired,'declared_checks_complete':bool(scope) and paired==len(scope) and not gaps,'affected_page_total':None,'all_reported_urls_verified':False,'full_site_proven':False},
 'limitations':['平台严重级别、建议、索引阻断和当前根因不是同一个概念。','Bing 索引、Live URL、旧 Site Scan 与普通 HTTP 是不同时间/客户端证据，200 或提交接受不证明已收录。','报表顶部数据及样例不是全量 URL 库存；计数单位分别保存。','当前客户端可比性未证实；专业转交不是已执行专项，不自动关闭历史问题。']}
