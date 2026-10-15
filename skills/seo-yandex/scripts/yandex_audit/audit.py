"""Evidence comparisons and stable observations; no remediation submissions."""
import sys as _site_sys
from pathlib import Path as _SitePath
_site_dependency=_SitePath(__file__).resolve().parents[3]/'seo-crawlability/scripts'
if str(_site_dependency) not in _site_sys.path:_site_sys.path.insert(0,str(_site_dependency))
from crawlability.site import site_host
import hashlib,json
from . import contracts as c
RULES={
 'ROUTE_ENTITY_MISMATCH':('004','复核路由对应的业务实体与实际主体；禁止静默回退到BTC，仅改TDK不足。',True),
 'ERROR_PAGE_CONTENT':('004','核验错误页与HTTP状态；无等价内容时返回真实404/410，有已确认等价目标才精确重定向。',True),
 'EMPTY_METADATA':('007','先确认该URL是否有效内容页；若为错误页，优先修复状态与路由再决定元信息。',True),
 'HTTP_ERROR':('003','核对原 URL 的状态链、CDN/WAF 与真实爬虫日志；先保留历史失败时间。',False),
 'HOST_ERROR':('003','核验 DNS、TLS、响应和爬虫访问日志，普通请求不能证明机器人恢复。',False),
 'DNS_ERROR':('003','检查解析和实际访问；区分平台历史 DNS 失败与本次网络环境。',False),
 'ROBOTS_HOST_ERROR':('003','对照 robots 对 Yandex 的匹配规则与业务索引意图。',True),
 'ROBOTS_URL_ERROR':('003','对照 robots 对此精确 URL 的匹配规则。',True),
 'NO_INDEX':('003','核验初始 HTML、响应头与渲染索引指令；确认业务意图后再改。',True),
 'CLEAN_PARAMS':('003','核验 Clean-param 的路径、参数值及业务含义；不要删除影响实体或语言的参数。',True),
 'NOT_CANONICAL':('004','核验声明与引擎选择的目标，比较实体、语言、响应和索引意图。',True),
 'NOT_MAIN_MIRROR':('004','核验主镜像与协议/主机关系，不将各 host 的统计直接合并。',True),
 'REDIRECT_NOTSEARCHABLE':('004','逐跳检查目标状态与业务等价性；旧 URL 重定向可能符合预期。',True),
 'DUPLICATE':('004','比较原页与引擎关联页的实体、语言、参数及规范关系。',True),
 'LOW_QUALITY':('012','复核可见正文、模板价值和实体一致性；平台质量判断不等于应删除页面。',True),
 'PARSER_ERROR':('005','对照初始响应与 JS 渲染内容，检查内容是否真正到达机器人。',False),
 'NOTHING_FOUND':('001','核对发现入口、内链和 Sitemap；未发现不等于页面故障。',True),
 'DUPLICATE_TITLE':('007','按重复组核验同语言、分页和实体，保留实际标题后制定模板规则。',True),
 'DUPLICATE_DESCRIPTION':('007','按重复组复核描述、页面意图与实体差异，避免机械添加词语。',True),
 'GET_PARAMETER_DUPLICATES':('004','抽查原参数页与无参数页；确认等价后选择规范策略。',True),
 'ERRORS_IN_SITEMAPS':('002','读取对应 Sitemap 和原始条目，复核文件错误与线上 URL。',False),
 'NO_SITEMAPS':('002','检查 robots 声明、平台读取状态与真实文件，不能凭平台提示猜遗漏 URL。',False),
 'NO_METRIKA_COUNTER':('016','依据统计需求确认 Metrica 的配置，不把统计工具缺失认定为索引阻断。',True),
 'METRIKA_NOT_LINKED':('016','核对统计账号关联需求与权限，保留为平台建议。',True),
 'SUBDOMAINS_IN_SEARCH':('004','取得具体子域后确认索引意图，不对未检查子域批量封禁。',True),
 'FAVICON_RECOMMENDATION':('013','核验已声明 favicon 的实际格式与像素，并结合平台展示要求。',True),
 'TITLE_COUNTRY_MISSING':('007','保留平台与当前页面标题原文，核验国家路由与实际标题实体。',True),
}
def packed(v):return json.dumps(v,sort_keys=True,ensure_ascii=False,separators=(',',':'))
def key(row):return (row.get('url'),row.get('device','UNKNOWN'),row.get('js','UNKNOWN'))
def latest(items):
 if not items:return [],False
 newest=max(c.moment(e['captured_at']) for e,r in items);selected=[(e,r) for e,r in items if c.moment(e['captured_at'])==newest]
 # Text/bindings may differ while the actual comparison fields agree.
 sig={packed({k:r.get(k) for k in ['searchable','http_status','final_url','reason','target_url']}) for e,r in selected}
 return selected,len(sig)>1

def audit(inputs,*,at,max_age_hours=24):
 c.moment(at);host=inputs['host_id'];c.host_url(host);gaps=list(inputs['gaps']);evidence=[]
 for e in inputs['evidence']:
  if e['host_id']!=host or not c.fresh(e['captured_at'],at,max_age_hours):gaps.append({'evidence':e['id'],'reason':'host_mismatch_or_stale'});continue
  evidence.append(e)
  gaps.extend({'evidence':e['id'],'reason':g} for g in e.get('gaps',[]))
 findings={};allrows=[]
 for e in evidence:
  for row in e['rows']:
   allrows.append((e,row))
   if e['mode']=='ordinary_http':continue
   if row.get('state')=='ABSENT':continue
   if row.get('state')=='UNDEFINED':gaps.append({'evidence':e['id'],'reason':'diagnostic_state_undefined'});continue
   reason=row.get('reason')
   if not reason:continue
   group=row.get('group_id');identity=[site_host(),host,row.get('url'),reason,group];prefix='yandex-fixture-' if inputs['run_kind']=='controlled_fixture' else 'yandex-';iid=prefix+hashlib.sha256(packed(identity).encode()).hexdigest()[:24]
   owner,advice,intent=RULES.get(reason,('016','保留平台原始分类，补充官方定义与逐 URL 核验后再定修复。',True))
   classification='reviewed_public_observation' if e['mode']=='public_dom' else 'platform_recommendation' if row.get('severity')=='RECOMMENDATION' else 'platform_observation' if reason in RULES else 'unmapped_platform_observation'
   f=findings.setdefault(iid,{'issue_id':iid,'host_id':host,'url':row.get('url'),'rule':reason,'group_id':group,'owner_skill':owner,'classification':classification,'verified_site_defect':False,'confirmed_index_block':False,'intent_review_required':intent,'recommendation':advice,'retest':'以同 URL/设备/JS 条件复测；保留历史数据库状态，等待引擎证据后才能确认收录恢复。','evidence':[]})
   ref={'id':e['id'],'captured_at':e['captured_at'],'mode':e['mode'],'report':e['report'],'source':e['source'],'row':row}
   if ref not in f['evidence']:f['evidence'].append(ref)
 checks=[];paired=0;snapshots=0
 for s in inputs['scope']:
  matches=[(e,r) for e,r in allrows if key(r)==key(s)]
  db,db_conflict=latest([(e,r) for e,r in matches if e['mode']=='engine_snapshot' and e['report'] in {'database','important-urls'} and type(r.get('searchable')) is bool])
  live,live_conflict=latest([(e,r) for e,r in matches if e['mode']=='engine_live'])
  http,http_conflict=latest([(e,r) for e,r in matches if e['mode']=='ordinary_http'])
  check={**s,'searchable':db[0][1].get('searchable') if db and not db_conflict else None,'engine_evidence':[e['id'] for e,r in db],'engine_live_evidence':[e['id'] for e,r in live],'http_evidence':[e['id'] for e,r in http],'engine_recovery_confirmed':False,'content_verified':False,'client_comparability':'unproven','public_dom_evidence':sorted({e['id'] for e,r in allrows if e['mode']=='public_dom' and r.get('url')==s['url'] and r.get('device')==s['device']})}
  comp='observations_available_requires_specialist_review'
  if db_conflict:comp='conflicting_index_snapshots'
  elif not db:comp='index_snapshot_unavailable'
  elif http_conflict:comp='conflicting_http_observations'
  elif not http:comp='current_http_unavailable'
  elif live_conflict:comp='conflicting_engine_live_observations'
  else:
   paired+=1;hr=http[0][1];dr=db[0][1];lr=live[0][1] if live else {};code=hr.get('http_status');lcode=lr.get('http_status');dcode=dr.get('http_status')
   if hr['final_url']!=s['url']:comp='different_landing_unverified'
   elif lcode is not None and lcode>=400 and code>=400:comp='engine_and_public_access_limited'
   elif lcode is not None and lcode>=400 and code==200:comp='engine_live_failed_public_http_success'
   elif code>=400:comp='http_failure_reproduced' if dcode and dcode>=400 else 'current_access_limited'
   elif dcode and dcode>=400 and code==200:comp='historical_http_failure_not_reproduced'
  if db and not db_conflict:snapshots+=1
  check['comparison']=comp;checks.append(check)
  if comp in {'conflicting_index_snapshots','index_snapshot_unavailable','conflicting_http_observations','current_http_unavailable','conflicting_engine_live_observations','different_landing_unverified','current_access_limited','engine_and_public_access_limited','engine_live_failed_public_http_success'}:gaps.append({'url':s['url'],'device':s['device'],'js':s['js'],'reason':comp})
 selected={s['url'] for s in inputs['scope']};observed={r.get('url') for e,r in allrows if r.get('url')};fs=sorted(findings.values(),key=lambda f:f['issue_id'])
 coverage={'declared_urls':len(selected),'declared_variants':len(inputs['scope']),'index_snapshots':snapshots,'paired_variants':paired,'unselected_observed_urls':len(observed-selected),'declared_checks_complete':paired==len(inputs['scope']) and not gaps,'all_site_verified':False}
 return {'configured_site':site_host(),'skill_id':'016','version':'1.0.0','host_id':host,'at':at,'run_kind':inputs['run_kind'],'findings':fs,'checks':checks,'coverage':coverage,'gaps':gaps,'platform_reports':evidence,'referrals':[{'issue_id':f['issue_id'],'url':f['url'],'owner_skill':f['owner_skill'],'status':'pending_specialist_review'} for f in fs if f['owner_skill']!='016'],'limitations':['抓取成功、页面在搜索中、实时可访问是不同状态。','平台建议和质量分类尚不构成网站根因或删除页面的依据。','只对声明样本配对；样例数、重复组数、URL数和 Sitemap 链接数不相加。','UNKNOWN 环境不代表环境相同；普通请求不是 Yandexbot。','未执行的专业转交保持待核验；问题缺席不自动关闭历史。']}
