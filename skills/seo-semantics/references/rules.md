# 规则、归属与验收

- Nu：HTML规范错误/警告/信息分别保留；重复相同信息按URL合并，所有源位置留在证据数组。不是搜索排名惩罚清单。
- axe：violations中按WCAG与best-practice分类；incomplete始终待人工确认。原生nested target保留iframe/shadow定位含义，不展平成普通selector。passes只说明这些自动规则通过。
- 自定义：主内容landmark、可见空标题、标题跳级、导航命名、列表层级、表格用途、真实链接href、按钮/表单/iframe名称。多H1不判错；隐藏副本不当可见重复；ARIA结构和原生结构都考虑；未知可见性/名称归缺口。
- 模型：标题和正文是否匹配、内容是否应为列表/表格、交互是否应为链接/按钮。必须真实元素引文；结果单列model_review，不冒充校验器或搜索引擎结论。
- 图片：alt为空先判断装饰/信息性；媒体结果交013。006保留交接清单，不在自己账本重复登记。

问题键由006+URL+规则+稳定定位/消息生成。Nu重排但消息相同不重复登记；元素selector变化可能产生新的定位记录，不能保证所有重构都自动合并同一业务问题。重复同一run幂等；不同周期更新sightings/last_seen；消失或缺证据不会自动标记解决。最终复测由017处理。

最新失败不能回退使用旧成功；原始文档过期不能靠新检查时间“续期”。所有报告说明本轮范围和未检查项。局部model review仅增加reviewed_topics，不证明全页全部同主题已审完，因此pending_reviews仍保留全页待审。

测试验收覆盖原生报告分类、坏文件/哈希/时间/版本、DOM状态、合法反例、Nu失败、CLI、历史、输出转义、报告分组和真实浏览器。现场验收是英文桌面未登录SOLV详情一页；不代表全语言、全站或搜索引擎实际收录。

参考：[Google JavaScript SEO](https://developers.google.com/search/docs/crawling-indexing/javascript/javascript-seo-basics)、[Nu](https://github.com/validator/validator)、[axe-core](https://github.com/dequelabs/axe-core)。
