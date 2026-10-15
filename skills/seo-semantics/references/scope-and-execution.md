> Historical/opt-in BingX example. Apply to generic sites only after replacing URLs, selectors, and business assumptions with current evidence from the selected profile; never auto-import example evidence.

# 范围清单与执行

使用真实用户清单或001导出，不按技能样例数量重构清单。JSON可为URL数组或含 `url,id,page_type,locale,required_tools` 的对象数组；CSV至少有url列。业务查询参数、路径大小写与查询顺序保留。`all` 不接受子集筛选，技术文件按 `kind != page` 显式排除并列在预览中；未知或不支持的URL报错，先处理来源问题，不能静默丢弃。

已有完整清单且用户说“全量”，直接使用该清单。多个候选来源无法确定时，只询问缺失范围信息，不发网络请求。旧样例含候选子域/技术文件时先核对001分类与授权范围；把不检查的条目及原因完整列出。允许主机来自本轮显式 profile 的 allowed_hosts；本技能采集器不自动扩到其它子域。

```bash
python3 "<SKILL_DIR>/scripts/plan_scope.py" --mode single --url "<ACTUAL_URL>" --output "<WORK>/scope"
python3 "<SKILL_DIR>/scripts/plan_scope.py" --mode subset --input "<ACTUAL_LIST.json>" --id "<ACTUAL_ID>" --output "<WORK>/scope"
python3 "<SKILL_DIR>/scripts/plan_scope.py" --mode all --input "<ACTUAL_LIST.json>" --output "<WORK>/scope"
```

`--url`、`--id`可重复。读取scope-preview.md与scope.csv，先给用户展示具体清单和数量，然后才开始采集。长清单可以完整文件形式展示，但不能只说“检查100多个页面”而不提供逐页清单。scope_id是清单校验值，不是用户批准凭证。

每页单独配置实际就绪信号、单独输出新目录，依次或按受控小批执行，页面失败不取消后续页面。续做未检查页面时不改全量分母。进度只报告已检查页面数和未完成页面数。

```bash
node "<SKILL_DIR>/scripts/collect_page.mjs" --scope "<WORK>/scope/scope.json" --url "<ACTUAL_URL>" --config "<WORK>/observed-signals.json" --runtime "<TOOLS>/node-runtime" --browser-executable "<CHROME_PATH>" --output "<NEW_DOM_DIR>"
python3 "<SKILL_DIR>/scripts/check_html.py" --nu-executable "<NU_EXECUTABLE>" --html "<HTTP_CAPTURE>/body.html" --url "<ACTUAL_URL>" --source "<ACTUAL_SOURCE>" --captured-at "<ORIGINAL_UTC_TIMESTAMP>" --output "<NEW_NU_DIR>"
python3 "<SKILL_DIR>/scripts/audit_semantics.py" --scope "<WORK>/scope/scope.json" --manifest "<NEW_DOM_DIR>/manifest.json" --supplement "<NEW_NU_DIR>/manifest.json" --state "<DATA>/semantics" --output "<NEW_REPORT_DIR>"
```

多个manifest继续用 `--supplement`。没有任何证据时可创建 `{ "schema_version":1,"captures":[],"tool_reports":[] }` 的空manifest，仍按完整scope生成逐页缺口；这不是检查完成。失败日志必须另存，每页状态能说明失败原因。跳转后的URL作为实际证据URL保存，原始目标缺口保留；扩查目标前更新清单并告知用户。

`--scope` 与 `--urls/--url` 不能混用，防止汇总时缩小已公布范围。旧 `--urls/--url` 接口仅供兼容已有集成/证据回放，不用于跳过本技能的范围预览。

上述采集、Nu/axe和审计命令是兼容已有机器证据的辅助方式，不是默认必跑流程。默认直接用真实浏览器逐页核对 SKILL.md 的常见标签清单（包含 title/meta），保存对应 DOM 片段并生成简短报告。旧脚本 pending-reviews 仅描述其机器证据覆盖，不能替代整页检查记录；工具完整输出留本地，不纳入飞书正文。

## A 标签专项检查

每个页面均执行以下检查，不能只检查空 href 或 javascript:：

1. 在页面内容就绪后，枚举渲染 DOM 中的全部 `a[href]`，保留原始 href、解析后的目标、链接文字和定位。逐一核对内部链接的查询参数；`utm_*`、`gclid`、`fbclid` 等作为追踪候选，`ref`、`source` 等不能仅凭名称定性。按实际用途确认哪些只是埋点，哪些影响业务、目标内容或归因权益；证据不足则待确认，不建议统一删除查询串。记录相关参数名和所在链接，报告只写简短问题。
2. 检查头部、导航、正文卡片/列表、侧栏和页脚的可点击入口；滚动并展开公开导航以核对动态入口。结合可见交互、事件绑定、`role=link`、指针样式等定位非 A 候选，不能只查内联 onclick，也不能仅凭样式认定跳转。先检查元素及其祖先是否已有有效 A 标签。
3. 对疑似非 A 页面跳转，用真实浏览器安全点击，记录实际处理点击的元素片段及跳转前后 URL（包括新标签页或客户端路由）。仅执行公开浏览导航，不提交表单、登录、下单或改变账户状态。菜单展开、同页选项切换、弹窗不登记为缺少 A。无法确认行为的入口记为待确认；仅看到一个 onclick 或 BUTTON 不足以确认问题。点击观察后返回原页继续检查，未核对的入口不得当作通过。
4. 每页内部记录分别包含“内链参数”和“非 A 跳转”的状态（已检查／待确认／未检查）、覆盖区域、候选与确认结果、证据及剩余缺口。两项都执行后才可称这两项已检查；页面受阻或仍有未核对入口时保留具体缺口。旧采集器、Nu/axe 或仅保存 HTML 不能代替行为核对。飞书仍按页面合并简短 checkbox，不能因此增加冗长分析；缺口用一句短说明。
