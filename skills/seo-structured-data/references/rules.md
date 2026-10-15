# 008 规则范围与结论边界

规则审阅日期2026-09-17。规则或引擎要求变化时先核对官方文档，再写失败测试和调整实现。

| 范围 | 实际检查 | 限制 |
|---|---|---|
| JSON-LD | script原文/位置、空/截断/非法JSON、重复键、数组/@graph/嵌套实体、ID引用、大小深度限制 | 不是完整JSON-LD扩展/推理器；复杂context、term alias和外部词汇不猜测 |
| Microdata/RDFa | 实际extruct独立运行两种语法，嵌套值、itemref、相对链接、空结果/失败区别 | RDFa库标注experimental；使用原生JSON路径，未生成源DOM XPath；RDFa不等于Schema专用数据，OG等外部词汇保留未审 |
| Schema词汇 | 官方快照类型/属性、继承domain | 开放世界模型；未知词汇/domain是待审，不是JSON错误；未实现完整range/所有子属性验证 |
| 价格评分 | 价格符号/分隔符/占位，数值边界、评分尺度和计数 | 合法0不是缺失；格式正常不证明价格或评分真实 |
| 购物/应用/面包屑 | 明确选用profile后的部分必需/推荐字段；多条面包屑分开，末项可无item | 不完整覆盖各富媒体全部规则；币种行情不自动套商品资格；不保证展示 |
| 实体图 | 同ID字段差异、重复brand候选、本地悬空引用候选、初始/渲染重复定义增加 | 合法ID引用不算重复；同ID互补声明合法，字段多值可能合法，冲突须语义评审；外部ID不能仅因本页无定义判坏 |
| 当前可见事实 | snapshot+SHA+script/path+原值+可见引文的字段核验、有限数字修正示例 | 引文/哈希绑定不是对任意人工判断正确性的证明，Codex需实际阅读 |
| 历史和引擎 | 原始证据、时间、当前同文档测试、历史复现/未复现/未验证 | 不自动关闭历史、不推断索引重抓，不把本地检查当RRT实测 |

浏览器采集追踪JSON-LD脚本、itemscope外层、typeof/vocab外层的稳定性；其他孤立RDFa属性也会由保存HTML交给extruct提取，但未专门作为稳定签名监测点。报告中的“提取完整”只表示这三种格式在该快照完成提取，不代表Schema语义通过。

HTML/DOM不同阶段价格变化属于观察，必须核对时间、实体和更新逻辑后归因。相同错误跨阶段或运行合并到稳定问题ID，保留全部evidence；模板级根因合并由后续报告技能处理。

官方依据：
- [Schema.org数据模型](https://schema.org/docs/datamodel.html)
- [price](https://schema.org/price)、[priceCurrency](https://schema.org/priceCurrency)：价格与货币分别表达；Schema允许加密货币代码，不能把Google某产品规则套到所有Schema。
- [Google结构化数据政策](https://developers.google.com/search/docs/appearance/structured-data/sd-policies)：有效标记不保证实际展示。
- [Product snippet](https://developers.google.com/search/docs/appearance/structured-data/product-snippet)：与merchant listing区分，Offer货币推荐、AggregateOffer货币必需。当前只检查三位大写格式，未核对完整ISO币种表。
- [Software app](https://developers.google.com/search/docs/appearance/structured-data/software-app)：免费应用可用价格0；评分/评论须有依据。
- [Review snippet](https://developers.google.com/search/docs/appearance/structured-data/review-snippet)：默认评分尺度及显式上下界。
- [Breadcrumb](https://developers.google.com/search/docs/appearance/structured-data/breadcrumb)：支持多条路径，末项item可省略。
- [extruct源码与说明](https://github.com/scrapinghub/extruct)：多语法提取器，不是Google校验器。
