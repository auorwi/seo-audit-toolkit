# 规则、建议与边界

核对日期：2026-09-17（Asia/Singapore）。

- [Google canonical 指南](https://developers.google.com/search/docs/crawling-indexing/consolidate-duplicate-urls)：canonical是信号；HTML、HTTP及其他声明应一致；Google仅采用head内的HTML声明。带hreflang/lang/media/type的alternate式canonical不用于该规范化。缺少canonical不自动等于SEO错误。
- [Google重定向](https://developers.google.com/search/docs/crawling-indexing/301-redirects)：HTTP、refresh与JavaScript跳转是不同证据。refresh=0及延迟refresh的提示强度不同；解析声明不等于已执行浏览器跳转。

保留HTTP Link列表的多个头、URI里的逗号、引号参数和关系token。HTML相对声明按实际head base解析，HTTP Link不套用HTML base。重复同目标是重复声明提醒，不等于多个目标冲突。自指canonical不是循环。图谱有30步边界，未取得节点及超限保持待查。

跨语言路径只出candidate；有实际正文语言证据才出语言差异评审。同样，路由实体策略与主体实体观察相矛盾时，应查路由/接口/默认回退，不只修改title。无法证明正确替代页时不发明修复目标。

目标200、robots允许、未观察到noindex，依然不能证明内容等价或已收录。Google/Bing/Yandex的目标索引指令检查由003规则原语提供；未知引擎特殊行为保持unknown。

最小修复闭环：源URL和对照目标取证 → 确认应保留的实体、语言和参数 → 选择经核实的稳定目标 → 修改路由/声明的建议 → 复测直达、站内进入及返回。修复建议不自动发布，不自动提交索引。
