> Historical/opt-in BingX example. Apply to generic sites only after replacing URLs, selectors, and business assumptions with current evidence from the selected profile; never auto-import example evidence.

# 007 输入与证据合同

## 采集配置与manifest

浏览器配置必填mainSelector、identitySelector、expectedIdentity、placeholderSelector、errorSelector；从实际DOM观察后填写。可选errorText只匹配已观察的错误提示。默认timeoutMs30000、stableWindowMs1000、sampleIntervalMs250。正文、实体、占位和标题/描述稳定性共同判断；至少2份样本，预算到期unknown_timeout。dynamicTitle=true仅跳过不断变化的标题稳定性比较；标题实体/交易对仍由dynamic_title规则核对，不能因此省略事实配置。

采集输出dom.html、initial.html（如读取成功）、capture.json、collection.json、manifest.json、urls.json。隔离桌面未登录浏览器，不复用用户个人profile；只访问公开站点，不进行业务交易。支持bingx.com、www、blog、fiat子域；跨站最终导航拒绝。位置、设备、登录状态有限，不能代表所有用户或搜索机器人。

manifest根：`schema_version:1,captures:[...]`。每个capture：

- url、snapshot_id、captured_at（带时区）、source。
- representation：initial_html或rendered_html。
- document_sha256与evidence一致；evidence为`{path,bytes,sha256}`，文件相对manifest，不允许越界，最大8MiB。
- rendered_html必须有readiness：ready/pending/unknown_timeout/page_error。
- 失败可用state=timeout/http_error/evidence_error等记录尝试，不能回退旧成功。缺失或损坏文件的有效时间戳也保留失败尝试。
- 可选context_evidence：单独context JSON文件proof。内联fields不会覆盖实际HTML提取结果。

单URL优先最新渲染尝试；没有渲染才用最新原始HTML并标明缺口。该技能不比较全部进入路径，交005。初始与渲染各自有时间和哈希，不合并成同一内容。

## context与事实

根字段：url、snapshot_id、document_sha256必须对应capture；checked_at、source、template、language；facts数组、requirements数组、translation_keys数组、dynamic_title对象及reviews数组按需填写。

fact字段：id、role、value、aliases、origin、quote、source、observed_at。

- origin=page：quote必须出现在当前DOM正文文本中，value必须出现在quote中；location记录实际节点，visibility必须为visible。代码验证文本绑定，Codex负责真实观察可见性，不能用源HTML冒充可见DOM。
- origin=route_registry/product_catalog/search_console：另提供document_evidence引用实际本地原始资料；读取时验证文件后填入document。不能内联捏造document绕过proof。事实值和引文须有原文支持。
- role示例：page_entity、route_entity、page_product、route_product、country、target_topic、listing_status。
- listing_status限listed/not_listed/delisted/unknown，来源必须product_catalog；subject含entity、product、market_scope。实体匹配当前页面事实，实体和产品必须在目录引文中。市场/产品适用性仍需复核，不能把某地区某产品可用扩为全球所有服务。
- aliases只用于元信息匹配，不能让无关引文证明另一个value。多个冲突实体不静默取最后一个。

requirements示例：`[{"field":"title","fact_id":"project"},{"field":"description","fact_id":"country"}]`。只能引用已验证事实。字段不适用时不要强配必需项。

translation_keys仅填写已观察/代码确认的具体key，不把正常币种缩写当翻译key。dynamic_title示例：`{"enabled":true,"stable_fact_ids":["asset","pair"]}`，事实须独立可核实，不能只检查数字。

搜索表现可通过search_console来源的已导出资料辅助topic事实；保留日期、页面与查询范围。007不假设已经接入GSC API，不把CTR变化直接诊断成技术故障。

## reviews与草稿

每条包含snapshot_id、document_sha256、checked_at、source、topic（search_intent/language_and_wording）、status（needs_change/looks_reasonable/unknown）、quotes、fact_ids、reason、language、update_rule和proposed。

quotes为`[{"field":"titles","text":"实际标题原文"},{"field":"body_text","text":"实际正文原文"}]`。字段可为titles/descriptions/keywords/h1/body_text。proposed仅title/description字符串，事实引用不得缺失；language对应context。改写不能偷偷把SOLV换成ETH。

不完整绑定、不支持的引用或过期资料归缺口；路由/产品冲突、明显收益保证、未经目录确认的交易建议会拦截。**所有通过辅助检查的草稿仍为draft_requires_editorial_review**；该规则不能自动证明语言、法律合规、服务区域或任意文本所有主张正确，不自动发布。
