# 规则依据与可解释边界

核对日期：2026-09-16。

1. [Google robots 规范](https://developers.google.com/crawling/docs/robots-txt/robots-txt-spec)：origin 隔离、特定 UA、重复组、wildcard/end-anchor、最长匹配及 Allow 平局。Google 4xx（除 429）采用无规则限制模型；429/5xx 缺少缓存与持续时段证据时保留 unknown，不把“允许抓取模型”叫作 bot 实际访问。Google 的 500KiB 处理单独标注。
2. [RFC 9309](https://www.rfc-editor.org/rfc/rfc9309.html)：保留路径大小写，规范化非保留字符的百分号编码；保留编码斜杠的差异。URL fragment 不参与 HTTP 请求。
3. [Google meta 与 X-Robots-Tag](https://developers.google.com/search/docs/crawling-indexing/robots-meta-tag)：同时保留 HTML 和重复 HTTP 头，按 UA 作用域归并，更严格的规则生效。none 展开为 noindex/nofollow；indexifembedded 保留条件例外，不能抵消独立页面 noindex。Google 接受 body 中 robots meta；脚本注释和 template 内的字符串不当作页面指令。
4. [Bing 支持的 robots 指令](https://www.bing.com/webmasters/help/robots-meta-tags-and-attributes-that-bing-supports-5198d240)及[移除页面](https://www.bing.com/webmasters/help/how-to-permanently-remove-a-url-or-page-from-bing-or-copilot-37c07477)：generic/bingbot 与 HTTP noindex；必须可抓取才能读取指令。不能只设置 robots Disallow 就承诺移除索引。
5. [Yandex UA](https://yandex.com/support/webmaster/en/robot-workings/user-agent)、[robots 文件](https://www.yandex.com/support/webmaster/en/controlling-robot/robots-txt)：常规 YandexBot 优先自身组，再 Yandex，再通配组；独立 origin 仍需独立取证。特殊爬虫不在本版本模型内。

`unavailable_after` 日期保留原值与时区；Google 日期无效或当天仅有日期精度则无法确定。没有核实 Bing/Yandex 相同语义时，结果为 unknown + review。显式 body 内 meta 对这两个引擎也保留位置证据并标行为未核实，不直接复制 Google 判断。

Google 的 HTTP 错误处理不复制给 Bing/Yandex；其未被本模型实现的 robots 错误策略保持 unknown，建议对照各自后台实时检查。模型不代表官方解析器完全实现；没有平台请求、已验证爬虫日志、真实收录快照时，不推断真实爬虫可访问或已收录。

HTTP 返回 200 的错误页、JS 空壳、软 404、内容完整性、canonical 与实际搜索意图分别由 004/005/007/012 和对应平台专项继续核实。003 只报告手中证据能支持的索引指令与访问判断，不从正文关键词猜测网站故障。
