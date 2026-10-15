---
name: seo-internal-links
description: 专项核验 目标网站 内链、目标响应、分入口发现路径、孤立候选及分页href与直达行为，保留全部已观察来源、DOM和HTTP证据并维护问题历史。用于内链与分页排查；不把抽样无入链、深度阈值或nofollow当成全站孤立或抓取失败的证明。
---

运行前设置 `SEO_SITE_PROFILE=/absolute/path/site.json`。使用 `seo.py init` 为目标站点创建显式配置；主机采用精确白名单，不自动扩展子域。默认使用通用网站规则；`business_profile: "bingx"` 为可选业务扩展，只有明确选择它才启用对应路由和市场参考逻辑。缺少 profile 时不进行线上采集。

默认交付本地报告或问题清单。只有用户明确要求外部发布并指定或确认目的地时，才调用相应飞书/外部工具写入；无需发布时不要求外部账户授权。所有输出、证据和状态库存放在技能目录之外，按站点隔离。示例、fixtures 和既有历史记录仅用于显式选择的离线演练，不自动导入真实报告。浏览器的通用就绪信号仅证明可见正文与有限稳定性，不证明业务实体正确；如提供身份/模板信号则保持这些更强要求。


# 009 · 内链与发现路径

独立专项 v1.0.0。Python标准库审查复用同级003 `seo-crawlability` 的证据/账本原语；Node采集复用同级007 `seo-tdk` 就绪判断函数。不会启动其他完整技能。

## 执行

1. 使用001 URL资产清单和本轮明确的源页面范围。分别设置首页、分类、关键业务入口种子；源页面不足时保留缺口。重要URL的“无观察入链”只作候选，不能把Sitemap全集当完整链接图。常规巡查复用新鲜的原始HTML/稳定DOM，模型深评按模板抽样。
2. 实际打开页面确认主体、实体、加载/错误信号与列表条目选择器；采集初始HTML、稳定DOM、实际链接可见性及目标GET。检查真实href，不从点击事件或routerLink猜目的地。详见[证据合同](references/evidence.md)。
3. 对分页实际点击已观察的编号/下一页控件，同时独立打开它声明的href。对比点击前后URL、列表条目和直达响应。记录完整HTTP跳转链；地址没变但href存在时不能谎称“没有href”。点击后才出现的链接标记interaction_only，不混进普通初始发现图。
4. 构建观察图、去掉同来源-目标关系的重复计数，但保留每个节点位置和来源快照。按不同入口分别计算最短路径。目标状态需有真实GET证据；只解析链接但没访问目标时明确未观察，不能补造404。
5. Codex审核高价值页面的来源位置、锚文本和目标内容，选取真实相关分类/正文作为新增链接入口。空锚文本候选不等于可访问名称失败；语义化与可访问名称可交006。重定向目标先核对实体等价，再建议改链接；转004处理复杂路由。
6. 错误语言检查需要明确预期、源快照/链接绑定及实际目标html lang；实际重定向可关联最终页面。语言切换控件与普通内容导航分开，正文语言及地区对应关系交010。不会仅因路径是fr/en不同就判错。
7. 运行报告，复核断链全部已观察来源、分页、模板入口和证据缺口。目标响应的批量抓取应有范围/速率/页面数上限，遵守已知robots与访问限制，避免无限展开参数组合。参数变体多只是排查线索。
8. 同一状态目录累积稳定问题ID；候选/历史本轮未见不自动关闭。需飞书时使用当前飞书文档能力发布并回读；不修改生产页面、提交索引或发送消息。

## 命令

```bash
node "<SKILL_DIR>/scripts/collect_page.mjs" --url "<PUBLIC_URL>" --config "<WORK>/signals.json" --runtime "<NODE_RUNTIME>" --browser-executable "<CHROME>" --output "<NEW_CAPTURE_DIR>"
python3 "<SKILL_DIR>/scripts/audit_links.py" --manifest "<WORK>/manifest.json" --state "<DATA>/internal-links" --output "<NEW_REPORT_DIR>"
```

可选 `--pagination-selector` 操作已观察控件；配置必须包含itemSelector和paginationControlText。采集器只是一个URL及可选分页操作，不是全站爬虫。需要更多源/目标时按明确范围运行并用 `--supplement` 合并manifest；不同入口种子用不同组名，相同组名内容冲突会拒绝。

默认时效168小时；可设 `--max-age-hours`。`--depth-hint`默认4，`--parameter-variant-hint`默认100，均为本轮排查阈值；`--expected-parameter page`可声明正常参数。`--at`仅用于明确回放。

输出report.md/json、edges/nodes/paths/findings/orphan-candidates/issue-history CSV及targets/pagination/history JSON。全部已观察链接位置在edges.csv，Markdown按规则分组限量展示。

审查退出0只表示指定执行范围完成，2为证据缺口/待审，1为输入/执行错误；浏览器0只表示配置范围内就绪，2为部分采集。均不代表网站没有任何问题。

[证据合同](references/evidence.md) · [判断范围与修复](references/rules.md) · [运行与测试](references/runtime.md)
