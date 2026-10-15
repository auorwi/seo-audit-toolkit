> Historical/opt-in BingX example. Apply to generic sites only after replacing URLs, selectors, and business assumptions with current evidence from the selected profile; never auto-import example evidence.

# 输入与输出合同

## URL、策略与取数

`urls.json` 是 URL 字符串或对象数组。默认没有索引/路由业务判断：

```json
[{"url":"https://bingx.com/en/launchpad/detail?currency=78"}]
```

可选策略字段：`policy_source`、带时区的 `policy_at`、`entity_parameters`/`tracking_parameters`（参数名称数组）、`expected_entity`（业务实体标识）、`expected_role`（例如 public）、`preferred_canonical`（明确的拟采用URL）。缺少来源或策略超过 freshness 窗口则不作为判断依据。

查询参数保留重复值、空值和大小写；不同值不合并。路径语言只是线索，不替代正文语言证据。普通 fragment 不作为单独 HTTP 资源，但 canonical 中出现 fragment 会单独提示。

001 输入桥只读访问库存和本地证据；先取源 URL/robots/HTTP 链，再按声明补读已在库中的 canonical、refresh 目标。不会在发现外站声明时自动访问外站。目标缺失留在待采列表。

## 共享 manifest

`schema_version:1`；`records` 和 `rendered` 沿用003合同：真实 URL、整数 HTTP 状态或 null、带时区时间、headers键值对列表，以及 `evidence:{path,sha256,bytes}`。路径在manifest目录内，哈希/大小必须匹配。

新证据包含 `captured_header_names`，例如实际采集器允许保留的 `link`、`refresh`、`x-robots-tag`、`content-type` 等名称。这说明采集覆盖哪些字段，不能事后补写给旧文件伪装完整。没有 Link/Refresh 采集策略的旧证据标记 gap，即使 HTML 中已找到 canonical。

`rendered` 为实际完整 DOM，附 `mode:"rendered"`。没有确切HTTP状态时不猜200；结构化DOM字段摘录不能填进body当完整HTML。

## 语义、导航及平台补充

以下数组可以与 records/rendered 同在manifest中，也可以由 `--supplement` 加入。所有条目需 `source`、`checked_at`、本地 `evidence`。证据指向真实工具输出或明确撰写的评审记录；无需下载或保存登录凭证。

### facts

字段：`url`、`entity`/`language`/`role` 中至少一项、`quote`、`selector`、来源/时间/证据。quote必须实际出现在已验证的证据文本内，selector说明观察位置。实体及语言由实际页面语义评审产生，不根据URL猜测。只验证哈希与引文匹配，不自动证明selector或语义判断正确；报告分类为 evidence_backed_review。

证据可以是实际DOM，也可以是明确标注为文本摘录的浏览器观察JSON。对于摘录，记录未取得的HTTP状态和未导出的完整DOM，不能宣称完成渲染快照解析。建议引用项目详情/主内容，不用导航中的 BTC 作为主体币种依据。

### navigation

字段：`from_url`、`to_url`、`entry_mode:direct|internal|back|other`、来源/时间/证据。证据文件为实际已记录的结构化导航JSON，其中 from_url/to_url/entry_mode/checked_at 必须与manifest一致。仅阅读脚本源码不生成此项。

### equivalences

字段：`source_url`、`target_url`、`result:equivalent|different|unknown`、`source_sha256`、`target_sha256`、来源/时间/证据。证据JSON与这些字段及时间一致，并附语义评审理由、主体引文和实际浏览器证据引用。

审查时同时核对两侧当前HTTP正文哈希；任一变化后旧评审不复用。动态接口内容可能在HTML未变化时改变，因此哈希不是动态内容长期稳定的保证，应定期重看页面，必要时缩短 freshness 窗口。不得只因为HTML壳相同就设 equivalent。

### engine_observations

字段：`url`、`canonical`、`engine`、`kind`（例如 index_snapshot）、来源/时间/证据。保留平台快照与当下声明的时间差；普通抓取器结果不能标成平台canonical。脚本记录差异，不因此推定搜索引擎当前一定采用该历史值。

## 输出与去重

- report.md/json、rows.csv：逐源URL的HTTP链、声明、目标检查、参数变化、内容等价性评审及建议。
- relations.csv：canonical（raw/rendered）、HTTP redirect、refresh declaration、实际client navigation分别保存。
- parameter-changes.csv：变更参数及来源/目标所有值；类别为 entity_by_policy、tracking_by_policy 或 unknown。
- pending-targets.csv：缺失/失败/过期的目标与robots补采清单；其他证据缺口见findings/input_gaps。
- findings.csv、issue-history.json/csv：稳定ID、分类、证据、建议和首次/最后发现；没有复现不自动关闭。

独立状态库 `canonical-routing/issues.sqlite` 复用003已验证的原子去重账本。run ID 的内部前缀可能为 crawl-run；它只标识运行，不意味着调用了003整套审查。不同技能的状态目录和规则ID分别保存。
