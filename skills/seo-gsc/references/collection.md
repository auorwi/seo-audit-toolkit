# 采集流程与官方能力

## 浏览器主路径

使用本环境已授权浏览器工具定位 Search Console。先核对 property（不要依赖历史 tab ID）；保留当前完整地址、可见文本与采集 UTC 时间。按报告打开页面时先更新 UI 状态，避免沿用上个页面的节点标识。

推荐周巡查范围：页面索引原因变化、抓取统计/robots 和主机异常、提交的 Sitemap、实际出现的结构化数据报告、移动/桌面 CWV、视频索引、HTTPS、人工措施与安全；再按优先 URL 做索引检查。没有可见报告或权限时标为 unavailable，不补造零值。

每个报告记下筛选条件（主机/页面路径、设备、日期、搜索类型等）、原始计数单位、数据更新时间、用户可见的状态/原因标签。计数是 items 时不能改成 pages；同一 URL 可有多个错误，同一个 CWV URL 可落在多个问题组。没有清楚单位则先保留证据、列缺口，不输出虚假总数。

采样基于用户已确认的 URL 清单；平台新样例先追加来源，不静默改资产清单。优先新增问题、变差问题、重要页面和待修复旧问题；同模板保留固定复测样本与轮换样本，报告实际数量。网页索引报告的样例集合不能视为全部问题 URL。[Google 页面索引说明](https://support.google.com/webmasters/answer/7440203?hl=en)

逐 URL：复制完整 URL，读取索引版 Inspection，分别记录最后抓取时间、抓取代理、抓取结果、允许索引情况、用户声明/Google 选择的 canonical。根据可见字段摘录，不将 Overview 的总量当成此 URL 结果。需要实时 Google 检测时可执行只读的 Test live URL，明确为独立观察；不要顺手 Request indexing 或 Validate fix。[URL Inspection 工具说明](https://support.google.com/webmasters/answer/9012289?hl=en)

当前页面用实际 GET 或浏览器响应记录 requested URL、final URL、状态、设备、采集时间和环境。仅拿到普通诊断 HTTP 请求时设备写 UNKNOWN，不伪装为 MOBILE 或 Googlebot。浏览器渲染检查复用 005/相应专业技能，并保留实际响应来源。被登录/地域/安全挑战限制时写明限制，不绕过。

读取中文等界面时，保留原始标签与具名字段映射。UI 的稳定 `reason_key` 应根据语义映射到 routing.md；未识别原因用明确新键并保留标签，不靠机器猜测翻译来断言根因。日期缺失可设 null；索引报告统计日期和 URL 最后抓取时间不要互换。

## 只读 API 备选

前提：已有授权的连接器或 OAuth 凭据。优先 `https://www.googleapis.com/auth/webmasters.readonly`；不把 token/cookie 写进 evidence、命令日志或交付包。不编造可用权限或自动探查凭据。

| 能力 | 官方端点 | 本技能的限制 |
|---|---|---|
| 索引检查 | POST `https://searchconsole.googleapis.com/v1/urlInspection/index:inspect`，body 含 `inspectionUrl`、`siteUrl` | 仅索引版；不支持 API Live test |
| 搜索表现 | POST `https://www.googleapis.com/webmasters/v3/sites/{encodedSiteUrl}/searchAnalytics/query` | 原始请求一并保存；API 请求 body 不含路径参数 `siteUrl`，本地 envelope.request 则记录它 |
| 已提交 Sitemap | GET `https://www.googleapis.com/webmasters/v3/sites/{encodedSiteUrl}/sitemaps` | 是提交/索引文件引用范围，不是全站文件发现 |

[URL Inspection endpoint](https://developers.google.com/webmaster-tools/v1/urlInspection.index/inspect) · [结果字段](https://developers.google.com/webmaster-tools/v1/urlInspection.index/UrlInspectionResult)

Search Analytics 按 Pacific 日界请求；先确定完整数据的最新日期，再选两个等长窗口（例如连续两周），保存 dimensions、filters、type、aggregation、dataState、rowLimit、startRow。分页不会保证完整库存；停止于空页/短页/预算限制并保留截断原因。现有比较器支持从 startRow=0 开始的一份可比响应；需要合并多页时先解决重复、范围和排序不稳定问题，不能把单页结果改名为全量。日期/小时维度需要额外对齐，不在当前比较器自动支持范围内。

[Search Analytics 官方合同](https://developers.google.com/webmaster-tools/v1/searchanalytics/query)

URL Inspection 当前官方每站额度为 2,000 次/日、600 次/分钟；运行预算设得更低，优先复用本轮同一证据，配额耗尽写入缺口、保存进度，不连续重试。执行前如需依赖精确限额，重新核对官方配额。不能声称知道账户剩余额度。[官方限制](https://developers.google.com/webmaster-tools/limits)

Sitemap `contents.indexed` 已弃用；保存原始数据但不用于计算索引覆盖率。`mobileUsabilityResult` 已弃用，也不是 CWV。[Sitemap 字段](https://developers.google.com/webmaster-tools/v1/sitemaps)

API 成功不等于所有 UI 报告都已读取；页面索引汇总、人工措施、安全等由实际可用的 UI/导出补足。本技能不虚构这些报告的 REST 接口。
