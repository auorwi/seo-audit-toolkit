# 采集顺序与 Bing 特有边界

选站后先读可见报告。Recommendations、Site Explorer、Sitemaps、URL Inspection、既有 Site Scan、Search Performance/提交历史按任务范围取用；能力清单不是本次全部已读声明。没有更新日期就保留null，不拿今天日期填进旧报告。

- Recommendations 的页面数、错误数、实例数分别记录；16.1K/4.8M仅为显示值，不擅自展开成精确整数。样例上限以当前界面为准，本轮已见提示最多50页；不是全站完整列表。
- Site Explorer保留当前筛选、选中的主机/文件夹和时间范围。目录中出现子域不证明其中所有URL均已索引。不要通过相加可能重叠的分类推导全站数量。相对路径缺少协议/主机证据时不能伪装成已取得精确URL。
- Bing Index、Live URL与Site Scan分开。URL Inspection没有明确device时写UNKNOWN；最后抓取为空、N/A或没有时区保持原文，不能猜日期。IsPage只描述返回信息的页类型，API HttpStatus=0不是HTTP 0错误或成功。
- 先读取平台的历史HTML/响应：可能只是301跳转短正文。标题/H1/描述等旧告警需与响应对象关联。Cookie/Authorization等凭据不保存到输入；可保留经过说明的非敏感摘录，不能称完整响应导出。
- 对相同URL记录当前 GET 状态、所有HTTP跳转、最终URL和正文hash；浏览器可补充渲染内容。普通HTTP/浏览器、Bingbot、实时诊断工具不是同一环境；“两种请求都403”仍需结合WAF/CDN日志判断影响范围。
- Site Scan只读已有扫描，保留名称、完成日期、页数、错误/警告。新扫描会消耗服务额度和触发抓取，本技能不自动启动。
- IndexNow未使用是发现/更新建议，不直接说明被禁止索引。提交接受/处理与索引结果分开；不要默认每个查询参数变体都应提交或收录。
- 平台严重度不代替根因分析：title长度、多个H1、缺少Meta Language等建议需要结合实际语义、HTML lang与业务用途。不要为金融行情页补造运费、退货或商品价格。

## API 与官方参考

2026-09-17核对官方文档：Bing首页明确 SOAP/POX 已计划于2026-08-31退役；旧方法页面仍带SOAP/POX示例。采集仅选择当前可用JSON/HTTP只读能力，不能按旧教程建立SOAP连接。源码解析支持GetUrlInfo、GetCrawlIssues、GetFeeds、GetQueryStats、GetPageStats；不负责请求、凭据、配额自动重试，也不假装这些方法覆盖所有UI字段。

GetCrawlIssues采用位标志；未知位保留为缺口。GetQueryStats/GetPageStats是顶部数据且文档描述按周更新，不保证全量/最终窗口。没有有效对比窗口就只报告已读数据，不能给缺失页面补0或把查询行总和当作站点总流量。

- [官方入口与退役说明](https://learn.microsoft.com/en-us/bingwebmaster/)
- [协议](https://learn.microsoft.com/en-us/bingwebmaster/api-protocols)
- [GetUrlInfo](https://learn.microsoft.com/en-us/dotnet/api/microsoft.bing.webmaster.api.interfaces.iwebmasterapi.geturlinfo?view=bing-webmaster-dotnet)
- [CrawlIssues位标志](https://learn.microsoft.com/en-us/dotnet/api/microsoft.bing.webmaster.api.interfaces.urlwithcrawlissues.crawlissues?view=bing-webmaster-dotnet)
- [GetCrawlIssues](https://learn.microsoft.com/en-us/dotnet/api/microsoft.bing.webmaster.api.interfaces.iwebmasterapi.getcrawlissues?view=bing-webmaster-dotnet)
- [GetFeeds](https://learn.microsoft.com/en-us/dotnet/api/microsoft.bing.webmaster.api.interfaces.iwebmasterapi.getfeeds?view=bing-webmaster-dotnet)
- [GetQueryStats](https://learn.microsoft.com/en-us/dotnet/api/microsoft.bing.webmaster.api.interfaces.iwebmasterapi.getquerystats?view=bing-webmaster-dotnet)
- [GetPageStats](https://learn.microsoft.com/en-us/dotnet/api/microsoft.bing.webmaster.api.interfaces.iwebmasterapi.getpagestats?view=bing-webmaster-dotnet)
- [URL Inspection说明](https://www.bing.com/webmasters/help/url-inspection-55a30305)
- [Site Scan说明](https://www.bing.com/webmasters/help/site-scan-623520c9)
