> Historical/opt-in BingX example. Apply to generic sites only after replacing URLs, selectors, and business assumptions with current evidence from the selected profile; never auto-import example evidence.

# 输入、证据与持久状态

v1.0.1 补充：共享适配层保留 Link、Refresh 和可空 captured_header_names（安全响应头采集策略）。003 的索引指令规则不变；004 可据此区分“已捕获但未出现 canonical HTTP 头”与“旧版本根本没采集该头”。001 v1.0.3 起写入该采集策略字段。

## URL 范围

JSON 数组允许 URL 字符串，或下列对象：

```json
[{"url":"https://bingx.com/en","index_intent":"unknown"}]
```

只有明确批准的路由索引策略才附 `index_intent: indexable|excluded`、非空 `intent_source`、带时区的 `intent_at`。策略超过本次 freshness 窗口按 unknown 处理。不要生成虚构的策略来源。

## 001 数据桥

以 SQLite `mode=ro` 读取 schema_version=1 的 `fetches`；不更新 001 的资产或检查数据。选中指定 URL、各自 robots 和已记录跳转目标（最多六轮闭包），保留其全部历史请求。每条 body 必须在该数据目录内部、SHA-256 和字节数匹配，且不超过 8MB；损坏或缺失留为 evidence gap，不伪装网络故障。

新版本的 `headers_all` 是按线序保留的安全响应头列表；缺失时读取旧 headers 对象，并标记 `header_capture_complete=false`。不会反向声称旧历史捕获了所有重复头。`capture_id=run_id:fetch_id` 是本地证据编号，`request_id` 来自可用的 CF-Ray/X-Request-ID/X-Correlation-ID。没有服务端 ID 时留空。

## 独立 manifest / 浏览器补充

所有文件路径相对 manifest 所在目录，或该目录内的绝对路径。符号链接到目录外不能读取。`evidence` 哈希由实际保存的文件计算，不得使用示例值或手工重建 HTML 冒充线上响应。

```json
{
  "schema_version":1,
  "records":[{
    "url":"https://bingx.com/en",
    "status":200,
    "checked_at":"2026-09-16T15:00:00Z",
    "headers":[["content-type","text/html"],["x-robots-tag","noindex"]],
    "environment":"实际采集客户端/地区的描述",
    "evidence":{"path":"evidence/page.body","sha256":"实际文件的SHA-256","bytes":123}
  }],
  "rendered":[],
  "observations":[]
}
```

此片段只解释字段，不能直接用来运行审查。每一跳单独记录；本工具不隐式访问 Location。headers 列表代表完整采集安全头；如果工具仅提供部分字段，必须加 `header_capture_complete:false`。对象形式默认不完整。剔除 Cookie/Authorization 等非必要字段；保留审查所需公开响应头。

`status` 为 100–599 整数，工具网络失败为 null + `error`；不把错误代码强制转成 404/500。`checked_at` 要带时区。200 缺失正文仍保留状态，但不能推断不存在 meta。

`rendered` 使用相同证据结构，附 `mode:"rendered"`，正文是实际浏览器保存的 DOM。若浏览器无法取得真实 HTTP 状态/响应头，不猜测 200；保持未核验。脚本只采用状态为 2xx、未过期、正文已验证的 DOM 解析指令；原始和渲染证据不合并。

`observations` 每条需 `url`、`engine`、`kind`、`source`、`checked_at`，另附实际工具输出、证据链接和状态。`kind` 建议区分 `index_snapshot`、`live_inspection`、`verified_bot_log`、`user_agent_probe`。字段不自动转换成“已收录”或“真实 bot 访问成功”；报告保留原始观察由专项复核。不要混入会话 Cookie/令牌。

## 输出和历史

- `rows.csv`：每个 URL × 引擎的当前评估；`report.json` 保留完整证据和解释。
- `request-history.csv`：历史 HTTP 事件、时间、环境、服务端请求 ID、本地证据 ID，不因新成功删除旧失败。
- `findings.csv`：当前发现。`classification` 包括配置事实、HTTP 观察、配置交互、待复核、证据缺口。
- `issue-history.json/csv`：稳定 issue_id、first_seen、last_seen、sightings、open 状态和最新 payload。
- 状态库 `issues.sqlite`：原子写入 runs/issues/sightings，相同内容和时点重跑幂等。相同问题跨新周期只增加 sighting，不新建问题。旧报告回填不覆盖新报告的 payload。当前专项不自动关闭问题。

## 可用范围

Python 3.10+ 标准库；公开 HTTP 证据、常规 Googlebot/Bingbot/YandexBot。默认采用小批模板样本。全站大量 URL 应按原计划分批取证和输出，未获得权威全集不计算全站覆盖率。正文文件保存在本地数据目录，分享报告时需另行打包所需证据，JSON 中的本地路径不会自动上传飞书。
