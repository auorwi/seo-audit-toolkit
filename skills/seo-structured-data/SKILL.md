---
name: seo-structured-data
description: 专项核验 目标网站 的 JSON-LD、Microdata、RDFa、价格评分与面包屑规则、实体引用和进入路径差异，绑定实际DOM与平台证据输出修复方向和问题历史。用于结构化数据与富媒体异常排查；区分本地规则、引擎资格和实际展示，不补造评分或保证富媒体结果。
---

运行前设置 `SEO_SITE_PROFILE=/absolute/path/site.json`。使用 `seo.py init` 为目标站点创建显式配置；主机采用精确白名单，不自动扩展子域。默认使用通用网站规则；`business_profile: "bingx"` 为可选业务扩展，只有明确选择它才启用对应路由和市场参考逻辑。缺少 profile 时不进行线上采集。

默认交付本地报告或问题清单。只有用户明确要求外部发布并指定或确认目的地时，才调用相应飞书/外部工具写入；无需发布时不要求外部账户授权。所有输出、证据和状态库存放在技能目录之外，按站点隔离。示例、fixtures 和既有历史记录仅用于显式选择的离线演练，不自动导入真实报告。浏览器的通用就绪信号仅证明可见正文与有限稳定性，不证明业务实体正确；如提供身份/模板信号则保持这些更强要求。


# 008 · 结构化数据与实体图

独立专项技能 v1.0.0。Python 审查依赖同级003 `seo-crawlability` 的证据/账本原语；浏览器采集复用同级007 `seo-tdk` 的就绪判断函数。不会运行这两个完整审查。Microdata/RDFa 使用实际 extruct，不能用自写的演示结果代替。

## 执行

1. 从001库存、平台样例或用户清单确定URL与进入方式。全量解析已收集HTML，按模板抽样做可见内容与类型适用性评审。保留原URL参数、来源、时间和未覆盖范围；不把两页验收说成全站审核。
2. 实际打开页面确认主体、实体、加载/错误节点及必要业务字段，使用采集器保存初始HTML、稳定DOM、可见文本和导航证据。对于加载后的奖励金额等字段配置 `contentChecks`；标题稳定不代表业务内容就绪。超时/错误保留缺口。内部入口必须是实际观察到的可见链接。
3. 对每份待审HTML执行 `extract_embedded.py`，保存原生Microdata/RDFa结果与HTML SHA。加载新鲜的官方Schema.org词汇文件和来源/哈希。依赖失败、未知词汇上下文、未采集格式与“成功提取为空”分别记录。输入细节见[证据合同](references/evidence.md)。
4. 审阅同一稳定DOM的可见事实与实体字段，写入独立context证据。每项绑定URL、snapshot、SHA、script序号、实体路径/ID、原值、可见引文和观察时间。仅有币种行情或Product类型不能推断购物资格；只对明确适用页面启用局部Google配置。评分来源未见就保留待审，不能补造评分或默认填0。
5. 执行确定性审查并阅读四层结论：JSON语法、Schema用法、搜索引擎资格、实际展示。比较同次直接访问的初始/渲染、不同进入方式的稳定DOM；重复声明是候选，动态价格变化不直接归因于路由故障。
6. 如有平台历史、Rich Results Test或SERP证据，保留原始导出/截图文件并制作明确映射。代码测试必须绑定当前HTML SHA；URL测试不能伪装为本地快照测试；本轮未复现不自动关闭历史。没有真实引擎结果就保持未验证。
7. 阅读报告并补充逐项可执行修复：字段、当前证据、修改位置/数据源假设、复测方法。数值示例只能来自当前可见值，动态价格不能硬编码。复用同一个状态库去重，每次新报告目录；需要飞书时使用当前飞书文档能力发布并回读，不发送通知或修改生产页面。

## 命令

```bash
node "<SKILL_DIR>/scripts/collect_page.mjs" --url "<PUBLIC_URL>" --config "<WORK>/signals.json" --runtime "<NODE_RUNTIME>" --browser-executable "<CHROME>" --output "<NEW_CAPTURE_DIR>"
"<EXTRUCT_PYTHON>" "<SKILL_DIR>/scripts/extract_embedded.py" --html "<NEW_CAPTURE_DIR>/dom.html" --url "<PUBLIC_URL>" --output "<NEW_CAPTURE_DIR>/extruct-dom.json"
python3 "<SKILL_DIR>/scripts/audit_structured.py" --manifest "<WORK>/reviewed-manifest.json" --urls "<WORK>/urls.json" --state "<DATA>/structured-data" --output "<NEW_REPORT_DIR>"
```

- 对初始HTML也运行提取器；将真实结果文件proof加到manifest的 `extraction_evidence`，context加为 `context_evidence`，不要编写inline假实体。
- `--entry-origin` 与 `--entry-link` 一起使用执行站内进入；不自动点击交易或账户操作。当前内部入口不保存目标初始响应，报告明确这个缺口。
- `--supplement` 可重复，`--url` 可重复。URL字符串默认要求direct/internal两种进入；对象可明确只审direct。详见证据合同。
- 输出report.md/json、coverage/findings/graph-edges/issue-history CSV、entities/examples/engine-evidence/history JSON。
- 审查退出0仅表示指定执行范围完成，2表示有证据缺口或待评审，1是输入/执行错误。浏览器0表示配置范围内就绪，2未就绪；extruct 0只表示两种语法提取完成。三者均不等于全站SEO无问题。
- 默认时效168小时；`--at`仅用于明确回放，不能把旧证据刷新成今天。

[规则与边界](references/rules.md) · [运行环境与测试](references/runtime.md)
