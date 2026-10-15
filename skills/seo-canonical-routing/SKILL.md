---
name: seo-canonical-routing
description: 专项核验 目标网站 canonical、业务参数、HTTP/客户端跳转、目标状态及实体/语言等价性，输出关系图、逐URL修复方向与稳定问题历史。用于规范目标和路由错配；保留原始资产，不修改线上路由或推断引擎必然采用声明。
---

运行前设置 `SEO_SITE_PROFILE=/absolute/path/site.json`。使用 `seo.py init` 为目标站点创建显式配置；主机采用精确白名单，不自动扩展子域。默认使用通用网站规则；`business_profile: "bingx"` 为可选业务扩展，只有明确选择它才启用对应路由和市场参考逻辑。缺少 profile 时不进行线上采集。

默认交付本地报告或问题清单。只有用户明确要求外部发布并指定或确认目的地时，才调用相应飞书/外部工具写入；无需发布时不要求外部账户授权。所有输出、证据和状态库存放在技能目录之外，按站点隔离。示例、fixtures 和既有历史记录仅用于显式选择的离线演练，不自动导入真实报告。浏览器的通用就绪信号仅证明可见正文与有限稳定性，不证明业务实体正确；如提供身份/模板信号则保持这些更强要求。


# 004 · Canonical 与路由

Python 3.10+ 标准库。依赖同级安装的 `seo-crawlability` v1.0.1+ 的证据、HTTP、robots 与历史原语；不启动003完整审查。新取数使用001 v1.0.3+，以保留 Link/Refresh 和采集范围。数据不放在技能目录中。

## 逐项执行

1. 选取001中的实际 URL、平台问题样例和模板代表页。保留大小写、实体参数、原始地址与语言路径，不凭 canonical 合并资产。避免为测试凭空生成一批可能不存在的线上 URL。
2. 写入 `urls.json`。默认只含 URL；有可靠路由合同或业务策略时，再附 `policy_source`、`policy_at`、`entity_parameters`、`tracking_parameters`、`expected_entity`、`expected_role` 或 `preferred_canonical`。不要把经验猜测写成批准的策略。
3. 先读取已有证据并审查，再补 `pending-targets.csv` 中的目标、robots、跳转链和过期记录。001补采需有明确种子及请求预算，不自动扩到全站。
4. 对“去参数”“跨语言”“错误币种”“公开栏目落入收藏”等候选，实际打开源与目标，观察主体内容。区分直达、站内导航、返回与登录状态；不要点击交易、购买或账户操作。浏览器未稳定、仅出现占位或权限受阻时，留为未核验。
5. 将真实 DOM、页面实体/语言观察、客户端导航、平台 canonical 与内容对照按[输入合同](references/input-contract.md)保存。完整 DOM 和结构化文本摘录不同；无法导出完整 DOM 时，只记有来源的浏览器观察，不重建 HTML 冒充 DOM，不猜浏览器 HTTP 状态。
6. 执行独立命令；阅读逐 URL 结果与证据，对关键问题给出修改方向和复测步骤。必须区分已观察的声明冲突、HTTP 结果、业务政策冲突、语义待复核与证据缺口。

## 命令

```bash
python3 "<SKILL_DIR>/scripts/audit_canonical.py" --inventory "<INVENTORY_DATA>/inventory.sqlite" --urls "<WORK>/urls.json" --state "<STATE_DIR>" --output "<NEW_REPORT_DIR>"
```

默认建议状态目录 `<DATA_DIR>/<SITE_HOST>/canonical-routing`。每次用新报告目录；旧报告不覆盖，历史库不清空。

- `--url` 可重复，与 `--urls` JSON数组合并。
- `--manifest` 可替代 `--inventory`；`--supplement` 可重复加入实际浏览器、平台与语义证据。
- 默认 `--max-age-hours 168`；`--at` 可固定回放时点，否则用当前 UTC。
- `--max-graph-depth 30` 限制从库存补读 canonical/refresh 目标的轮数；不发网络请求。图谱评估本身最多30步，达到上限明确标缺口。
- `0` 表示所选证据范围的审查完成，仍可能有问题或未评估的语义；`2` 为有证据缺口的部分报告；`1` 为执行/输入错误。均不等于全站无问题。

## 解释结果

`report.json` 保存原始、HTTP、渲染和引擎观察，`relations.csv` 是关系图，`parameter-changes.csv` 列出参数变化，`pending-targets.csv` 列补采目标。`findings.csv` 和 `issue-history.json/csv` 保存当前发现与历史。

阅读[规则与限制](references/rules.md)，尤其避免：

- 将 canonical 声明当作 Google/Bing/Yandex 已采用的规范地址。
- 将 200 当作正文正确或内容等价。URL丢 currency 后返回200但项目加载失败，应核对内容与路由，不只检查状态码。
- 将标题里的 GOLDUSD 当作主体确实是黄金；应引用主体实体的实际观察。文章ID/slug冲突同样需要路由策略与主体证据。
- 自动把不同语言正文规范到英语，或把所有查询参数视为跟踪参数。
- 把 JavaScript 源码中的 location 字符串当作实际发生的跳转。
- 只改标题来掩盖数据/路由错配。

建议目标只在明确策略、对应当前页面哈希的等价性评审、目标响应及抓取/索引指令均支持时填入。否则留空并列出需核实的事实。语义证据仍需要审阅；哈希只能证明文件未变，不能证明判断一定正确。

问题ID按规则和源URL稳定生成，不同URL不因 canonical 相同而自动合并。跨周期更新同一问题，缺席不自动关闭；修复验收由017或明确复核流程完成。

用户需要飞书时使用可用文档工具发布并回读；本技能不假定凭证、不发送消息、不提交索引、不修改线上路由。

## 维护

v1.0.0。任何规则变化先写能复现缺陷的失败案例，再实现并回归：

```bash
python3 -m unittest discover -s "<SKILL_DIR>/tests" -v
```

安装后再跑测试并用真实证据验收。离线场景不能冒充后台或浏览器接入；不要把本次模板抽样扩写成全站检查完成。
