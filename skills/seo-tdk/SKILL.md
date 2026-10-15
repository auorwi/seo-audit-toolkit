---
name: seo-tdk
description: 专项审查 目标网站 标题、描述、目标主题与路由/实体/产品匹配，盘点既有keywords，对全部指定已提取元信息聚类，结合来源绑定事实输出改写草稿、修复方向和问题历史。用于TDK与搜索意图排查；不把字数、缺keywords或未经证实的交易表述当作确定SEO结论。
---

运行前设置 `SEO_SITE_PROFILE=/absolute/path/site.json`。使用 `seo.py init` 为目标站点创建显式配置；主机采用精确白名单，不自动扩展子域。默认使用通用网站规则；`business_profile: "bingx"` 为可选业务扩展，只有明确选择它才启用对应路由和市场参考逻辑。缺少 profile 时不进行线上采集。

默认交付本地报告或问题清单。只有用户明确要求外部发布并指定或确认目的地时，才调用相应飞书/外部工具写入；无需发布时不要求外部账户授权。所有输出、证据和状态库存放在技能目录之外，按站点隔离。示例、fixtures 和既有历史记录仅用于显式选择的离线演练，不自动导入真实报告。浏览器的通用就绪信号仅证明可见正文与有限稳定性，不证明业务实体正确；如提供身份/模板信号则保持这些更强要求。


# 007 · TDK 与搜索意图

Python 3.10+标准库，依赖同级003 `seo-crawlability` v1.0.1+的证据/历史原语。独立浏览器采集另用Node、playwright-core与隔离Chromium。**不启动其他完整技能，也不运行Nu/axe。**

## 工作步骤

1. 明确本轮URL清单与模板/语言矩阵。可以使用001库存、平台异常样例或用户清单；保留查询参数和实体，不先去重掉不同业务URL。将所有需要聚类的已采集URL显式列入清单，同模板深评可抽样。不能把样本聚类称为全站重复率。
2. 打开实际页面，确认主体、实体、占位和错误选择器；使用独立采集器保存同次导航初始HTML与就绪DOM。已有新鲜真实证据可直接复用，保留原采集时间。无法打开、实体错误、加载未完成或工具失败都报告缺口。
3. 阅读[输入合同](references/evidence.md)，将Codex观察和已核实的路由/产品资料写入单独context文件。每项事实保留来源、时间、原文引用和文件哈希。正文实体必须是实际可见节点；产品上架状态必须来自独立产品资料，并绑定同一资产及产品，不能把页面宣传当作可用性证明。
4. 执行确定性检查：缺失/空/重复标签、占位/翻译key、必需国家/实体字段、动态标题稳定字段及显式事实冲突。对全部指定有效样本做title/description精确归一化聚类，按html语言分组；保留成员和原值。
5. Codex逐个代表页面评审标题、描述、H1和主体是否服务同一主题，参考明确时间窗口的页面查询数据（如有）。评审写入当前context的reviews，绑定快照、文档SHA、实际引文和事实ID。生成准确、简洁的草稿，并写明语言、模板和更新规则；无依据不承诺收益、可交易、费率或服务地区。短语拦截只是辅助手段，不保证模型任意文字都事实正确。
6. 运行报告并复核。黄金路由但BTC正文、产品类型错配等交004/012，先核验根因，不能只改标题。重复周期复用状态库；同问题更新历史，未见不自动关闭。所有草稿保留待编辑复核状态，不自动发布。

## 命令

浏览器独立采集：

```bash
node "<SKILL_DIR>/scripts/collect_page.mjs" --url "<PUBLIC_URL>" --config "<WORK>/template-signals.json" --runtime "<TOOLS>/node-runtime" --browser-executable "<CHROME_PATH>" --output "<NEW_CAPTURE_DIR>"
```

浏览器输出manifest可直接审查；补充真实context并更新其文件proof后可进行语义评审：

```bash
python3 "<SKILL_DIR>/scripts/audit_tdk.py" --manifest "<NEW_CAPTURE_DIR>/manifest.json" --urls "<NEW_CAPTURE_DIR>/urls.json" --state "<DATA>/tdk" --output "<NEW_REPORT_DIR>"
```

- `--supplement`重复合并其他manifest；`--url`可重复；`--urls`是URL字符串数组。
- 默认时效168小时；`--max-age-hours`可改；`--at`用于明确回放，不得把旧证据改成今天。
- 每次使用新输出目录。退出0仅指指定范围执行完整，2指有缺口或人工待审，1指输入/执行错误。常规含语义待审的审查返回2，不能当成全站通过。
- 输出report.md/json、coverage.csv、findings.csv、duplicate-clusters.csv、drafts.json、handoffs.csv及issue-history.json/csv。Markdown限量展示，完整证据保留在JSON/CSV。

规则细节与边界见[规则](references/rules.md)，环境与测试见[运行和测试](references/runtime.md)。需要飞书时通过当前飞书文档能力发布并回读，不内置凭证或发送消息。

## 维护

v1.0.0。新行为先失败用例，再实现、回归、真实证据验收和安装验证。

```bash
python3 -m unittest discover -s "<SKILL_DIR>/tests" -v
```
