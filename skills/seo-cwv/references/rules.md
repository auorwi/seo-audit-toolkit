# 判断与修复

真实用户CWV使用p75，良好上界：LCP 2500ms、INP 200ms、CLS 0.1；需改进上界分别4000ms、500ms、0.25。三者数据充足时均良好才完整通过。PSI在INP不足而LCP/CLS良好时允许特殊通过，本技能显示pass_inp_unavailable并保留覆盖不足，不声称三项均测得。

实验室默认工程预算为LCP 2500ms、CLS 0.1、TBT 300ms；用于本工具排查，TBT预算不是CWV门槛。导航Lighthouse缺真实用户INP，实验室分数90也不能推出用户体验全部良好。

| 问题证据 | 调查与修复 |
|---|---|
| LCP慢 | 对照实际LCP元素与资源、TTFB/加载等待/加载/渲染阶段。只有确认图片为LCP关键资源才考虑尺寸、优先级、预加载；文本/字体/渲染延迟不能一律压缩hero图片解决。 |
| 布局偏移 | 检查工具指出的节点、图片尺寸、异步内容插入和字体替换，并复现触发过程；不能把所有无宽高属性图片当已证实CLS根因。 |
| TBT或长任务 | 阅读任务时间与资源归属，确认哪些工作可推迟/拆分；不可据此计算INP值。真实交互需测输入延迟、处理与呈现阶段。 |
| 未使用JS/CSS | 单次入口未运行不等于全站无用；验证设备、路由、交互与覆盖后再移除。 |
| 缓存/资源体积 | 区分可版本化静态资源和动态行情/用户内容；不机械给动态响应长期缓存。 |
| 重复测量差异大 | 先看环境、负载、网络、最终URL与业务内容；保存所有成功/失败，不删除慢样本美化中位数。 |
| 字段/实验室相反 | 保留设备分布、URL/origin范围、窗口、远端/本机环境差异；不随意把其中一方判错。 |
| 发布后字段未改善 | 字段统计窗口包含历史体验；同条件实验室/交互复测和后续真实用户窗口分别跟踪。 |

每个审计项的estimated savings单独保留，可能重叠；不能直接求和保证总收益。不存在实际trace或源码时不假造函数级根因。旧PSI远端Lighthouse13.4.1/Chromium151与新本地LHCI12.6.1/Chrome153基线不可直接混算。

依据：[Web Vitals](https://web.dev/articles/vitals)、[PSI数据说明](https://developers.google.com/speed/docs/insights/v5/about)、[CrUX API](https://developer.chrome.com/docs/crux/api/)、[Lighthouse CI配置](https://github.com/GoogleChrome/lighthouse-ci/blob/main/docs/configuration.md)。
