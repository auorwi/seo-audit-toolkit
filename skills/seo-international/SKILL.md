---
name: seo-international
description: 专项核验 目标网站 多语言页面的hreflang、正文语种、canonical、Schema语言和语言切换实体，保留HTTP/HTML/Sitemap与实际正文证据并维护稳定问题历史。用于技术国际化排查；不把路径语言、抽样或声明存在当成翻译正确和已收录证明。
---

运行前设置 `SEO_SITE_PROFILE=/absolute/path/site.json`。使用 `seo.py init` 为目标站点创建显式配置；主机采用精确白名单，不自动扩展子域。默认使用通用网站规则；`business_profile: "bingx"` 为可选业务扩展，只有明确选择它才启用对应路由和市场参考逻辑。缺少 profile 时不进行线上采集。

默认交付本地报告或问题清单。只有用户明确要求外部发布并指定或确认目的地时，才调用相应飞书/外部工具写入；无需发布时不要求外部账户授权。所有输出、证据和状态库存放在技能目录之外，按站点隔离。示例、fixtures 和既有历史记录仅用于显式选择的离线演练，不自动导入真实报告。浏览器的通用就绪信号仅证明可见正文与有限稳定性，不证明业务实体正确；如提供身份/模板信号则保持这些更强要求。


# 010 · 技术国际化

独立专项 v1.0.0。复用同级003证据与账本、007浏览器就绪函数、009目标响应链评估原语，不启动其他完整技能，不含总调度入口。

## 工作方法

1. 先读取001资产及明确的语言/实体发布对应表。按模板、语言、入口抽样；新变更、历史问题和高价值页面优先。已发现URL和实际已发布翻译分开，不能由Sitemap或路由规则推断所有语言必有页面。
2. 打开实际页面确认正文、实体标题、加载/错误信号，保存初始响应与业务就绪DOM。采集范围明确后检查HTML、HTTP Link及已使用的Sitemap语言声明；三种方法可共存，不要求网站只用一种。
3. 检查语言、地区与脚本代码、目标完整URL、声明位置、冲突、自关联与返回关联，建立同实体语言组。缺目标证据保留未知；只在已观察渠道没找到返回关联时标记候选，不能声称其他渠道也没有。
4. 实际GET语言目标，保留原始地址、各跳状态与最终正文。HTTP200不证明内容正确，403/429不算永久失效。跨语言canonical需比较两端实质正文、实体与策略；同语言地区重复页可有共享canonical，不机械判错。
5. Codex阅读被采集的**可见主内容**，记录语种、实体ID、原文引文、判断来源和置信度。生成的body_review须绑定URL、快照ID、SHA和时间。不能仅由路径、html lang、title、Schema或页脚推断正文语种；短文、混合语种、不确定实体保持待审。模型判断不冒充人工或官方认证。
6. 如范围包含语言切换，实际操作已观察的语言控件，记录前后URL、正文、实体与目标语言。主页跳转、加载失败与实体变化分别记录。找不到控件或没取得真实操作证据时不写“切换通过”。按钮操作只改变隔离浏览器的公开页面语言，不操作账户、交易或地域限制。
7. 按明确业务要求检查本地化字段，例如买币页国家选择。字段是否必需来自业务/发布对应表；缺采集不能写成缺字段。文案地道程度、金融推广适用性和合规结论留给019及相应业务审核。
8. 运行专项审查，复核每条候选，写出具体模板/字段修复与复测步骤。证据有冲突或过期则保留缺口。同一状态目录累积稳定ID，本轮未见不自动关闭。需飞书时使用可用文档能力发布并回读；不自动修改生产、提交索引或发送消息。

## 调用

```bash
node "<SKILL_DIR>/scripts/collect_page.mjs" --url "<PUBLIC_URL>" --config "<WORK>/signals.json" --runtime "<NODE_RUNTIME>" --browser-executable "<CHROME>" --output "<NEW_CAPTURE_DIR>"
python3 "<SKILL_DIR>/scripts/audit_international.py" --manifest "<WORK>/reviewed-manifest.json" --supplement "<OTHER_MANIFEST>" --state "<DATA>/international" --output "<NEW_REPORT_DIR>"
```

`--supplement`可重复。采集器每次只处理一个公开URL及可选语言切换；批量范围、限速、缓存由调用者明确，不递归展开全站。可配置 `--switch-selector`、`--switch-config`、`--switch-locale`、`--switch-text`，必要时先用已观察的 `--menu-selector` 打开语言菜单。选择器和目标语言配置必须来自实际页面观察。

默认证据时效168小时，可设 `--max-age-hours`；`--at`用于明确回放。退出2表示报告带缺口/待审，1表示输入或执行错误；采集0表示配置范围就绪，不能解读为网站健康。当前审查保留引擎采纳、文案适用性等人工判断项，因此通常退出2。

输出语言矩阵、正文引文、目标响应、切换过程、问题与历史JSON/CSV，以及Markdown报告。

[输入与证据](references/evidence.md) · [规则、修复与边界](references/rules.md) · [运行与测试](references/runtime.md) · [数据来源](references/data-sources.md)
