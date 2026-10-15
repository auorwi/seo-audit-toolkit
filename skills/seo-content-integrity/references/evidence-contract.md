# 输入与证据契约

manifest schema_version 为 1，包含 `scope`、`captures`、`reviews`、`actions`，可选 `references`。scope 条目是 `{url,kinds:[pair,forecast,calculator,claim]}`；只填写实际要执行的类型，不为提升覆盖率删除未执行项。其余数组为 `{path,bytes,sha256}` 文件引用，路径必须在 manifest 根目录内，每文件至多 8MB。

capture 保存 `snapshot_id,url,requested_url,captured_at,source,readiness,html,document_sha256,visible_main,fields`。fields 每字段包含 `selector,present,count,visible,text,value`。`value` 是实际输入属性，不能拿 HTML 初始 value 属性替代。私密账户及密码不在本技能采集范围。

review 包含 `reviewer,method,reviewed_at,snapshot_bindings,checks`。method 必须是 `semantic_review_of_bound_evidence`；snapshot_bindings 映射快照 ID 到 HTML SHA256。时间必须在引用捕获之后、审查时点之前。每项 check 含 `check_id,kind,url,payload,citations`；citation 是 `{snapshot_id,field,quote}`，quote 必须来自该快照唯一可见字段。语义判断属于具名复核，不宣称由哈希自动证明。

数值对象只能由 `content_integrity.numbers.parse_quantity(raw, decimal_mark='.', group_mark=',', exact=False)` 产生。原始数字必须在引文中，重解析结果必须一致。`exact=True` 只用于输入或已知精确值，不用它抹掉页面显示精度。

## payload 类型

- pair：`{left:observation,right:observation}`。observation 含 `asset_id,concept,unit,basis,period,scenario,temporal_kind,observed_at,data_at,number`。temporal_kind 为 live/static/same_snapshot_assertions；最后一种还需真实 `snapshot_id`。observed_at 必须来自引用的捕获时间。
- forecast：`{table:[observation+year],summary:observation+year}`。year 为整数，period 为相同年份字符串；使用静态“预测声明”，scenario 明确增长率等条件。不是把未来年份当捕获日期。
- calculator：`trial_id,action_id,asset_id,asset_unit,quote_unit,observed_at,direction,requested_input,actual_input,output,rate,rate_basis,input_unit,output_unit,interaction_status,readiness,rate_changed,before_evidence_id,after_evidence_id,rate_evidence_id`。数值字段均为解析对象，rate_basis 为 quote_per_asset。action 原始记录需要 before/after 快照与 SHA、实际请求/输入、方向和时间。默认六个用例是 1/10/1000×两个方向。
- claim：`kind,observed_at,reviewed:true`，加该类参数。direction 需 direction、change、change_kind；template_field 需 field、value、required；freshness 需 live_claim、data_at；numeric_display 需 raw、expected_numeric 和明确地区格式；lifecycle 需 page_state、reference_state、reference_scope 及市场/资产。same_page 可检查站内矛盾，official_api 缺少原始接口证据时被拒绝。official_api 还需 reference_id、reference_symbol、reference_market=spot、reference_at、reference_status=ok；引用实际 references 文件的 reference_id，状态必须与对应 symbol 的明确状态一致。

references 文件由 collect_reference.py 保存，含原始响应 body 字符串及实际 URL、method、status、captured_at、source。接口仅支持官方公开现货 `/openApi/spot/v1/common/symbols`。null/空 symbols 保持未知；不能扩展为合约、预市场或地区交易权限判断。

`check_id` 使用稳定的业务字段名，例如 `circulating-supply-body-vs-card`，不能包含每次运行日期、价格、随机快照 ID；预测检查另含固定目标年份和增长情景，换算另含数量/方向。问题身份结合 URL、类型、check_id；报告中的值和“候选→确认”状态变化不参与身份计算。共享账本保留 first_seen/last_seen，原运行回放不增加 sightings。

预测问题额外按同一 URL 的摘要目标年份聚合：不同增长情景仍逐项检查，重复复现只增加该问题的证据，不新增三条相同年份问题；出现有充分证据的确认时升级聚合结论，保留其它情景的不确定性。

## 采集配置

必须提供 `mainSelector,identitySelector,expectedIdentity,placeholderSelector,errorSelector,fieldSelectors`。`requiredFields` 对重要字段设置 `nonEmpty` 或 `pattern`，必须来自实际页面结构及应有业务内容。可配置 timeoutMs/stableWindowMs/sampleIntervalMs，动态标题使用 dynamicTitle。

`trials` 每项指定 `inputSelector,quantity,direction`，必要时提供该方向的 fieldSelectors。标准字段名 input/output/rate/input_unit/output_unit 用于操作核验；输出是 input 控件时保存当前 value。两方向不同控件应交换相应字段映射。只填写公开换算输入框，不通过登录、交易、表单提交完成测试。

`scenarioTrials` 为 `{inputSelector,growthPercent}` 数组，适用于实际页面声明的 -100% 至 1000% 预测输入。保留百分号格式并核对实际值。一次 fill 返回不等于生效：实际值不匹配时 action 为 failed，不允许把目标情景写进结果。仅填写预测 UI，不提交投资订单。

calculator_suites 分别输出 interaction_coverage_complete（实际输入覆盖）及 coverage_complete（有效汇率下可完成算术检查）。六次交互都完成但汇率未知时，前者可为 true，后者必须为 false。

抓取原始 DOM 并不自动生成可信语义；Codex 必须实际阅读字段原文，建立 review 后才能执行有结论的审查。没有 review 时报告保持未覆盖。
