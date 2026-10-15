> Historical/opt-in BingX example. Apply to generic sites only after replacing URLs, selectors, and business assumptions with current evidence from the selected profile; never auto-import example evidence.

# 005 采集与输入合同

## 导航、范围和预算

`urls.json` 是非空数组，例如：

```json
[{"url":"https://bingx.com/en/launchpad/detail?currency=78","expected_entry_modes":["direct","internal","back"],"readiness":{"required_identity":"SOLV","max_wait_ms":30000,"min_stable_samples":2,"stable_window_ms":1000}}]
```

URLs必须来自实际观察。实体匹配默认忽略首尾空格和大小写；不是标题是否包含关键词的模糊匹配。每次导航有独立ID，每次交互后的采集阶段有独立phase_id；不能合并不同页面、设备、环境或阶段快照凑稳定次数。后台长连接不强制等network-idle。最大等待由Codex采集过程执行；分析器对输入时间和稳定样本做复核，本身不操纵浏览器、不主动等待。

`bindings.json` 用于把独立HTTP基线关联到审查场景：

```json
[{"url":"https://bingx.com/en/launchpad/detail?currency=78","entry_mode":"direct","navigation_id":"nav-1"}]
```

此关联只建立比较分组，不证明HTTP请求是这次浏览器导航。prepare脚本显式标记 independent_http，选最新尝试；不因最新超时而回退到旧成功，不用302/非HTML响应冒充页面正文，不重抓网络。

## Manifest与本地文件

```json
{"schema_version":1,"snapshots":[],"interactions":[],"gaps":[]}
```

每个snapshot的元信息：

- `id` 唯一、`url` 实际地址、`requested_url` 检查场景地址，二者允许因真实跳转不同。
- `stage`: initial / dom / interaction。
- `entry_mode`: direct / internal / back。
- `navigation_id`、`source`、`captured_at`（含时区ISO时间）必填。
- `kind`: initial_html / rendered_html / dom_fields。
- 可选 `phase_id`、`navigation_started_at`、`environment`对象、`http_status`（浏览器不知道就null）。实际导航开始时间未知时不要补猜。
- 初始HTML的 `baseline_relation`: same_navigation / independent_http / unspecified。same_navigation只能用于有实际响应—导航关联的证据。未提供视为unspecified。
- `evidence`: `{ "path":"snapshot.json", "sha256":"实际字节SHA256", "bytes":123 }`。

证据文件必须位于manifest同目录或子目录，含真实采集结果。哈希及字节数检查文件一致性，不为来源或语义背书。超过8MB、越界路径、篡改或缺失文件标缺口。报告/manifest不可包含密码、Cookie、令牌、账户信息。

initial_html读取原始响应；rendered_html仅用于实际完整DOM导出。两种HTML均不会执行JS，也不会凭HTML捏造实体身份、占位状态或浏览器报错。

dom_fields是JSON对象。以上元信息、可选阶段/环境/状态字段应同时写入文件和manifest，值完全一致。字段格式：

| 字段 | 类型 | 采集意义 |
|---|---|---|
| title | string | document.title |
| titles / descriptions / canonical | string数组 | 全部对应head节点，重复不能去掉；canonical解析为绝对URL |
| h1 | string数组 | 实际h1的文本，空节点保留 |
| main_text | string | 已确认主体范围的文本；不要拿导航/页脚补主体 |
| identity | string | 已确认实体节点/主体证据；缺失为unknown |
| placeholder_count | 非负整数 | 在明确主体范围内实际识别的占位；不是任意连字符计数的通用规则 |
| page_errors / console_errors | string数组 | 可见页面错误和控制台信息分开 |
| schema | object数组 | 每项raw、parsed、error；无效JSON保留错误 |
| links | object数组 | href、raw_href、text；纯按钮不编造href |
| visible_items | string数组 | 分页/筛选可见业务条目，注明提取键/范围 |
| page_indicator | string | 实际页码/游标 |
| document_ready_state | string | 辅助观察，不独立证明就绪 |
| network_idle | boolean | 可选，未知不填 |

`coverage` 为上述字段名到 complete / partial / unknown 的映射。未知不等于空数组；截断文本、限定节点子集或不一致主体边界为partial。compare只用双方complete字段；就绪判断可使用明确主体的局部实体信号，不能据此称全文已查。初始HTML只自动提取main/role=main；若DOM用自定义主体选择器，应把不可直接对比的main_text标partial/unknown或提供同范围真实提取，不把两种边界当作同一正文。

浏览器工具限制：先读工具文档/当前页面，再按已观察的DOM或可访问树操作；只读DOM取数，不读取隐藏应用状态或账户凭证。没有完整DOM导出时保存字段JSON，明确其为观察摘录。真实采集时间逐份记录，不能复制快照只改时间。保存截图/工具原始记录作为辅助证据时与结构化文件关联。

## 交互事件

id、url（检查场景）、kind、before_id、after_id、source、checked_at和evidence必填。证据JSON与manifest事件一致，文件里无需含自身evidence。

- kind只能paginate/filter/open_internal_link/back；其他类型标排除，不执行。
- paginate：before_page、after_page、before_items、after_items必须与相应快照一致。同地址数据发生变化是可分享路由待审；只有明确新鲜的policy_source、policy_at、pagination_requires_url_change:true才判策略冲突。它只说明观测到了数据变化，不等于完整稳定性验收。
- filter：before_items/after_items匹配实际观察。未见变化不称成功。
- open_internal_link/back：操作前记录expected_url、expected_identity。可来自实际链接、已经观察的路由、浏览历史；不从操作后的结果反推预期。
- 后续至少2份同阶段稳定快照用于内链/返回/筛选就绪；只有一次after或不符合实体仍保留缺口/差异。

分页尚无实际可操作样本时用fixture验证规则，并将真实交互覆盖写清，不能把内链验收冒充所有分页筛选均已验收。
