> Historical/opt-in BingX example. Apply to generic sites only after replacing URLs, selectors, and business assumptions with current evidence from the selected profile; never auto-import example evidence.

# 输入与证据合同

manifest为JSON，schema_version=1。所有文件证据使用 `{path,bytes,sha256}`，相对于manifest目录，不能越界，单文件最多8MB。页面字节不符合哈希时保留失败尝试，不能退回旧成功冒充本次状态。

## captures

每条包含url、snapshot_id、captured_at（带时区）、source、representation（initial_html/rendered_html）、state、document_sha256、evidence；rendered_html须readiness=ready才进入当前判断。entry_mode区分direct、language_switch等入口；requested_url保留重定向前地址。

解析器从实际HTML提取声明，不信manifest内附带的html_lang或canonical断言。browser_evidence是文件证明，内含相同url/snapshot_id/captured_at/document_sha256和source；visible_main、main_selector、visible_fields来自同一次DOM evaluate。没有绑定浏览器证据时可做声明检查，但不能凭原始HTML假装读取了可见正文。

initial_html使用HTMLParser提取明确标签，不是完整HTML5修复器；浏览器修复后的DOM另行保留。模板/noscript不混入普通活动声明。复杂扩展JSON-LD上下文解释交008；本项提取字面inLanguage，作为上下文复核线索。

## http_records与sitemaps

HTTP每条含url、checked_at、source、state、method、status、headers数组、evidence、evidence_kind=actual_response_metadata。证据JSON相应字段必须与manifest相同。HEAD不替代GET，跨跳链由最新独立观察拼接时明确说明；不冒称必然来自同一次导航。仅实际2xx GET响应头参与当前语言声明。

sitemaps每条含url、captured_at、source、evidence，正文必须是标准命名空间urlset及XHTML link；拒绝DTD/实体。Sitemap index由002展开，本项不把索引文件冒充页面语言表。

## body_reviews、asset_mappings、switches

这些数组存放文件证明；文件内容可为单对象或对象数组。

正文复核对象：
```json
{"url":"https://bingx.com/fr/example","snapshot_id":"实际ID","document_sha256":"实际SHA256","reviewed_at":"带时区时间","source":"Codex对指定visible_main的复核","method":"llm_review","confidence":"high","body_language":"fr","entity_id":"明确实体ID","quotes":["实际正文原文片段"]}
```
引文必须逐字出现在已绑定visible_main；reviewed_at不能早于该快照。方法支持human_review/llm_review，高置信才进入比较，其余保持缺口。entity_id需依据实际主题/实体和引文解释，不能从路径硬赋值；复杂实体对应留待审。同一URL不同入口的语种/实体复核冲突时，不挑一个覆盖另一个。

发布对应表每条至少url、source、mapped_at；可加locale、entity_id、published布尔、required_fields数组、canonical_policy。仅published=true的明确同实体版本用于遗漏候选；没有独立CMS发布清单时说明只是已观察页面子集。旧对应表不用于推断当前缺页。required_fields只与浏览器实际采集的visible_fields比较，未采集字段保持未知。

语言切换对象含source、selector、control、clicked_at、expected_locale、before_snapshot/after_snapshot、before_sha256/after_sha256、before_url/after_url。点击时间在前后快照之间，前后就绪且正文复核/实体齐全才给实体保持结论。采集器保存真实操作文件；UI操作后的HTTP初始响应可能未捕获，不补造，必要时独立直达补采。

## 浏览器信号

必需mainSelector、identitySelector、expectedIdentity、placeholderSelector、errorSelector；errorText可限制错误文本；可选requiredText、expectedHtmlLang、fieldSelectors、dynamicTitle。超时/stableWindow/sampleInterval为正毫秒值。requiredText用于已观察的业务加载条件，不能用预期语种覆盖实际正文证据。

模型复核与业务对应表都是可追溯的判断输入，不是网站天然事实。report.json保留输入来源、快照和全部缺口；最终报告须明确哪些是机器规则、HTTP观察、模型候选和未验证范围。
