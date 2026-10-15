# 规则与修复方向

| 证据 | 判断与修复 |
|---|---|
| 未支持的hreflang代码 | Google语言使用ISO639-1；地区使用ISO3166-1 alpha2，允许脚本。es-419虽是BCP47注册形式，Google当前指南不支持；en-UK/EU/UN不当作有效地区。修成真实受众对应值，不能机械把路由名复制到hreflang。 |
| 相同locale指向不同目标 | 保留HTML/HTTP/Sitemap和原始/渲染/入口差异，找到生成来源，统一到同实体、同语言的正确目标；一致的多渠道不算重复故障。 |
| 相对URL、片段、错误位置 | hreflang需要完整HTTP(S)URL，HTML应在head且不能混带媒体替代属性。保留非法声明，不把解析后的绝对URL当原始声明合规。跨域替代URL本身允许。 |
| 自关联/返回关联未观察 | 先补采目标和实际使用渠道，再修已确认存在的语言组；不虚构未发布翻译，局部缺返回不推断全组必然全部失效。x-default有适用场景，但缺少不自动判故障。 |
| 跳转或HTTP异常目标 | 验证最终状态、语言、实体；确认等价后指向稳定落地页。403/429先排访问条件，不判永久删除；200再查正文。 |
| html lang与正文不同 | html lang提供页面语言语义，但Google主要根据正文判断语言；修实际语言声明，不能仅改lang掩盖未翻译正文。地区差异不等于正文语种不同；明确脚本差异另列。 |
| Schema inLanguage与正文不同 | 先核对Schema实体范围是否描述该正文；引用/嵌入材料可能允许不同语言。确认同一正文后同步模板字段，复杂类型/图关系转008。 |
| 翻译正文canonical到其他语言 | 成对核对主体实体与实质翻译，确认独立可索引翻译策略后通常给各语言自canonical并建立hreflang；同语言地区重复版本按策略处理。只发现声明，不能推断Google已采用。 |
| 语言切换丢实体/错正文语言 | 修语言路由映射保留slug、参数及实体；无对应翻译可明确回退，不能伪装成功。加载中、失败与已确认实体变化分开。 |
| 本地化必填业务字段缺失 | 对照明确业务要求和实际可见控件，区分地区政策、产品差异与渲染故障；不擅自绕过地区限制。 |

实际验收回归线索：法语Zcash快讯法语正文、英文canonical及Schema inLanguage=en；009英文列表的无语言前缀分页href独立打开后302到繁体页。环境是隔离浏览器、本地出口、未登录；不扩大成全球全部用户结果。法语活动印尼语正文、日语/俄语购买页国家字段等旧线索须重新采集，不能仅凭历史报告声称本轮复现。

BCP47检查器是保守子集：普通language/script/region查IANA注册表，私用、变体、扩展和grandfathered交review，不声称完成全部BCP47语法验证。正文语言是模型/人工引文复核，不提供机器翻译质量、法律或投资内容正确性的认证。

来源：[Google本地化版本](https://developers.google.com/search/docs/specialty/international/localized-versions)、[多地区网站](https://developers.google.com/search/docs/specialty/international/managing-multi-regional-sites)。
