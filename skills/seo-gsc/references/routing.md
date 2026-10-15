> Historical/opt-in BingX example. Apply to generic sites only after replacing URLs, selectors, and business assumptions with current evidence from the selected profile; never auto-import example evidence.

# 稳定原因与专业归属

先保留平台原文，再做语义映射；不把自由文本 coverageState 当成永远稳定的枚举。本表供读取者核对，不是按标签自动证明根因。

| reason_key / 报告 | 主责专业 | 需要补充的当前证据 |
|---|---|---|
| server_error / robots_blocked / noindex / not_found / access_denied | 003 抓取可用性 | GET、robots、索引指令、失败环境，必要时日志 |
| redirect / redirect_error / alternate_canonical / duplicate | 004 canonical 与路由 | 每跳响应、参数与最终实体/语言、规范声明 |
| google_canonical_disagreement / google_selected_other_url | 004 | Google 所选目标与当前声明分别验证 |
| crawled_not_indexed / soft_404 | 005 渲染，必要时 012 内容 | 原始/渲染主体及真实数据；未收录原因仍可能未知 |
| discovered_not_indexed | 009 站内链接 | 发现路径和重要性；不直接断言抓取预算不足 |
| rich_results | 008 结构化数据 | 类型、具体项目和字段、当前代码与 Google 解析 |
| cwv | 011 | 移动/桌面及现场窗口，不以一次 Lighthouse 代替 |
| sitemaps | 002 | 实际文件与独立发布清单；提交不是索引 |
| video_indexing | 013，必要时 008 | 主/辅视频用途、观看页条件、媒体和标记 |
| https | 003 | 报告实际样例、TLS/协议和路由；0 不证明全站证书正常 |
| manual_actions / security | 014 专项人工评估 | 具体告警、受影响范围、平台说明；不自动处置或申请复审 |

可用状态键 `available`、`no_issues_detected`、`validation_passed`、`valid`、`indexed` 只保留观察，不创建新的平台故障，也不关闭旧问题。`index_status_requires_review` 表示索引状态需要进一步核对，没有足够证据自动归因。

## BingX 已有线索如何使用

历史报告里出现的 5xx 与当前可访问差异、反馈参数 URL、旧语言跳转、Google canonical 差异、Product/Merchant/Breadcrumb 标记、CWV、辅助视频等，可以指导选样。但过去的数量、示例抓取时间、截图或修复建议不是这次平台事实；运行时重新读取。测试/服务子域的主动排除和辅助视频未索引须先确认业务目标。

修复建议必须落到证据支持的层级。例如“检查 CDN/源站日志”是排查方向，不能写成“已确认 CDN 配置错误”；浏览器没有重现重复标记，也不能覆盖 Google 当次真实解析结果。两边证据冲突就同时保留并报告差异。
