> Historical/opt-in BingX example. Apply to generic sites only after replacing URLs, selectors, and business assumptions with current evidence from the selected profile; never auto-import example evidence.

# 证据合同

所有示例均为合同示意，不能拿来充当真实后台数据。JSON UTF-8，manifest及每个proof最多8MiB；路径相对manifest，禁止绝对路径/越界symlink。大导出拆分保留批次；文件SHA256按原始字节计算。拒绝重复JSON键、NaN/Infinity和凭据字段。不同证据ID重复字节只保留一次；重复ID全部隔离。

## Manifest

```json
{
  "schema_version":1,
  "run_kind":"audit",
  "site":"https://bingx.com/",
  "scope":[{"url":"https://bingx.com/en","device":"UNKNOWN"}],
  "evidence":[{"id":"index-1","kind":"bing_ui","path":"inspection.json","sha256":"实际SHA256"}]
}
```

run_kind也可historical_replay/controlled_fixture，控制样例使用独立ID前缀。scope声明本轮逐页承诺，URL设备去重；保留query及其顺序，fragment不参与身份。site使用已核对的完整站点URL并带尾斜杠。本地scope默认只允许该前缀；若要检查平台列出的另一个主机/协议，请用相应已确认站点范围另运行，不偷偷扩展分母。UI行中真实出现的其他BingX主机可以保留，标记outside_site_prefix，不成为已检查URL；与BingX无关的主机拒绝。

## UI envelope

通用字段：kind=bing_ui、site、captured_at（时区ISO）、report、site_quote、reviewer、source、report_date（ISO日期或null）、filters对象、count_unit、rows数组。

source为`{url,path,sha256}`，url必须是实际bing.com/webmasters地址且siteUrl与选站匹配；path是实际文本/DOM摘录或导出。明确摘录边界，不称作完整导出。site_quote需实际包含选站主机。

report支持url_inspection、live_url、site_scan、recommendations、site_explorer、sitemaps、performance、submission、security、crawl_stats。

count_unit为pages/urls/issues/occurrences/items/sitemaps/not_applicable。reported_total可null；非空时total_quote必须是实际精确数值，允许逗号/空格分隔，不接受K/M。不能把字段错误、无效项目与页面数相加。

report_date非空需report_date_quote及格式：YYYY-MM-DD（默认）、D MMM YYYY（英文缩写含Sept）、D/M/YYYY、M/D/YYYY。日期格式按实际UI确定。每个文件最后抓取日期不是统一报告更新日期；不存在后者就填null并保留缺口。

每行：`{url?,url_quote?,device?,reason_key,reason_label,quote,severity?}`。reason_key是具名映射枚举（例如meta_refresh、title_too_long、description_missing、description_length_review、meta_language_missing、h1_missing、multiple_h1、image_alt_missing、sitemap_missing、indexnow_not_submitted）；未知键保留待审。label必须出现在quote中，quote必须出现在原文；URL还需作为完整token在原文与url_quote中出现，不能用前缀或另一个参数版本绑定。

### 单 URL 字段

```json
"inspection": {
  "url":"https://bingx.com/en/example",
  "url_quote":"https://bingx.com/en/example",
  "device":"UNKNOWN",
  "fields": {
    "indexed":{"value":false,"quote":"Discovered but not crawled"},
    "fetch_state":{"value":"FAILED","quote":"Failed"}
  }
}
```

仅用于report=url_inspection/live_url。fields支持indexed（bool，**live_url禁止**）、fetch_state（SUCCESS/FAILED/UNKNOWN）、http_status、last_crawled、index_reason、crawl_allowed。未取得字段保持null；FAILED不能推导状态码。http_status必须绑定同一个实际三位数字。last_crawled的value和原文quote均必须可解析为同一带时区时点；UI无时区时留在原文，省略这个字段，不添加假时区。index_reason为实际原因映射文本，不能被用作根因证明。

实时403/500、HTML与Schema问题放在live_url的inspection/rows，与索引状态分开。Live URL可用行使用available，不产生“已索引”结论。UI富媒体错误用rich_result_error，转008；原文中的项目数和字段数分别记录。

### 既有 Site Scan

必须包含scan：`{id,completed_date,quote,date_format}`，例如日期格式D MMM YYYY；或者`{id,completed_at,quote}`且时间带时区。两种日期形式不能同时填。扫描时间绑定原文，旧扫描（超过7日）提示历史证据，不能把captured_at当成扫描完成时间。尚未完成或无法读取时间的扫描保留原始记录并说明未支持，不能伪造完成结果。

## API envelope

```json
{"kind":"bing_api","site":"https://bingx.com/","captured_at":"2026-09-17T02:00:00Z","http_status":200,"method":"GetUrlInfo","request":{"siteUrl":"https://bingx.com/","url":"https://bingx.com/en"},"response":{"d":{"Url":"https://bingx.com/en","HttpStatus":200,"IsPage":true}}}
```

仅为示例。保存实际JSON/HTTP返回，禁止把UI人工映射包装成API响应。HTTP错误、Fault体、站点/URL不一致隔离；登录/限流失败不是网站故障。不要保存带API Key的请求URL或Authorization/Cookie。键值和文本凭据检测用于防止误纳入报告，不是敏感信息识别的完整替代。

Microsoft `/Date(ms±offset)/` 的毫秒是UTC时点，不再次加减后缀偏移；日期缺失保持未知。GetUrlInfo的IsPage不映射为indexed；HttpStatus=0为未知。CrawlIssues允许组合位，未知位单列缺口。GetFeeds的UrlCount不当作索引量。GetQueryStats/GetPageStats分别保留AvgClickPosition与AvgImpressionPosition，后者的Query字段作为页面URL；未知字段留在原始proof。当前未实现自动搜索表现窗口比较，不能声称已计算周环比。

## 当前HTTP

`{kind:"live_http",site,captured_at,url,final_url,device,method:"GET",status,source_description}`。附加真实headers/redirect_chain、user_agent、body_path/body_sha256及truncated状态，保留实际来源；脚本关联精简视图只比较状态和落点，完整正文/渲染/内容判断由专业复核另列。

普通请求device=UNKNOWN时，报告不会将它包装成Bingbot相同设备/网络。HEAD不作为页面观察。最终落点变化明确保留，不能拿目标200证明原始路径页面已修复。HTTP200同样不证明内容正常或已索引。

## 历史与输出

同站点/完整URL/规则维持ID，不因来源从旧扫描变成实时测试而新增另一根因工单。各来源模式和时间保留。状态默认open，本轮缺席不自动关闭；17号技能负责修复验收。反复相同输入和at回放不增加sighting；新采集/新审查时点是新的观察。

平台条目、引擎实时结果、普通HTTP差异与专业根因不能混在一个“已确认故障总量”中。各报告原始筛选、日期和单位在report.json保存；declared_checks_complete是关联范围结果，不是全站或全部专项通过。
