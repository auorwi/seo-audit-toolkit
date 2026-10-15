> Historical/opt-in BingX example. Apply to generic sites only after replacing URLs, selectors, and business assumptions with current evidence from the selected profile; never auto-import example evidence.

# 证据输入与持久状态

## Manifest

UTF-8 JSON，最大 8 MiB。所有 proof 路径相对 manifest 所在目录；禁止逃逸和外部符号链接。证据文件最大 8 MiB，大导出拆分并保留批次，不静默截断。SHA256 对实际文件字节计算。

```json
{
  "schema_version": 1,
  "run_kind": "audit",
  "property": "sc-domain:bingx.com",
  "scope": [{"url": "https://bingx.com/en/price/ripple", "device": "MOBILE"}],
  "evidence": [
    {"id": "inspection-001", "kind": "inspection_api", "path": "inspection-001.json", "sha256": "实际文件的64位SHA256"},
    {"id": "current-001", "kind": "live_http", "path": "current-001.json", "sha256": "实际文件的64位SHA256"}
  ],
  "comparisons": []
}
```

`run_kind` 为 audit（默认）、historical_replay 或 controlled_fixture。历史重放和控制样例在人类报告中醒目标识；控制样例问题 ID 使用独立前缀，避免与真实观察混淆。所有演练应使用独立 state 目录。

`scope` 是本轮承诺逐页核验范围；平台读取到的其他 URL 保留为观察，但不会偷偷扩大已检查分母。设备仅 MOBILE、DESKTOP、UNKNOWN；普通网络诊断写 UNKNOWN。相同完整 URL 和设备才配对；业务查询参数不删除、不排序，fragment 不参与页面身份。重复 id 的全部证据隔离，重复字节只保留一次有效观察。

`comparisons` 可填 `[{"before":"analytics-prior","after":"analytics-current"}]`，指向两份 analytics_api 证据。返回对照和未匹配行，不补零；只比较当前导入的可见数据，不归因为某项 SEO 故障。

## API envelope

`inspection_api`、`analytics_api`、`sitemaps_api` 通用字段：

```json
{
  "kind": "inspection_api",
  "property": "sc-domain:bingx.com",
  "captured_at": "2026-09-17T00:00:00Z",
  "http_status": 200,
  "request": {"siteUrl":"sc-domain:bingx.com","inspectionUrl":"https://bingx.com/en/price/ripple"},
  "response": {"inspectionResult": {"indexStatusResult": {"verdict":"PASS","pageFetchState":"SUCCESSFUL","crawledAs":"MOBILE","lastCrawlTime":"2026-09-15T01:00:00Z"}}}
}
```

上例仅展示合同，不能用作真实巡查证据。`request` 保存实际调用参数及 property，`response` 保存实际完整响应，采集时间带时区。API 错误、非 200、请求 property 不符、未来最后抓取时间等隔离为缺口。历史抓取时间老于采集时间本身不是输入过期；新取回的索引快照可以描述旧抓取。

analytics 的 request 另含 startDate/endDate/dimensions 等；sitemaps 的 response 使用官方 `sitemap` 数组。解析后的字段缺失保持未知，原始多余字段仍在 proof 文件中。当前本地数值实现拒绝 clicks/impressions 超过 2^53−1 的输入以避免报告互操作精度问题；这是本地支持边界，不是 Google 的官方流量上限。

## UI 采集 / 导出

`kind=gsc_ui`，通用 property、captured_at。`source` 是实际读取的原文/导出文本 proof，UTF-8。可另外保留截图与工具日志作人工核验依据；这版解析器不自动 OCR 图片。CSV 导出可作为原文来源，由 Codex 按实际列名提取映射，保留原文件；不能只留下模型摘要。

```json
{
  "kind":"gsc_ui",
  "property":"sc-domain:bingx.com",
  "captured_at":"2026-09-17T00:00:00Z",
  "report":"page_indexing",
  "report_date":"2026-09-04",
  "report_date_quote":"2026-09-04",
  "property_quote":"sc-domain:bingx.com",
  "filters":{"pages":"all known pages"},
  "count_unit":"pages",
  "reported_total":44682,
  "total_quote":"44,682",
  "reviewer":"实际读取者姓名或代理标识",
  "source":{"url":"https://search.google.com/search-console/index?resource_id=sc-domain%3Abingx.com","path":"raw-ui.txt","sha256":"实际SHA256"},
  "rows":[{"url":"https://bingx.com/en/example","url_quote":"https://bingx.com/en/example","device":"UNKNOWN","reason_key":"server_error","reason_label":"Server error (5xx)","quote":"Server error (5xx)"}]
}
```

这是合同示例，并非真实后台记录。所有 quote 必须能在原文件中找到，允许折叠空白；URL 还必须作为完整 URL 出现在原文中，不能用 /en 去匹配 /english，也不能拿参数变体证明无参数 URL。canonical、Sitemap 和 referring URL 的每个值同样逐项绑定；引用尽量取完整纯 URL，保留编码和业务参数，避免把句末标点混入引用。不能为了让解析器通过而修改原始文本。`report_date` 填标准 ISO 值，`report_date_quote` 必须保留原始日期。`report_date_format` 默认 YYYY-MM-DD，也支持 M/D/YY、D/M/YY、M/D/YYYY、D/M/YYYY、YYYY/M/D、MMM D, YYYY（英文月份）和 YYYY年M月D日。带斜线日期必须根据实际界面格式明确指定顺序，不能按当前机器地区猜测；两位年份在本版本解释为 2000–2099。其他日期格式先填 null 并保留原文及缺口，不伪造 ISO 摘录。

`count_unit`：pages/items/groups/sitemaps/issues/not_applicable。reported_total 可 null（未读取），不能将空值写 0；非空必须提供仅包含实际数字及逗号/空格分隔符的 total_quote。计数是当前筛选和问题分组的口径；多个错误行可能重叠，不相加。

`report`：page_indexing、sitemaps、rich_results、cwv、video_indexing、https、manual_actions、security、performance、url_inspection、live_test。未知报告先保留原始材料并报告未支持，不强行套用另一报告。

### UI 单 URL 索引检查

当 `report=url_inspection` 时，加：

```json
"inspection": {
  "url":"https://bingx.com/en/example",
  "url_quote":"https://bingx.com/en/example",
  "fields": {
    "verdict":{"value":"FAIL","quote":"URL is not on Google"},
    "pageFetchState":{"value":"SERVER_ERROR","quote":"Server error (5xx)"},
    "crawledAs":{"value":"MOBILE","quote":"Googlebot smartphone"},
    "lastCrawlTime":{"value":"2026-09-04T15:01:31Z","quote":"Sep 4, 2026, 11:01:31 PM"}
  }
}
```

转换最后抓取时间前核对 UI 时区；不能因为用户本地在新加坡就假定 GSC 所显示的一定为 UTC+8。缺失时区保留原文、不要填猜测的 lastCrawlTime。value 为官方字段语义，quote 为所见文本，reviewer 负责核实映射，解析器仅检查引用、类型和时间合理性。允许字段为 verdict、robotsTxtState、indexingState、pageFetchState、crawledAs、coverageState、lastCrawlTime、googleCanonical、userCanonical、sitemap、referringUrls；列表项要逐一核对实际来源。

Inspection 没有汇总 report_date 可以为 null；其最后抓取时间单独记录。report=live_test 不允许提供这组索引快照字段；实时结果保存在带 quote 的 rows 中，只作为实时证据，不生成已收录结论。

实时测试或单 URL 索引检查中的无效富媒体项目使用 `reason_key=rich_result_error`，每个具体错误原文各存一行，`count_unit=items`。审查器合并为同 URL 的富媒体平台观察并转交 008；不把三条字段错误算成三个受影响页面。URL 可用与富媒体错误可同时存在；`available` 行不会抹去错误。未知实时错误保留为待核验观察，不能静默忽略。平台索引和实时测试归入同一稳定问题时，`observation_modes` 保留不同模式。

## 当前 HTTP 观察

```json
{
  "kind":"live_http","property":"sc-domain:bingx.com",
  "captured_at":"2026-09-17T00:00:00Z",
  "url":"https://bingx.com/en/example","final_url":"https://bingx.com/en/example",
  "method":"GET","status":200,"device":"MOBILE",
  "source_description":"实际浏览器响应；记录所用代理、设备、视口和环境来源"
}
```

这是精简关联视图，附加原始请求链/采集文件引用、状态来源、截图和原始 HTML hash，保存它来自何处；不能从“页面看起来正常”补造 HTTP 200。HEAD 不作本版本的页面观察输入。当前工具只比较状态与目标，不读取正文判断内容健康；专业结论留在对应专项报告。普通 HTTP 无设备证据就写 UNKNOWN，即使因此产生设备无法配对的缺口。

## 状态与报告

SQLite 问题主键包含 property、报告、URL、规则。API 与 UI 对应同一 `server_error` 等键时合并；新的不同原因保留独立记录。没有源 URL 的报告级观察不会虚构受影响 URL。重复运行相同输入和 at 幂等，新时点是新观察；不同 run 的次数不等于独立用户或受影响页面数。

`declared_checks_complete` 仅表示声明 URL 组合有可比较的引擎索引与 HTTP 观察且没有已知采集缺口，不等于所有 SEO 专项已通过。实际 defect、修复与引擎更新状态仍需额外证据。全站覆盖、全部报告 URL 已核验等字段固定不宣称为真。
