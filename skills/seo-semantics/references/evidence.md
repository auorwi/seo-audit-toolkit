# 证据合同

所有时间为带时区ISO格式；保存真实来源、采集时间、URL、唯一快照ID。文件证据为 `{path,bytes,sha256}`，相对于manifest目录；禁止越界、缺失、大小或SHA不匹配，单文件上限8MiB。

## 浏览器配置

必填 `mainSelector, identitySelector, expectedIdentity, placeholderSelector, errorSelector`，均从实际页面观察。可选errorText仅匹配已观察的错误文案，避免大容器中的普通文字被误认为错误。默认timeoutMs30000、stableWindowMs1000、sampleIntervalMs250。必须主体有内容、实体符合预期、占位消失、关键字段跨至少2份样本稳定。行情数值变化不阻止实体判定。

输出dom.html、elements.json、axe.json、axe.capture.json、collection.json、manifest.json。DOM范围是当前document，未自动展开隐藏菜单、遍历iframe或shadow root。节点有截断标记；全DOM文件超过输入上限会被拒绝并报告缺口。采集器不宣称任意大型页面均可完整处理。

elements元数据：`url,snapshot_id,captured_at,source,document_sha256,representation=rendered_elements,readiness,scope=document,coverage,nodes`。

节点字段：`node_id,tag,selector,attributes,text,accessible_name,visibility,parent_id,ancestor_tags,snippet`。visibility来自实际样式/矩形；display:contents等无法确认时unknown。aria-hidden与视觉隐藏分开。采集器不自行模拟可访问名称算法，accessible_name为null；实际名称相关检查由axe执行，不能据null判空。

## manifest v1

根包含 `schema_version:1,captures:[],tool_reports:[]`。

capture行：kind为initial_html或rendered_elements，外层重复 `url,snapshot_id,captured_at,source`，evidence指向实际HTML或元素JSON。rendered_elements另有document_evidence指向其真实DOM HTML，哈希必须等于元素JSON document_sha256；外层不能篡改内层状态。

tool_report行：`tool,url,capture_id,checked_at,evidence,document_evidence`；evidence指向检查记录JSON，document_evidence指向被检查的实际文件。

检查记录：`tool=nu|axe,url,checked_at,source,capture_id,checker_version,state=completed,representation,document_sha256,input_sha256,payload`。axe另需readiness=ready；若有after_sha256必须与输入SHA一致。payload是原生Nu/axe结果，不是自己拼出的通过标记。

Nu针对initial_html；axe针对rendered_dom。Nu CLI即使退出1，只要返回有效文档错误JSON仍是有效检查；执行失败、超时、无效JSON则是证据缺口。重新运行Nu不会刷新原始HTML采集时间。

## Codex语义评审

另存复制的elements文件，添加semantic_reviews数组，重新计算其文件proof，并保留原始文件引用。每条：`snapshot_id,document_sha256,source,checked_at,topic,status,nodes,quotes,reason,recommendation,retest`。

topic限heading_topic_hierarchy / list_and_table_purpose / link_and_button_purpose。status为needs_change、looks_reasonable或unknown。nodes为实际node_id数组，quotes为node_id到该节点实际原文的映射。绑定旧快照、错误SHA、引文不符、节点缺失均不能形成确认发现。

用途标注purposes可用于区分真正导航与业务按钮；同样绑定快照、SHA、节点、来源和时间，具体字段以tests/test_rules.py覆盖的合同为准。不要仅因button没有href就判为爬虫问题。

source HTML解析器只提供源元素、属性、文本和源位置，不模拟完整HTML5树修复或浏览器可见性；Nu与真实浏览器各负责对应判断。
