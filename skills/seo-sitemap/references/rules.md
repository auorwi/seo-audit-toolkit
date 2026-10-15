# 002 规则依据与判断边界

查阅日期：2026-09-16。实现是确定性检查和证据对账，不是搜索引擎模拟器，也不是全套 XML Schema 验证器。

| 检查 | 判断 |
|---|---|
| 基础 XML | 区分 index/urlset，校验 UTF-8、namespace、loc 数量、绝对 HTTP URL、转义与格式；拒绝 DTD |
| 文件上限 | 按未压缩正文 52,428,800 字节和 50,000 条检查；gzip 大小不能代替解压后大小 |
| 索引图 | 检查已知循环、索引嵌套、上层目录目标；未知子文件明确待取数 |
| 多文件重复 | 保存各来源；作为维护候选，不推断重复 URL 直接导致索引惩罚 |
| lastmod | 缺省是允许的；查无效/未来时间、重复字段；只有独立重要变更证据才能判断滞后 |
| 页面响应 | 404/410 为当前响应事实；是否移除仍附业务条件。访问限制/服务失败需复测 |
| noindex | generic 与引擎专用作用域分开；先确认是否为有意排除，不直接批量删除 |
| canonical | 不同目标、不同语言或缺失业务参数均先核验；声明不等于引擎选定规范页 |
| 错误正文 | 仅采纳显式、带时间和证据的内容评审；标题关键词不够 |
| 独立对账 | 同入口范围、独立预期、明确意图和文件读取范围分别记录；无依据不填全站分母 |

五类修复清单是建议差异，满足本阶段可审阅需求；首版不自动生成整站替换 XML，避免对未读部分、扩展标签或未知意图作破坏性改写。

News／image／video 等扩展节点保留在原证据中，基础条目计数不会把图片 URL 当页面。扩展自身全部业务约束不在此基础 XML 规则中，交由结构化数据／媒体专项。优先级和 changefreq 不被写成 Google 收录硬规则。

跨站主机先确认独立所有权和提交配置；普通 allowlist 不能代替该证明。示例中的 language 前缀仅用于定位，语言语义和 hreflang 全面检查交由 010。

官方来源：

- [Sitemap 协议](https://www.sitemaps.org/protocol.html)：文件格式、大小、数量、日期和 URL 约束。
- [Google 构建 Sitemap](https://developers.google.com/search/docs/crawling-indexing/sitemaps/build-sitemap)：规范 URL、lastmod 的重要变更、跨站提交。
- [Google 大型 Sitemap 与索引](https://developers.google.com/search/docs/crawling-indexing/sitemaps/large-sitemaps)：索引数量、同站和目录组织。
- [Search Console Sitemaps report](https://support.google.com/webmasters/answer/7451001?hl=en)：错误 HTML、无效日期、格式错误和明确不支持的索引嵌套。
