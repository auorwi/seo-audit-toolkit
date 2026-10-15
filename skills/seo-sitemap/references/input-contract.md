> Historical/opt-in BingX example. Apply to generic sites only after replacing URLs, selectors, and business assumptions with current evidence from the selected profile; never auto-import example evidence.

# 输入与历史合同

## 001 证据桥接

`--inventory` 读取 schema_version=1 的 001 SQLite。按 URL 选最新 fetch（同时间以 id 决定），不回退到旧成功；从该次 run 的匹配 checks 取得 HTML 元信息。最新失败、哈希不匹配和证据文件丢失均保留为数据缺口。证据必须位于数据目录内，拒绝路径逃逸。

读取使用只读连接及一致性事务，不修改 001 数据库。证据正文是 HTTP 响应内容，不执行 JS；页面渲染结论需要单独浏览器证据。

## 独立证据 manifest

JSON 示例（示例 URL 和哈希必须替换为实际取得的证据）：

```json
{
  "documents": [{
    "url": "https://bingx.com/en/sitemap-main.xml",
    "checked_at": "2026-09-16T10:00:00Z",
    "status": 200,
    "evidence": {"path": "/absolute/evidence/leaf.xml", "sha256": "实际SHA256", "bytes": 6755}
  }],
  "pages": {
    "https://bingx.com/en": {
      "url": "https://bingx.com/en",
      "checked_at": "2026-09-16T10:01:00Z",
      "status": 200,
      "evidence": {"path": "/absolute/evidence/page.html", "sha256": "实际SHA256", "bytes": 12345},
      "details": {
        "headers": {"content-type": "text/html"},
        "noindex_observed": false,
        "robots_directives": {"googlebot": ["index"]},
        "canonicals": ["https://bingx.com/en"]
      }
    }
  }
}
```

manifest 与正文位于同一目录树内；每份证据先验证字节数和 SHA-256。错误请求使用 `status:null` 与 `error`，不编造正文。响应头只保留受支持字段，Cookie／账户授权不导入。

浏览器确认错误正文后可在 details 添加：

```json
{"content_verdict":{"state":"error_content","evidence":"实际元素 selector、文字片段和截图/浏览器证据位置","reviewed_at":"2026-09-16T10:02:00Z"}}
```

它必须来自实际观察，不是根据 URL 或 title 猜测。保留原 HTTP 证据和浏览器参考，说明两种观察环境。此字段代表评审结论，脚本不会替代浏览器复核其语义。

## 独立业务预期清单

```json
{
  "source_id": "cms-published-export-2026-09-16",
  "kind": "cms",
  "coverage": "complete",
  "captured_at": "2026-09-16T10:00:00Z",
  "scope_roots": ["https://bingx.com/sitemap.xml"],
  "rows": [{
    "url": "https://bingx.com/en/price/bitcoin",
    "published": true,
    "should_index": true,
    "canonical_url": "https://bingx.com/en/price/bitcoin",
    "modified_at": "2026-09-15",
    "modification_kind": "significant"
  }]
}
```

独立 kind 为 `cms`、`routes` 或 `business`，必须说明真实出处。其他 kind 不用于证明完整。Sitemap 派生清单即使重命名为 CMS 也不独立，调用方需核实来源，脚本无法验证清单作者的声明。

coverage 为 complete／sample／unknown。complete 指所声明入口范围的独立业务全集，不是任意当前导出页。只有明确 published=true、should_index=true 且 canonical_url 与该 URL 相同时才算预期可索引规范 URL；布尔值必须为真正的 JSON 布尔值。缺意图时保留未知。

`retired:true` 必须来自业务退役记录。`modification_kind:significant` 仅用于已知重要变更，不把版权年份、抓取时间或普通部署时间当作内容更新时间。日期精度按天保留，同日不能推出 lastmod 落后。

## 持久账本

问题 ID 基于站点、规则、URL、关联目标与引擎，不包含周次或采集时间。首次／最后报告时间与证据采集时间不同，不能把再次汇总当成重新访问。

重复同一输入及审查时刻保持幂等；新周的同一问题更新观察记录，保留原 ID。某问题本周未出现不自动关闭，`seen_in_latest_run:false` 表示本轮未再观察；修复验证由后续 017 专项负责。
