> Historical/opt-in BingX example. Apply to generic sites only after replacing URLs, selectors, and business assumptions with current evidence from the selected profile; never auto-import example evidence.

# 修复复测证据合同

全部路径相对plan所在目录，限制16MiB、禁止越界/软链接越界、重复JSON键、NaN、凭证；引用`{path,sha256}`。源报告必须唯一包含原issue_id；不相信操作者另造的新问题。读取失败的源问题不产生假验收记录。无效快照隔离且保留缺口。

## Plan

```json
{
  "schema_version": 1,
  "run_kind": "audit",
  "issues": [{
    "issue_id": "原技能已有ID",
    "source_report": {"path":"original-report.json","sha256":"真实哈希"},
    "scope_type":"url",
    "deployment":null,
    "cases":[{
      "id":"route-entity-direct-desktop",
      "role":"symptom",
      "url":"https://bingx.com/en/futures/forex/EURCAD",
      "device":"DESKTOP",
      "js":"ENABLED",
      "entry":"direct",
      "predicate":{"field":"h1","op":"equals","expected":["EURCAD"]},
      "baseline":{"kind":"dom","entry":"direct","source":{"path":"before.json","sha256":"真实哈希"}},
      "after":[{"kind":"dom","entry":"direct","source":{"path":"after.json","sha256":"真实哈希"}}],
      "repetitions":2
    }],
    "engine_reports":[{"platform":"yandex","source":{"path":"yandex-report.json","sha256":"真实哈希"}}]
  }]
}
```

上例是形状示意，不是批准的EURCAD产品策略。实际expected应来自修复方案与业务意图；条件未明确时记录症状，不声称完成修复验收。

- run_kind：audit/controlled_fixture/historical_replay。fixture历史独立命名空间，issue_id本身保持原值。
- scope_type：url/template/unknown；url要求原问题有精确URL。模板和unknown不会被一组样本自动关闭。
- deployment：`{at,source:{path,sha256},quote}`；quote在源文件中且含该带时区时间。部署范围及版本作为上下文由操作者核对；没有证据就null，不使用聊天时间代替。
- cases至少一个symptom，控制样本role=control。case_id不得重复；symptom URL必须与原问题URL一致。device为DESKTOP/MOBILE/UNKNOWN；js为ENABLED/DISABLED/UNKNOWN；entry为direct/internal/back。进入方式由真实复现记录标注，不能为匹配而更改。
- baseline的SHA必须存在于原问题的证据引用，时间不晚于源报告。症状基线应确实失败，否则无法证明“原问题已修复”。控制样本可没有失败基线。
- repetitions 1–100，按不同采集时点去重；相同时间内容冲突为无法判定。它计采集，不代表独立地区/独立爬虫；需要多次新导航时应实际执行并核对每条navigation_at。

## 捕获格式

DOM JSON包含url、captured_at、device、js=ENABLED、navigation_at以及真实读取的title/description/h1/canonical/body_excerpt。navigation_at指完成新导航被观察的时间，不冒充网络请求起始时间。部署后通过要求它不早于部署且晚于失败基线；旧标签页可记录症状仍存在，但不足以证明修复。

HTTP JSON包含url、final_url、captured_at、device、js=DISABLED、method=GET、status。当前实现不同最终落点保守列待专业核验；若修复策略是迁移，先由004证明原URL/目标等价，再制定迁移验收，不能将目标200作为旧页面修复通过。

captured_at/navigation_at均为带时区实际时间。未来、过期、设备/JS/进入方式/精确URL不匹配的after隔离。业务查询参数保留，不通过canonical合并。

## 谓词

- equals：类型和值均相等；true不能等同整数1。
- in：类型和值匹配非空允许列表；适用于HTTP状态码。
- nonempty：非空字符串或至少一项非空字符串的列表。
- contains/not_contains：大小写敏感非空字符串，不使用任意代码或正则。
- 字段缺失/null/类型不支持→inconclusive。不能把缺值当作“没有问题”。
- 对body_excerpt，存在文字可以得到肯定观察；没有出现文字不能证明全文不存在，因此not_contains未找到时inconclusive。title/description/h1/canonical等已完整提取的字段可用于完整性判断。此机制不会认定截图或模型摘要等同于真实DOM。

通过谓词只能证明相应条件，不自动证明语义、产品合法性或原问题根因。复杂验收应结合主责专业技能的原始证据。

## 引擎与历史

engine_reports支持014 Google、015 Bing、016 Yandex报告，必须匹配平台编号、SHA和新鲜度。保持其原URL/设备/JS与数据库时点；同原ID有后台观察记issue_still_reported，仅有公共DOM观察不当成引擎报错。未检查原URL记exact_url_not_checked。找到快照但问题清除未知记snapshot_available_clearance_unverified。列表缺席和已收录不等于原问题已解决。

SQLite写入独立recheck事件，幂等run ID基于结果内容；重新评估内容变化是新事件，同证据同结果重放不重复。原ID、首次/最后验收时间及复发保留；乱序旧结果不覆盖最新结果。原专项台账不修改，缺席不关闭。report-initial等早期结果应标明阶段，不能当作额外线上采集。
