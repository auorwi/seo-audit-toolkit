# 规则与归属

仅从实际head提取title、meta name=description和keywords，保留重复节点、空内容、原始字符和源位置。body中的SVG title、script/style/template等不冒充主标题。HTMLParser是源提取工具，不模拟完整浏览器HTML5纠错或可见性；head不完整时不确认缺失标签。

- 缺失、空值、重复节点：分开记录。缺description是编辑/摘要优化项，不能解释成无法收录。
- 模板：{{...}}、${...}、%s、独立undefined/null以及配置的已知翻译key；英文buy模板的空in国家槽位为待审。其他语言的语法依赖Codex评审，不假装正则覆盖所有语言。
- 实体/国家/产品：仅基于配置的已验证事实。模板允许省略的字段不应配置为必需。
- 路由实体与实际实体不同、路由产品与正文产品不同：交004/012并拦截简单改写；未上架却有交易文案交012作状态与范围复核。
- 长度：记录字符数，title超过80或description超过220仅触发显示/简洁性提醒。这是可调产品规则的初始值，不是Google字数限制，也没有伪造像素宽度测量。真实搜索展示可能使用不同标题或摘要。
- keywords：只盘点既有值，不缺省生成任务。K主要用于主题与查询意图。
- 动态标题：不因为行情数值变化判错，但必须配置并验证币种/交易对/产品稳定字段；未知实体不推断。
- 聚类：对全部指定、有效且head完整的样本做Unicode NFKC、大小写及空白归一化的精确重复聚类，按html_lang分组。不是语义近似聚类。重复是候选，原始/渲染来源保留；参数/语言/规范关系未核实前不删除或合并页面。

稳定问题ID按URL+规则+字段生成；重复集群按字段+语言+归一化值生成，成员增减保留最新证据。值改变会得到新集群ID，因此不承诺自动追踪所有模板重构。重复同一运行幂等；本轮未见不自动关闭问题。路由/内容交接不在007冒充根因已修复。

模型局部评审不清空全部search_intent/language_and_wording待审范围。总报告退出2是正常的部分审查状态。自动检查、样本覆盖、一个正确草稿都不保证全站无SEO问题。

官方依据：[标题链接](https://developers.google.com/search/docs/appearance/title-link)、[摘要](https://developers.google.com/search/docs/appearance/snippet)、[元标签](https://developers.google.com/search/docs/crawling-indexing/special-tags)。2026-09-17读取；Google会自行生成搜索展示，keywords不用于其索引与排名。
