> Historical/opt-in BingX example. Apply to generic sites only after replacing URLs, selectors, and business assumptions with current evidence from the selected profile; never auto-import example evidence.

# 证据合同 v1

运行数据放到技能目录外。JSON禁止重复键和NaN，单个manifest/证据8MiB上限；source路径相对manifest目录，不能越界或通过软链接越界，必须SHA256匹配。错误证据隔离后继续处理其余文件；同ID全部隔离，同内容同报告同采集时间不重复计数。

## Manifest

```json
{"schema_version":1,"host_id":"https:bingx.com:443","run_kind":"audit","scope":[{"url":"https://bingx.com/en","device":"DESKTOP","js":"DISABLED"}],"evidence":["mapped-database.json","mapped-http.json","mapped-dom.json"]}
```

run_kind：audit/controlled_fixture/historical_replay。scope非空；device为DESKTOP/MOBILE/UNKNOWN；js为ENABLED/DISABLED/UNKNOWN。不同设备、JS、查询参数组合不能替换。HTTP→DOM是两次观察，不声称同次导航或相同网络。

## 通用 Envelope

必需 id/kind/host_id/captured_at/source；时间带显式时区，不能晚于比较时点。source为`{"path":"file.txt","sha256":"真实64位哈希"}`。captured_at是工具取得证据时间，不是后台数据库日期。数据不能含凭证。

### yandex_ui

必需 report、source_url、reviewer、site_quote、rows。source_url须为Yandex Webmaster且path host匹配。site_quote来自可见站点选择器。report支持diagnostics/duplicates/sitemaps/searchable/excluded/crawl_stats/page_check/database/js_render/performance/get_parameters/security。

可选database_date格式：`{"value":"2026-09-09","quote":"09/09/2026","format":"%m/%d/%Y"}`，quote须存在且日期可核对，不能将条目日期冒充整份报告日期。可选filters保留筛选、实际取样及数量单位；该字段只作为操作者描述，不生成已确认问题。

Page check/js_render另给test_date同上；过往日期归historical_test，未知归undated_test。只有与采集日相同的绑定日期才纳入当前引擎对照，精度明确为当地日期且时区未知。无法判断跨日时保守列缺口，禁止为通过验证伪造时间；需要小时级新鲜度须另取得带时区的真实测试记录。

每条row：`{"url":"精确原URL或null","quote":"此行或此检查的原文","fields":{"字段":{"value":"映射值","quote":"该字段原文"}}}`。url必须在此条quote中完整出现（含参数）；报告级观察用null。fields支持：

- searchable：bool，仅接受明确的正/负搜索状态原文；用于database，Page check结果不能覆盖搜索快照。
- http_status/count：真实整数、独立数值token匹配，不把48,003中的3识别为3。
- device/js：绑定原文；缺失为UNKNOWN。Decided by robot不能映射为ENABLED。
- crawl_at/search_at/tested_at：仅原文有时区且对应同一时点才可转换；否则用raw_date。
- reason/severity/state：reviewer的受控分类映射，须绑定原始标签；不是模型直接确认根因。state=PRESENT/ABSENT/UNDEFINED。
- title/description/note/raw_date/count_display/group_id：保留原值，不能借映射改写事实。group_id建议用实际分组元信息稳定识别；同URL的不同组不误合并。
- target_url：实际绑定目标；只是关联地址，业务等价性另验。

### live_http

source JSON必需url/final_url/status/method=GET/device/js=DISABLED/captured_at/source_description。不接收操作者另写的status覆盖原始JSON。可带redirects列表，以及`body:{path,sha256}`绑定实际正文；最终不同落点必须专业核验。普通UA和平台机器人是否可比不能通过同device字符串证明。

### public_dom

source JSON必需url/captured_at/device/js=ENABLED，按实际DOM保存title/description/h1/body_excerpt/canonical/lang。body_excerpt是摘录，不得叫完整DOM。Envelope附reviewer、reviews：`{"reason":"ROUTE_ENTITY_MISMATCH","field":"h1","quote":"实际实体原文"}`。支持ROUTE_ENTITY_MISMATCH/ERROR_PAGE_CONTENT/EMPTY_METADATA/TITLE_COUNTRY_MISSING；field限定title/description/h1/body_excerpt。空quote仅可用于确实为空的EMPTY_METADATA字段。

DOM评审是有来源的人工/模型观察；不自动写成网站根因、平台排除原因或“引擎已恢复”。同URL/设备可作数据库JS关闭样本的补充，但保留JS区别。输出仍指向专业owner并要求业务/代码确认。

### yandex_api

Envelope附endpoint与脱敏request_url，必须匹配`https://api.webmaster.yandex.net/v4/user/<数字>/hosts/<host-id>/<endpoint>`。source为该只读响应JSON。支持diagnostics、indexing/samples、important-urls、search-urls/events/samples、sitemaps。分页样例总数不是全站URL数；本版本不自动分页或调用网络。

## 历史与结论

issue ID绑定host/原URL/规则/重复组；同一问题跨报告追加证据。SQLite按run内容幂等记录，同次重放不新增sighting；缺席不自动关闭。fixture使用独立问题命名空间。referrals是待专业审查的转交单，不是已经执行的审查。
