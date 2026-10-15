> Historical/opt-in BingX example. Apply to generic sites only after replacing URLs, selectors, and business assumptions with current evidence from the selected profile; never auto-import example evidence.

# 输入与持久状态

manifest 示例（SHA必须由真实字节计算，下面省略值不能直接使用）：

```json
{"site":"bingx.com","run_id":"weekly-2026-09-17","at":"2026-09-17T06:00:00Z","sources":[{"skill":"016","path":"sources/016.json","sha256":"实际64位SHA256"}]}
```

来源路径限manifest所在目录内，允许子目录，禁止越界/逃逸链接。单报告最大64MiB。001summary有generated_at/url_count/coverage_claim；002接受skill=002-sitemap与id；003–016接受skill/skill_id、at、findings；017接受rechecks。时间必须带时区，不接受未来报告、重复JSON键、非有限数、凭证字段或fixture。源报告本身的SHA已验证，不意味着底层每张截图/HTML都在本轮重验。

保持业务参数、尾斜线、大小写；不按canonical合并ID。问题记录沿用issue_id/id；相同ID必须规则与精确URL一致。classification/certainty、recommendation、retest及evidence原样保存在report.json。源报告 coverage、gaps、input_gaps、limitations、platform_reports全部保留，不把平台总体数相加。

SQLite ledger.sqlite保存唯一内容事件与来源报告。first_seen/last_seen为来源观察时间（无观察时间时为源报告生成时间），不是本工具导入时间，也不代表问题在网站首次发生。过期版本可重放，但不覆盖已知更新值。同时间矛盾拒绝并回滚。本轮没有出现的问题仍保留seen_in_run=false；open意为待处置记录，含候选与缺口。

分类：confirmed包括原始confirmed/evidence_supported_conflict/html_conformance_error/accessibility_violation；environment_limited独立；evidence_gap独立；engine_observation等列platform_observation；其余review。每类保留原分类，不提升确定性；没有统一受影响页数、没有推断SEO排名损失。

017复查与原问题精确URL/rule绑定；最新复查单独显示，源记录不关闭。引擎恢复必须另证；报告里的repair_verified也不能覆盖更广模板的未测部分。跨技能重复症状保留不同ID和责任技能，只有主责复核后才在人工根因治理中关联，脚本不做模糊去重。

输出report.md/json、issues.csv、publication.json。CSV做公式前缀转义；JSON保留完整值。将源码升级与state分开，备份state和源证据，不把测试目录当生产数据。

部分审查可在 manifest 显式设置 requested_skills，例如 ["014"] 只要求 GSC，或 ["014","015","016"] 要求三平台。missing_skills仅列所要求但没有报告的技能；不填写时按001–017全部检查报告计算。无论范围大小都不推断全站通过。
