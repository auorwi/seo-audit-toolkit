> Historical/opt-in BingX example. Apply to generic sites only after replacing URLs, selectors, and business assumptions with current evidence from the selected profile; never auto-import example evidence.

# 009 证据合同

manifest顶层 `schema_version:1`，数组captures/http_records/assets/pagination/language_expectations，seeds对象。后四项可空；审查合并后必须有显式assets和seeds。文件proof为 `{path,bytes,sha256}`，路径在manifest目录内；原始文件SHA与字节数需一致，每份最多8,000,000字节。哈希证明保存字节一致，不独立证明所有来源描述正确。

## 资产与入口

assets是URL字符串或含url的元数据对象；同URL元数据冲突会拒绝。种子例：`{"home":["https://bingx.com/en/"],"category":["https://bingx.com/en/price"],"business":["https://bingx.com/en/download"]}`。首页未采集时仍可声明，但最短路径会明确缺口；不要伪造主页入链。

## 页面快照

capture：url、snapshot_id、document_sha256、captured_at、source、representation（initial_html/rendered_html）、entry_mode、evidence；DOM需readiness（ready/pending/unknown_timeout/page_error），失败用state非completed。导入器从真实HTML重新提取链接，忽略inline自报links。

- 从HTTP获取的页面保留requested_url/final URL与原始时点。
- 点击才能获得的状态：`discovery_mode:"interaction_only"`，例如entry_mode:pagination。图保留证据但不把这些边混成初始发现路径。
- `browser_evidence`是可选JSON proof，包含与capture相同的url/snapshot_id/document_sha256/captured_at，另含source、links、item_keys。每个link有locator、href、visible布尔、inner_text。locator为 `a[observed-index=N]`：按DOM中a、button和role=link的共同顺序从0计数。HTML解析器与浏览器位置/href必须一致，才附加可见性。
- 可见性来自浏览器CSS/布局观察，非视口曝光度；不计算完整可访问名称。原始HTML中图标、ARIA或隐藏内容交006进一步核验。
- item_keys来自显式itemSelector及itemAttribute（未设属性则实际innerText），用于分页集合对比。不要把价格或无关按钮作为条目身份；语言/排序变化导致URL字符串不同仍需Codex辨认实体，不直接认定内容错误。

采集配置必需：mainSelector、identitySelector、expectedIdentity、placeholderSelector、errorSelector。可选errorText、dynamicTitle及timeoutMs/stableWindowMs/sampleIntervalMs（默认30000/1000/250）；分页另需itemSelector、可选itemAttribute、paginationControlText。先观察页面再填配置，不能套失效选择器。采集器等待主体/实体和链接集合稳定；稳定窗口不是对所有未来异步加载的保证。

## HTTP目标

http_records：url、checked_at、source、method、status、headers（名称/值对）、evidence，可含error/state/evidence_error。状态为GET观察，不能把HEAD或缺原始证明当确定目标状态。

采集器从浏览器实际请求链保存每一跳响应元数据，evidence_kind为actual_response_metadata；对应JSON文件中的url/status/method/headers/time/source/state须与manifest一致。只保留诊断响应头，不保存Set-Cookie。原始HTML作为其他证据时仍须实际body proof；状态元信息是来源报告，不能仅凭HTML哈希证明HTTP状态。

目标解析按每个URL最新观察拼接有限链（默认最多5次跳转），报告明确并非必然同次导航；跨时点变化需重新采集。采集器的同次链文件另可直接逐跳复核。没抓取的链接目标保持not_observed；不为“完成率”而制造响应。

## 分页交互

pagination数组条目：before/after/direct分别是capture snapshot_id，action_evidence为实际操作JSON proof。

action字段：source、selector、control（tag/text/href/disabled）、before_snapshot/after_snapshot、before_document_sha256/after_document_sha256、clicked_at。时间位于前后快照之间。前后捕获必须ready并有item_keys；直达未就绪独立标未知，不能用点击后的成功覆盖它。

有真实A href时优先核验声明地址；否则核对点击后的地址。query不同可代表独立URL；仅hash变化仍属于同一文档地址。当前本机采集器会独立打开声明地址，保留实际requested_url与最终落地URL。按钮分页也可能有其他有效编号链接，不能一概判不可发现。

## 语言预期

language_expectations是JSON proof数组。每份含source_url、source_snapshot、source_document_sha256、locator、target_url、expected_language、purpose（content_navigation/language_switch）、source、checked_at。可以附加已核实的语言路由资料与具体引文。

源绑定按同URL/同进入方式最新快照核验，不被其他交互阶段替代。目标要求当前就绪DOM及实际html lang；若目标经已核实的重定向成功抵达其他URL，可关联最终页面。仅比较主要语言，地区/脚本、正文语言与切换实体完整性转010，不宣称这一检查涵盖全部国际化。
