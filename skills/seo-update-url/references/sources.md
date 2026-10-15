> Historical/opt-in BingX example. Apply to generic sites only after replacing URLs, selectors, and business assumptions with current evidence from the selected profile; never auto-import example evidence.

# 来源接入与浏览器补充

## JSON／CSV／TXT

```bash
python3 "<SKILL_DIR>/scripts/update_url.py" import --data "<DATA_DIR>" --file "<EXPORT_FILE>" --source-id "gsc:page-indexing:2026-09" --kind gsc --captured-at "2026-09-16T15:00:00+08:00" --coverage sample
```

支持 JSON 字符串数组、包含 url 的对象数组，或 `records`／`urls`／`rows` 包装；CSV 识别 url、Page、Top pages、网页等列，否则指定 `--url-column`；TXT 一行一个 URL。只保留必要的资产元数据，不复制整个账户导出。

来源 kind 可选 historical、gsc、bing、yandex、cms、routes、logs、export。保留同一个逻辑来源 ID，以便比较不同时间；同一份内容、时间与来源重复导入幂等。覆盖范围变化应明确另建来源 ID 或使用 sample。

`captured-at` 是来源采集时间，不是执行导入的时间。只有日期时可填 YYYY-MM-DD，工具保留日期精度；不得虚构小时。带时间时必须包含时区。

`complete` 表示该明确来源完整且没有导出／分页截断。GSC、Bing、Yandex 的示例 URL、搜索表现列表通常不能当作站点全集；不知道就标 unknown。数据库会把有拒绝行的完整导入降为 sample，避免据此推断其他 URL 消失。

## 三个平台

001 提供来源导入和浏览器补充，不声称已经实现三个平台的完整 API 连接器。使用当前已授权工具读取／导出用户指定报告，再导入；保留原报告 URL、数据日期与样例限制的说明。需要新登录时交由用户完成，继续独立的公开发现工作。

导入平台 URL 是资产发现，不是重新进行了该平台 URL 实时测试。平台报告量和实际取得 URL 数分开报告。不要自动请求索引或提交 Sitemap。

## 浏览器 DOM 导入

使用当前可用浏览器工具的已文档化读取能力，读取真实当前页面。记录页面 URL、实际采集时间、页面加载是否完成和是否执行 JS。只导出公开页面的发现字段，不导出 Cookie／LocalStorage／令牌。

保存 JSON：

```json
{
  "page_url": "https://bingx.com/en",
  "captured_at": "2026-09-16T15:00:00+08:00",
  "links": ["https://bingx.com/en/price/bitcoin"],
  "canonicals": ["https://bingx.com/en"],
  "alternates": [{"url": "https://bingx.com/ja", "hreflang": "ja"}]
}
```

时间为格式示例，使用时必须换成真实观察时间。links 来自页面 a[href]，canonicals 来自 link[rel=canonical]，alternates 来自有 hreflang 的 alternate。先过滤 javascript、mailto 等非 HTTP 链接；相对 URL 可以导入并按 page_url 解析。网页使用 base 时优先导出浏览器计算后的绝对 href。

```bash
python3 "<SKILL_DIR>/scripts/update_url.py" import-dom --data "<DATA_DIR>" --file "<DOM_JSON>" --source-id "browser:https://bingx.com/en"
```

保持每个被访问页面一个逻辑来源，不能把部分滚动／菜单状态的结果标成全站完整。客户端 hash 路由保留为资产，HTTP 队列标为需要浏览器，不假装请求 fragment 即能看到该页面。

## 调整公开发现范围

使用 toolkit 的 `seo.py init` 为目标网站创建 profile，填写公开 seeds、sitemaps、allowed_hosts 和排除路径，使用 `--profile` 或 SEO_SITE_PROFILE 显式传入。`assets/bingx-profile.json` 仅供选择 BingX 业务扩展时参考，不是默认配置。未知子域只出现在范围外记录中，不自动加入；不要将发现的 UAT／账户等地址当成已授权爬取目标。

requests 是整个 run 的实际尝试上限，包含 robots、Sitemap、页面与跳转各跳；max-urls 是整个资产库的容量上限，已有资产不会被删除，达到上限会停止新增并记录排除。使用已有 21 万 URL 目录时应设至少 500000，或按实际规模配置。

`--resume` 延续已落盘队列；它不会自动重试受阻任务，也不允许偷偷改变深度／范围。429 会停止该 origin 的后续请求；完成授权或等待恢复后启动新 run。

响应大小上限 8MB（含解压后），超限明确失败。仅解析原始 HTTP 的链接；JS 补链需要浏览器。robots 无法读取时保守暂停该 origin 的页面自动发现，不把失败解释为站点禁止索引。

## 当前机器的 DNS 代理模式

线上采集只允许公网 DNS 地址并固定已验证的连接地址。历史 `allow_system_dns_alias` 设置不能开启线上 benchmark/private DNS 例外；如系统网络返回非公网地址，记录环境限制并由用户调整网络。受控测试只使用独立且明确的本地 fixture 配置，不放宽真实站点的 DNS 约束。

2026-09-16 此机器已用正常 TLS 验证 BingX robots 返回200，并完成显式配置。通用技能配置仍保持关闭；换机器不要照搬此选项。CLI 优先使用数据目录的 profile.json，显式 --profile 参数优先级最高。
