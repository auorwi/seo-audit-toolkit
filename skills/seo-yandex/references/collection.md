> Historical/opt-in BingX example. Apply to generic sites only after replacing URLs, selectors, and business assumptions with current evidence from the selected profile; never auto-import example evidence.

# 平台采集与专业核查

## 浏览器

通过已授权账号选择精确 host，确认域名/协议。先读取摘要，再分别打开以下报告；菜单名称会变化，以当前可见控件为准：

- Website optimization → Diagnostics：PRESENT/ABSENT/UNDEFINED、严重度、Relevant since 与平台检查时间分别保存。Metrica、favicon 和子域建议不是统一的索引阻断。
- Indexing → Searchable pages → Excluded pages：原URL、关联目标、原因和最后访问日期；保留跳转、non-canonical、low-value、duplicate 的区别。UI展示的前若干行不是全量。
- Titles and descriptions：分别保存总页面数、百分比、分组原文、组数量和已取得成员。不能相加两种重复数量；不能按取到的三条成员冒称整组已验证。
- Sitemap files：区分手工与robots来源，可能指向同一文件；index文件的“Number of links in file”可能是子Sitemap数，不是已收录页数。折叠内容、未取得子文件均列覆盖缺口。
- Page check：选择准确URL与Mobile/Desktop，执行只读 Check；分开保存 Check results 和数据库版本，禁止点击 reindex。记录选中标签、新检查日期、HTTP码、元信息和实际JS执行原文。历史数据库时间无时区时只保留原文与明确日期，不推断小时。
- JavaScript page rendering：站点设置和某次实际执行结果不同；不为审查更改站点设置。未获得执行JS的引擎测试时明确未覆盖，普通浏览器DOM仅作补充。

浏览器不可导出时保存工具确实返回的原文摘录，描述为摘录；不要拼接HTML伪造完整DOM。账户信息、Cookie、Authorization、OAuth与带签名的账户链接不入证据文件。截图可补充布局，不能代替可核对原文。

## 本次实测形成的验收场景

- Lucia 国家路由、HTTP200且在搜索中，标题仍有空国家槽：007核验字段，不能改写成已经可以在 BingX 交易。
- EURCAD 原始HTML为通用TDK，浏览器变成BTCUSDT且地址不变：004/005核验实体与静默回退；只改title不够。
- 重复语言/文章路径出现错误页正文但HTTP200：004核验路由和状态；没有等价目标时不要统一跳首页。
- 这些是2026-09-17所选样例，不是永远成立的规则；每次重新观察。

## 只读 API

先通过官方授权取得用户可用权限；不要从浏览器提取凭据。仅保存脱敏 request URL、采集时间和响应JSON。API错误/权限失败是采集失败，不能变成网站故障。响应包含样例上限、缺项、未知枚举时保留限制。本版本只有离线合同测试，未完成 OAuth、配额和网络重试的真实验收。

官方资料（2026-09-17核对）：

- [Page check](https://www.yandex.com/support/webmaster/en/service/check-url)
- [Site diagnostics](https://yandex.com/dev/webmaster/doc/en/reference/host-diagnostics-get)
- [Crawl samples](https://yandex.com/dev/webmaster/doc/en/reference/hosts-indexing-samples)
- [Important URL state](https://yandex.com/dev/webmaster/doc/en/reference/host-id-important-urls)
- [Search events](https://yandex.com/dev/webmaster/doc/en/reference/hosts-search-events-samples)
- [Sitemap list](https://yandex.ru/dev/webmaster/doc/en/reference/host-sitemaps-get)

`indexing/samples`是抓取观察，不能从200推断在搜索中；search events是历史事件，不是当前状态。important-urls将indexing_status和search_status两套时间保留；target_url可能是规范、跳转或重复关联，不能一律叫canonical。
