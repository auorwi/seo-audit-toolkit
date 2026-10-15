---
name: seo-crawlability
description: 按指定 目标网站 URL 核验 robots、HTTP 跳转及 meta/X-Robots-Tag 索引指令，关联原始与渲染证据，保留历史故障和稳定问题 ID。用于抓取限制、noindex 和访问异常专项；不推断实际收录，不修改生产配置。
---

运行前设置 `SEO_SITE_PROFILE=/absolute/path/site.json`。使用 `seo.py init` 为目标站点创建显式配置；主机采用精确白名单，不自动扩展子域。默认使用通用网站规则；`business_profile: "bingx"` 为可选业务扩展，只有明确选择它才启用对应路由和市场参考逻辑。缺少 profile 时不进行线上采集。

v0.1.0 的主机字段及 URL 主机只接受 ASCII。国际化域名请显式提供 ASCII punycode A-label（例如 `xn--fa-hia.de`）；不要输入 Unicode 主机名。工具不会自动把 `faß.de` 转成其他域名，Unicode 路径和品牌文字仍可使用。

默认交付本地报告或问题清单。只有用户明确要求外部发布并指定或确认目的地时，才调用相应飞书/外部工具写入；无需发布时不要求外部账户授权。所有输出、证据和状态库存放在技能目录之外，按站点隔离。示例、fixtures 和既有历史记录仅用于显式选择的离线演练，不自动导入真实报告。浏览器的通用就绪信号仅证明可见正文与有限稳定性，不证明业务实体正确；如提供身份/模板信号则保持这些更强要求。


# 003 · 可抓取性与索引指令

使用随附 Python 3.10+ 标准库脚本。默认数据来自 001 的持久证据库；独立 manifest 也可运行。不要临时重写规则解析或将三家搜索引擎当作同一套行为。

## 明确范围并取证

1. 采用用户指定 URL、平台问题样例或 001 的模板样本，写入 `urls.json`。不要默认逐一渲染全部币种页面，也不要将导出的平台样例当作完整错误清单。重复模板先抽样；发现共同问题后再扩大受影响范围。
2. 读取 [输入与证据合同](references/input-contract.md)。业务索引意图默认 unknown；只有带来源和时间的明确策略才设为 indexable/excluded。不要仅因为 URL 在 Sitemap 中就判定必须收录。
3. 先检查现有证据的新鲜度、每个 origin 的 robots、跳转链及页面响应。需要补采时调用已安装的 `$seo-update-url`，小批捕获公开页面；将数据和工作 profile 放在数据目录或临时工作目录。001 v1.0.2 起保留重复响应头；旧记录缺少此证据须如实标记。
4. HTTP 与渲染状态不同。需要渲染证据时使用可用浏览器实际打开对应页面，保存 DOM、URL、采集时间、浏览器来源及 SHA-256，按 manifest 追加。只看到文本摘要不等于取得完整 DOM。浏览器或登录受阻时保留未检查范围，不捏造证据。
5. 后台或日志观察按引擎、URL、时间、来源独立保留；平台功能可用时用既有授权只读读取。用户要求只检查 003 时，不自动开展三个站长平台的全面审查。真实平台取数分别属于 014–016，不能用本地模拟 User-Agent 宣称真实爬虫访问成功。

补采示例（替换为绝对路径，profile 使用本次样本种子；抓取仍受主机白名单、robots 和请求预算限制）：

```bash
python3 "<001_SKILL>/scripts/update_url.py" discover --data "<INVENTORY_DATA>" --profile "<WORK>/profile.json" --max-requests 20 --max-depth 0 --max-sitemaps 0 --max-urls 500000
```

## 执行本专项

默认历史状态目录为 `<DATA_DIR>/<SITE_HOST>/crawlability`。每次报告使用新目录；不要清空旧问题库。

```bash
python3 "<SKILL_DIR>/scripts/audit_crawlability.py" --inventory "<INVENTORY_DATA>/inventory.sqlite" --urls "<WORK>/urls.json" --state "<STATE_DIR>" --output "<NEW_REPORT_DIR>"
```

- `--url` 可重复；或 `--urls` 读取 JSON 数组。二者合并，精确 URL 保留查询参数与大小写；普通 fragment 不作为单独 HTTP 请求。
- 默认评估 Googlebot、Bingbot、YandexBot；`--agent Googlebot` 等可单独调用或重复指定。
- `--max-age-hours 168` 为默认证据窗口。`--at` 可固定回放时点；无此参数时用当前 UTC。
- `--manifest` 可替代 `--inventory`；`--supplement` 可重复，用于实际浏览器和平台观察。脚本本身不发网络请求。
- `0` 表示所选范围的审查完成，仍可能存在问题；`2` 表示已生成部分报告且有证据缺口；`1` 为输入或执行错误。三者均不表示全站无问题。

## 判断及复核

使用 [规则与边界](references/rules.md) 解释结果。重点区分：

- robots 规则模型、工具实际 HTTP 事件、页面声明、真实引擎观察和实际索引状态。
- noindex 与 nofollow/nosnippet；排除意图未知与明确配置错误；robots 禁抓导致 noindex 无法读取的交互。
- 原始与渲染后的指令；不要用渲染后的 index 覆盖原始 noindex。
- 一次 403/429/5xx、同环境重复事件及跨环境观察。请求失败或证据过期不得回退成旧 200 的当前成功证明。
- 旧版折叠响应头、缺失 Content-Type、缺少独立 origin robots、跳转链断点与网站真实缺陷。

逐项阅读 `report.md`、`rows.csv`、`findings.csv` 和 `request-history.csv`。详细证据在 `report.json`，问题历史在 `issue-history.json/csv`。稳定问题 ID 按规则、URL、引擎组成；重复运行更新同一问题，缺席不自动关闭。修复验收由 017 或明确的新证据确认。

输出结论包含检查范围、真实采集数量、发现、证据时间、建议、尚未检查项和报告位置。用户要求飞书时使用当前可用飞书工具发布并回读验证；本技能不假定平台凭证，不发送消息、不提交索引、不改变 robots/页面/CDN 配置。

## 维护验证

生产行为变更先添加失败案例，再实现和回归：

```bash
python3 -m unittest discover -s "<SKILL_DIR>/tests" -v
```

离线测试证明规则与合同；只有实际抓取或后台读取能证明外部接入。本技能 v1.0.1；共享证据层新增保留 Link/Refresh 与 captured_header_names，供004读取，不改003判断范围。当前上线验收范围见独立交付报告，不能扩大为全站检查。
