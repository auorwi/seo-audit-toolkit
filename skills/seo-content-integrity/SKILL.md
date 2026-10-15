---
name: seo-content-integrity
description: 专项核验 目标网站 页面数字、字段语义、预测年份、换算器交互及状态文案的一致性，以实际页面与绑定原文证据生成修复清单和稳定问题历史。用于行情字段矛盾、预测表文错位、换算精度或模板残留排查；不把自洽当作市场价格真实，不预测涨跌，不代替完整 SEO 审核。
---

运行前设置 `SEO_SITE_PROFILE=/absolute/path/site.json`。使用 `seo.py init` 为目标站点创建显式配置；主机采用精确白名单，不自动扩展子域。默认使用通用网站规则；`business_profile: "bingx"` 为可选业务扩展，只有明确选择它才启用对应路由和市场参考逻辑。缺少 profile 时不进行线上采集。

默认交付本地报告或问题清单。只有用户明确要求外部发布并指定或确认目的地时，才调用相应飞书/外部工具写入；无需发布时不要求外部账户授权。所有输出、证据和状态库存放在技能目录之外，按站点隔离。示例、fixtures 和既有历史记录仅用于显式选择的离线演练，不自动导入真实报告。浏览器的通用就绪信号仅证明可见正文与有限稳定性，不证明业务实体正确；如提供身份/模板信号则保持这些更强要求。


# 012 内容与数据一致性

按用户指定 URL 或既有 001 资产清单执行本专项。先写清本轮 URL、资产、语种、检查项和采样矩阵；不展开总入口，也不暗中把几页样本等同全站。无需为已授权的公开页面读取重复询问许可。

本技能由 Codex 完成页面识别与具名语义复核，Python 负责可重复计算、证据校验、问题身份和报告。必须使用实际页面证据；旧报告仅作待复测线索。遇到页面或接口不可用，输出缺口并继续独立检查。

## 执行顺序

1. 查找已有清单及历史，确认原始 URL、币种实体、页面模板、语言和业务市场。保留参数及真实请求 URL；不自行合并不同币种或市场。
2. 读取页面实际 DOM，确认主体、唯一实体标题、loading/error 与业务字段选择器。使用已有配置前核对选择器是否仍唯一、可见；错误配置不能成为网站问题。字段缺失、字段空、加载中、HTTP/浏览器失败分开记录。
3. 运行 `scripts/collect_page.mjs`，保存同一次 DOM 读取的 HTML、可见字段、输入当前值、时间、哈希和实际最终 URL。设置 `requiredFields`，重要表格/价格未就绪时等待到预算耗尽并保留未知。此采集无账户登录，不使用用户个人 Chrome 配置。
4. 对计算器真正填写 1、10、1000，并覆盖资产→计价币和计价币→资产。使用当前页面观察到的两个输入控件和单位；保留 before/after 与实际 action。仅填写公开计算器，不点击买入、登录或提交。若页面只有一个方向或缺有效汇率，不能宣称六个算术用例通过。
5. 具名复核字段语义，建立 `references/evidence-contract.md` 的 review。引用实际快照里的字段原文；每个数值保留 raw 及地区格式，由 `parse_quantity` 解析，禁止手写 value/quantum。数据时间未知不使用抓取时间冒充。预测表与摘要绑定年份、增长情景和相同资产/单位；`scenarioTrials` 可实际填写 1%、2%、5%，必须检查 applied_input 和后续表文是否对应新情景。
6. 运行 `scripts/audit_content.py`。查看每项结果、缺口、建议和复测条件；必要时补取证据。不能通过修改规则、时间、原文或哈希让真实失败“通过”。
7. 输出 Markdown/JSON/CSV 与共享持久问题历史。每轮用新输出目录，复用 state 目录。报告明确本轮覆盖范围、候选与确认、未执行项；同一问题更新观察历史，不重复添加，不因未复现自动关闭。

## 可执行方式

Python 仅标准库。依赖同级已安装 `seo-crawlability` 的证据/时间/账本工具及 `seo-tdk` 的浏览器就绪采集原语；不会执行它们的完整审查。浏览器依赖已有 `playwright-core` 运行环境及隔离 Chrome。先确认实际路径，不在文档中假定全新机器已安装。

```bash
node scripts/collect_page.mjs --url 'https://example.com/products/example' \
  --config /absolute/path/observed-template.json \
  --runtime /absolute/path/playwright-runtime \
  --browser-executable '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' \
  --output /absolute/path/new-capture

python3 scripts/audit_content.py \
  --manifest /absolute/path/reviewed/manifest.json \
  --state /absolute/path/persistent-state \
  --output /absolute/path/new-report

python3 scripts/collect_reference.py --symbol BTC-USDT \
  --output /absolute/path/new-public-spot-reference
```

`--at` 仅用于明确标记的历史证据回放，不能把历史回放当作今天的新核验。默认新鲜度 24 小时，`--max-age-hours` 可显式调整。退出码 0 表示声明范围完成，2 表示有未核验/证据缺口，1 表示输入或执行错误；0 不表示页面零问题。

## 判定规则

- 比较前对齐资产、概念、单位、市场/价格基准、期间和情景。流通量/总量/最大供应量、USD/USDT、现货价/标记价不是同一字段。
- Decimal 保留小数、极小值和 K/M/B 精度。缺失值不转 0；显示精度区间只用于四舍五入兼容判断，不证明原始真实值相等。两个比较数值的区间仅在边界相接时列待复核，不直接判相同。
- 跨快照实时数据须有有效且相近的数据时点。同一次页面中的两条声明可使用 `same_snapshot_assertions`，其结论只表示页面内部表达不一致，不能判定哪一个是实时正确值。
- 预测年份按年份键匹配；摘要数值恰好对应别年但目标年份缺失时，只列候选。不同增长情景不能直接对比，不评价未来收益。
- 换算器对比其自己声明的有效汇率。汇率为 0、缺失、切换中或未知时不进行除法、不捏造真实市场价。`E` 等非法数值显示可单独做具名文案/数值格式检查。
- 状态判断限定同一业务市场。按钮不是上架证明。`collect_reference.py` 只请求一次官方公开现货 symbols GET，无密钥、不访问账户/交易。将实际响应 proof 加入 manifest.references 后，才允许验证 `official_api` 状态断言；缺少原始 HTTP 证据时拒绝入账。空数组/null、接口错误或不同市场都不是下架证明。请求至少间隔一秒，遇到限流保留结果，不批量重试。
- 原因分“可复现事实 / 可能原因 / 尚需代码或数据源确认”。不由两段冲突文案直接断定具体后端字段写错。

## 交付与验证

运行 `python3 -m unittest discover -s tests -p 'test_*.py'`。真实 Chrome 的受控交互测试在 `tests/browser_integration.py`，需要 `SEMANTICS_RUNTIME` 与 `SEMANTICS_CHROME`。固定测试页面不是 目标网站 线上证据。安装后使用同一证据/时点回放并比对报告，同时保留实际线上抽样与受阻项目。

详见 [证据格式](references/evidence-contract.md)、[复核和修复方法](references/review-playbook.md)。
