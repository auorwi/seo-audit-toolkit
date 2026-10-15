---
name: seo-cwv
description: 专项核验 目标网站 移动与桌面的Core Web Vitals、Lighthouse重复测量、资源/节点诊断及性能回归，区分真实用户p75、实验室指标、数据缺口与测量环境。用于性能巡查和改版复测；不以总分、TBT或单次样本冒充真实用户CWV通过。
---

运行前设置 `SEO_SITE_PROFILE=/absolute/path/site.json`。使用 `seo.py init` 为目标站点创建显式配置；主机采用精确白名单，不自动扩展子域。默认使用通用网站规则；`business_profile: "bingx"` 为可选业务扩展，只有明确选择它才启用对应路由和市场参考逻辑。缺少 profile 时不进行线上采集。

默认交付本地报告或问题清单。只有用户明确要求外部发布并指定或确认目的地时，才调用相应飞书/外部工具写入；无需发布时不要求外部账户授权。所有输出、证据和状态库存放在技能目录之外，按站点隔离。示例、fixtures 和既有历史记录仅用于显式选择的离线演练，不自动导入真实报告。浏览器的通用就绪信号仅证明可见正文与有限稳定性，不证明业务实体正确；如提供身份/模板信号则保持这些更强要求。


# 011 · Core Web Vitals

独立性能专项。使用固定版本Lighthouse CI串行测量，Python聚合与Codex诊断；共享003证据/账本原语，不运行其他完整技能。

## 执行顺序

1. 明确URL、设备和模式。全面基线使用用户指定的当前网站 URL 清单，或从当前 profile 对应的最新资产清单中明确选择页面；逐项验证主机范围，不自行套用其他站点模板。移动/桌面各3次有效同环境测量；周查可明确缩小到变更/异常模板。所有失败与额外测量保留，不挑最好的一次。保留已约定的本轮范围，不静默缩减计划。

   [历史 BingX 8页样例](references/approved-sample-seed.json) 仅供用户明确选择的离线历史演练，标记为 historical_fixture / explicit_opt_in_only；不是默认基线、当前网站库存或线上证据，不自动导入或发起采集。
2. 读取可用CrUX/PSI真实用户数据。记录URL或origin、设备、p75、统计窗口、查询时间与可用性。origin不代替每页数据；缺API授权、配额错误和无样本保持未知。GSC分组数据需通过014来源保留分组口径，不能当独立URL CrUX值。
3. 固定Lighthouse/Chrome版本、设备/视口、节流、入口、登录与缓存条件；区别报告locale与实际页面/浏览器语言。使用独立浏览器和性能锁串行执行，不同时做全站抓取。每单元先检查主机负载：1分钟load/逻辑CPU超过2或数据缺失时保存collection_events并暂停，保留完整计划。此阈值是工程门禁，不是SEO标准；低于阈值也不证明绝无外部干扰。不关闭未知的用户进程。已采集高负载数据只作观察，不能采用为可靠回归基线。
4. 核对LHR实际落地URL、HTTP状态、runtimeError、节点与截图，确认测到的是目标业务页面。得分和200均不保证内容正确；错误实体、骨架屏、机器人验证页或加载失败不能作为目标业务健康结果。逐次查看截图后，将明确署名的复核JSON加入同目录新manifest的page_reviews，绑定run_id、LHR和截图SHA；不能仅按URL或分数批量填valid。业务不符会保留数值但排除目标基线，矛盾或不足的复核保持未知。原始采集manifest不覆盖。
5. 聚合同URL、设备和环境的全部有效样本，列中位数/最小/最大/样本数。LCP、CLS与TBT等实验室指标同真实用户数据分表；TBT/FID不填INP。导航Lighthouse不能证明交互INP，必要时补真实交互记录、trace或RUM。
6. 对异常逐项定位实际LCP元素、布局偏移节点、长任务或资源。工具估算可能重叠，不能累加承诺；零收益项不机械列优化任务。需要源码/trace才成立的原因写待验证，不能从资源名猜根因。
7. 与同环境且主机负载证据合格的历史报告比较。工具、浏览器、节流、设备或来源改变时保留不同基线。受污染数据不能混进新的干净基线；另建采集目录，旧证据仍归档。前后真实用户窗口可能重叠，部署后仍包含旧体验；不要把字段未立即改善判成修复失败。
8. 输出具体URL/设备、证据、工程预算与p75口径、修改对象、复测条件和覆盖缺口。同一状态目录保存稳定问题ID；本轮未见不关闭。需飞书时使用可用文档能力发布并回读；不修改生产、启用网站RUM脚本、发送消息或自动提交索引。

## 工具调用

```bash
python3 "<SKILL_DIR>/scripts/collect_lab.py" --urls-file "<WORK>/urls.json" --runtime "<LHCI_RUNTIME>" --chrome "<CHROME>" --output "<NEW_CAPTURE_DIR>" --lock "<DATA>/cwv/performance.lock"
python3 "<SKILL_DIR>/scripts/collect_field.py" --source crux_api --url "<PUBLIC_URL>" --device mobile --output "<NEW_FIELD_DIR>"
python3 "<SKILL_DIR>/scripts/audit_cwv.py" --manifest "<CAPTURE_DIR>/manifest.json" --supplement "<FIELD_DIR>/manifest.json" --state "<DATA>/cwv" --output "<NEW_REPORT_DIR>"
```

CrUX默认读取CRUX_API_KEY，PSI可使用PAGESPEED_API_KEY；只通过环境变量提供，勿把凭据写进命令、报告或共享文件。没有CrUX key时记录authorization_missing，不伪造API响应。PSI只有实际返回的字段才导入。

采集可选 `--device desktop`、`--plan-only`、`--resume`、`--budget-seconds`。`--resume`校验计划一致并跳过已留档单元；失败单元需要查看原始证据后制定补测，不能删除失败以凑够3次。配置完整说明见[运行方法](references/runtime.md)。

审查可设 `--baseline <PREVIOUS_REPORT_JSON>`、`--at`回放时间、`--max-age-hours`（默认168）。报告退出2表示缺口或待审，1为执行/输入错误；采集0只表示流程完成，还须审查有效次数与业务页面。

[证据输入](references/evidence.md) · [判断和修复](references/rules.md) · [运行方法与边界](references/runtime.md)
