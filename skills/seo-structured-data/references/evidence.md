> Historical/opt-in BingX example. Apply to generic sites only after replacing URLs, selectors, and business assumptions with current evidence from the selected profile; never auto-import example evidence.

# 证据输入合同

manifest顶层 `schema_version:1`，`captures:[]`，可选 `vocabulary`、`engine_reports`。文件proof统一为 `{path,bytes,sha256}`，相对manifest目录；路径不能逃出目录，SHA/字节数须匹配实际文件。HTML最多8MiB。不嵌入凭证。

## 页面

capture字段：url、snapshot_id（唯一）、captured_at（带时区ISO时间）、document_sha256、source、representation（initial_html/rendered_html）、entry_mode（direct/internal/history_return）、evidence。rendered_html另含readiness（ready/pending/unknown_timeout/page_error）。失败可用state非completed；失败记录仍参与“最新尝试”选择，不能回退到旧成功。

可选proof：
- visible_evidence：JSON包含url/snapshot_id/captured_at/document_sha256/source/visible_text，与HTML绑定；浏览器采集器在同一个evaluate中取HTML与body.innerText。
- extraction_evidence：`extract_embedded.py`的原生结果；包含tool、checker_version、source、checked_at、url、document/input SHA、syntaxes、payload、state。分别执行Microdata/RDFa，未成功的格式是缺口。
- context_evidence：见下。

内部导航保存navigation.json：实际入口URL、点击时间、链接原始HTML/href、最终URL。当前CLI支持同标签页可见A链接；新标签、菜单展开、浏览器后退可由Codex使用实际浏览器采集后导入，不能把未执行路径改名成已执行。已有内部采集无初始HTML时仍会报缺口。

URL清单例：
```json
[{"url":"https://bingx.com/en/price/bitcoin","entries":["direct","internal"]},{"url":"https://bingx.com/en/download","entries":["direct"]}]
```

## 就绪配置

必需：mainSelector、identitySelector、expectedIdentity、placeholderSelector、errorSelector。可选errorText限定实际错误文案，dynamicTitle允许动态币价标题变化；timeoutMs/stableWindowMs/sampleIntervalMs默认30000/1000/250。

可选 `contentChecks:[{"selector":".leading-sub-title","requiredText":"USDT","forbiddenText":"--"}]`。每项要求可见非空文本及至少一个非空判定条件；业务字段与结构化声明均需稳定至少两次采样。选择器来自现场观察，不复用失效模板。持续变动的结构化行情可能超时，应标记无法获得稳定窗口。

## Codex上下文

context含url、snapshot_id、document_sha256、checked_at、source、profile、checks。
profile可null，或 `{name:"google_software_app",applicable:true,quote:"Download BingX App",reason:"..."}`。还支持google_product_snippet/google_breadcrumb。引文必须存在于当前可见文本；false不启用规则。此配置只选择局部规则，不是适用性的自动证明。

每条check：entity_id（无ID可null）、entity_path（提取JSON路径）、script_index（从0起）、field（当前实体直接字段）、schema_value、visible_quote、selector、status（format_issue/mismatch/matches/unknown）、reason、observed_at。同ID同路径跨script不明确时必须提供script_index；不能忽略冲突值。

可选recommended_value与update_rule仅支持price/lowPrice/highPrice/ratingValue/ratingCount/reviewCount，且必须等于明确可见数字；引文支持英文常见 `$1,234.56` 写法，其他本地化数字不猜测。输出为采集时点示例，非上线值。matches/unknown不产生故障；全局可见真实性、类型适用性和引擎表现仍需评审。

## 词汇

`vocabulary:{evidence,source,retrieved_at}`：source需https://schema.org/官方文件，evidence指向JSON-LD词汇图。保留官方文件原字节，默认同样168小时。`latest`不是固定版本号，应以下载时间和SHA标识。

## 搜索引擎证据

`engine_reports:[{evidence,original_evidence}]`：前者是映射JSON，后者是实际导出/截图。仅提交手填映射不算原始证据。映射含url、engine:"Google"、tool、source、checked_at、kind、result。artifact_sha256由原始文件proof校验后填入。

- historical_issue：rule为本地明确映射规则，result:error；可选entity_id/field缩小范围。当前实体/字段缺失或未检查不算修复。局部规则不能证明平台重抓。
- code_test：result:valid/invalid，document_sha256需绑定当前就绪HTML；test_failed不回退旧valid。
- url_test：可保留远端URL测试，但远端文档与本地HTML未绑定。
- serp_observation：result:observed及query/device/locale/feature，表示记录时间/环境中观察到结果，不是永久展示承诺。

引擎摘要按每种kind/tool取最新结果，不自动解释不同工具间冲突；完整tests保留，冲突需Codex说明。Bing/Yandex平台映射由后续专项采集，当前008不假装支持其Google富媒体测试合同。
