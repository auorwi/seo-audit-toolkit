# 001 数据合同

SQLite schema version 1。运行状态与证据保存在独立 data 目录；升级技能不删除数据库。一个 CLI 进程持有该数据目录的排他锁，阻止并发写入。

## 身份与路由

- URL 身份仅归一 scheme／host／默认端口，去除普通文档锚点；业务查询、顺序、重复查询键、路径大小写、尾斜线保持。
- `#/...`／`#!/...` 保留为客户端路由身份，不能用 HTTP 判为已访问。
- canonical、hreflang、redirect、link、sitemap_child 是单独关系；任何关系都不会自动删除或合并原 URL。
- template 为已知路由模式，unknown 以字面路径分组；classified=false 的分组不是已经确认的真实路由模板。
- index_intent 默认 unknown。当前001不根据观察自动决定是否应该收录。

## 主要对象

- urls：首次／最后来源观察、分类、最近 HTTP 状态和检查时间。
- sources／snapshots／appearances：逻辑来源、原采集时间、导入时间、范围、原始URL与保留元数据。
- source_urls：每来源对该URL的 observed 或 missing_candidate 状态。
- changes：new_url、missing_from_source、reappeared_in_source、http_status_changed。
- checks／fetches：观察与实际 HTTP 尝试分开；一次请求可产生基础响应和解析后观察，不能将 checks 行数当请求数。
- tasks：queued、running、done、failed、blocked、deferred 及原因。
- relations：带运行 ID 的关系边；source URL 是实际被取数的文档。
- exclusions：范围外、无效、敏感或容量受限记录，敏感值脱敏。

报告中的 accepted 是接受的输入记录数，可能包含重复；url_count 是合并后的身份数量。source_snapshot_count 是来源快照数量，不是 URL 数量。

languages.csv 按页面的路由语言前缀统计，空值表示未识别，不能当作无语言。source-coverage.csv 的独有数按全部历史来源成员关系计算，包括缺失候选；observed 与 missing_candidate 另列。一个 URL 同时属于多个来源时会进入各来源发现数，但不再算任何单个来源独有。

预期可索引规范 URL 总量、已确认退役 URL 总量当前均为 null：本技能没有足够权威状态输入，不能将 200、canonical 声明或来源缺失替代为这些结论。reclassify 仅更新派生路由字段，不改原始观察记录。

## 状态解释

sample／unknown 来源中未出现某 URL 不改变它的历史状态。明确 complete 来源的新快照中缺失仅产生候选，仍保留 URL；较旧快照不能覆盖更新来源的当前状态。

历史导入不更新 last_checked。HTTP 200 不代表页面有正确内容、可索引或已索引。普通 GET 使用自己的 UA，不代表真实 Googlebot／Bingbot。所有抓取均保留无 JS 的证据模式。

completed 表示已执行当前有限队列且没有受阻／延期，不等于全站完整；partial 包括预算耗尽、失败、受阻或主动延期。report 命令成功只代表文件生成，不改变运行覆盖。

## 证据与导出

fetches 记录实际请求、脱敏响应头、原始响应正文文件路径、SHA-256、时间与错误类别。含 Cookie／Authorization 的头不归档。HTTPS 校验证书，解析目标为公网 IP 后固定连接该 IP，不使用账户会话。

保留原始证据及来源文件，CSV 适合筛选，snapshot.json 用于机器消费。Excel 公式前缀在 CSV 单元格中转义；JSON 保持真实字符串。

若迁移数据目录，正文证据路径当前是绝对路径，应一起迁移证据并按迁移映射更新 fetches.evidence 与 checks.details 中的路径；文件校验值不变。不要仅复制 SQLite 然后声称证据完整。
# v1.0.2 响应头证据补充

`fetches.headers_all` 为可空 JSON 列：按响应中的顺序保留允许保存的重复响应头，包括多个 X-Robots-Tag。旧 `headers` 对象继续保留兼容性。旧记录的 headers_all 为 NULL，不能据此证明重复头完整。升级只添加列，不覆盖历史。CF-Ray、X-Request-ID、X-Correlation-ID 可保留作公开请求追踪；Cookie/Authorization 不保存。
# v1.0.3 canonical 证据补充

捕获公开 `Link` 和 `Refresh` 响应头，并增加可空 `fetches.captured_header_names` JSON 列记录本次采集器允许保留的头名称。没有该字段的历史记录，不能证明未出现 Link/Refresh。此变化不改写旧响应。敏感 URL 查询值仍脱敏。003共享适配层也保留这些字段，供004使用。
