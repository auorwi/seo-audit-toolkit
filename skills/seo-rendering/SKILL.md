---
name: seo-rendering
description: 专项核验 目标网站 初始HTML、稳定浏览器DOM、直达/站内进入/返回及公开分页筛选后的内容差异，保留真实证据、覆盖缺口和问题历史。用于JavaScript渲染、旧实体残留和元信息更新问题；不把HTTP成功或点击成功当作渲染正常。
---

运行前设置 `SEO_SITE_PROFILE=/absolute/path/site.json`。使用 `seo.py init` 为目标站点创建显式配置；主机采用精确白名单，不自动扩展子域。默认使用通用网站规则；`business_profile: "bingx"` 为可选业务扩展，只有明确选择它才启用对应路由和市场参考逻辑。缺少 profile 时不进行线上采集。

默认交付本地报告或问题清单。只有用户明确要求外部发布并指定或确认目的地时，才调用相应飞书/外部工具写入；无需发布时不要求外部账户授权。所有输出、证据和状态库存放在技能目录之外，按站点隔离。示例、fixtures 和既有历史记录仅用于显式选择的离线演练，不自动导入真实报告。浏览器的通用就绪信号仅证明可见正文与有限稳定性，不证明业务实体正确；如提供身份/模板信号则保持这些更强要求。


# 005 · JavaScript 渲染与交互一致性

Python 3.10+ 标准库。依赖同级 `seo-crawlability` v1.0.1+ 和 `seo-canonical-routing` v1.0.0+ 的已验证证据/解析/历史原语，不启动它们的完整审查。001 v1.0.3+ 可提供独立HTTP基线。状态和采集数据放在技能目录以外。

## 执行

1. 从001资产、站长平台样例或用户清单选择实际URL；同模板抽样，保留实体参数和语言。写 `urls.json`，列出要查的直达、站内进入、返回路径。默认三条路径都检查；用户只要部分时可显式缩小范围，报告保留范围。
2. 阅读[采集与输入合同](references/capture-contract.md)。打开真实公开页面，确认主体、实体、占位、错误提示的DOM选择器；按观察采集字段，不凭模板猜测。记录浏览器、设备、语言、进入方式、时间与导航/阶段ID。完整DOM导出不可用时保存结构化字段快照及采集范围，不重造HTML。
3. 从开始观察到预算上限采集少量间隔快照。检查主体有内容、实体符合预期、占位消失、关键字段稳定；默认至少2份、跨度至少1秒、最多等待30秒。行情数值波动不阻止实体稳定判定。网络空闲、document.readyState或控制台警告本身都不证明页面成功/失败。预算到期保留未知及未满足条件，不无限等待。
4. 逐条完成公开内链、返回、分页或筛选。操作前记录目标URL/实体或页码/条目；操作后核对实际URL、数据、title、canonical、H1、schema、链接，并采稳定快照。只允许公开阅读操作；不点击交易、下单、充值、授权或账户修改。登录或权限不足时保留缺口并移交用户。
5. 如已有同次导航原始响应，保留其实际导航来源。否则使用 `prepare_baseline.py` 导入001独立HTTP结果；此类基线不是浏览器同次请求，差异不直接证明JS导致。保留环境、时效和选择器差异。
6. 执行独立审查，阅读覆盖表、变化和交互结果，给关键问题写具体修复方向和复测步骤。区分正常加载补全、页面可见错误、进入路径差异、业务策略候选及证据缺口。canonical目标语义交给004，标签规范交给006，标题意图交给007；不因此隐式跑其他完整审查。

## 命令

可选准备HTTP基线（不联网、不改001库存）：

```bash
python3 "<SKILL_DIR>/scripts/prepare_baseline.py" --inventory "<DATA>/update-url/inventory.sqlite" --bindings "<WORK>/bindings.json" --output "<NEW_BASELINE_DIR>"
```

实际审查：

```bash
python3 "<SKILL_DIR>/scripts/audit_rendering.py" --manifest "<CAPTURE_DIR>/manifest.json" --supplement "<NEW_BASELINE_DIR>/manifest.json" --urls "<WORK>/urls.json" --state "<DATA>/rendering" --output "<NEW_REPORT_DIR>"
```

- 没有HTTP基线时省略 `--supplement`，照常产出带缺口的报告；不编造初始HTML。
- `--supplement`、`--url` 可重复；`--urls` 为数组。明确路径范围的配置优先用文件。
- 默认时效168小时，`--max-age-hours` 可调整，`--at` 仅用于指定回放时点；常规运行用真实当前UTC。
- 每次使用新输出目录；历史库不清空。退出0为指定证据范围执行完毕，2为带缺口的部分报告，1为输入/执行错误。都不代表全站无问题。

`report.md/json`、`coverage.csv`、`changes.csv`、`interactions.csv`、`findings.csv` 和 `issue-history.json/csv` 同时交付。问题ID稳定，重复运行不新增重复问题；本轮未见不自动关闭旧问题。规则及限制见[规则说明](references/rules.md)。

需要飞书时使用当前可用飞书文档能力发布并回读；此技能不假设凭证、不发消息、不提交索引或改线上配置。

## 维护

v1.0.0。新行为先写失败案例，再实现和回归；真实验收与离线fixture分开。

```bash
python3 -m unittest discover -s "<SKILL_DIR>/tests" -v
```

安装后重跑测试和真实证据报告。不能把模板抽样、独立HTTP响应或本地浏览器结果扩写为全站、搜索引擎实际渲染或收录验证。
