# 013 证据合同

`manifest.json` 使用 `schema_version: 1`，包含 `scope: [{url, devices: ["desktop", "mobile"]}]`、`captures: [proof]`、`reviews: [proof]`。每个 proof 为 `{path, bytes, sha256}`；文件必须位于 manifest 根目录或其子目录，单个文件不超过 8 MB。哈希证明本地字节未改变，不证明外部事实独立可信。

capture 来自 `collect_page.mjs`：`snapshot_id`、`url`（真实最终 URL）、`requested_url`、`device`、`captured_at`、`readiness`、`html`、`document_sha256`、`media`、`responses`、`viewport`、`environment`、`phase`、`screenshot`。媒体行共享该快照采集时间。解码是快照之后的有界探测，保留 `current_src`、`source_after_probe`、`completed_at`，不能将其他资源的解码结果绑定到当前图。

媒体行 `slot` 取唯一 DOM id 或实际 nth-of-type 路径；CSS 背景另加伪元素/背景后缀。重复槽位/快照 ID 拒绝接收，避免覆盖旧证据。DOM 结构重排可能改变槽位，需要在历史层人工归并，不自动模糊合并不同媒体。

`visible` 使用浏览器 checkVisibility 的 opacity、visibility 与 content-visibility 检查，再检查尺寸；`in_viewport` 另加视口矩形相交。这仍不是遮挡检测。截图在 DOM 快照和解码探测之后单独采集，时间差内可能发生异步加载或布局变化；不能反向用较晚截图伪造较早时刻的成功加载。

响应保留实际 GET、状态、时间、白名单响应头和资源类型。`body_prefix_base64` 仅在已知小型、未压缩图片响应上可用，最多 4096 字节；其他响应保留 `body_unobserved_reason`。206 必须确认 Content-Range 从 0 开始后才进行文件头判别。加载/解码成功不是文件传输预算或索引通过。

具名用途 review 示例（用真实 capture、截图 proof 与原文替换）：

```json
{
  "snapshot_id": "media-actual-id",
  "capture_sha256": "实际 capture 文件的 SHA-256",
  "screenshot_sha256": "实际截图 SHA-256",
  "reviewer": "Codex + 本轮复核标识",
  "method": "已查看实际截图，并对照同快照 DOM 与可见原文",
  "reviewed_at": "带时区的实际复核时间",
  "items": [{
    "slot": "img#actual-id",
    "purpose": "informative",
    "citation": {"field": "visible_main", "quote": "实际可见原文片段"},
    "notes": "说明图片在此上下文中的用途，以及截图和 DOM 如何支持判断",
    "important_initial": true
  }]
}
```

purpose 可选 `informative`、`decorative`、`functional`、`watch_video`、`auxiliary_video`、`nonvideo_embed`、`unknown`。`citation.field` 仅为 entity/visible_main，quote 必须实际存在且非空。复核时间在采集之后、审查时点之前。不要依据文件名或 alt 自行编造图片内容。

信息型 CSS 可加 `image_search_target`（是否需要图片搜索发现）、`equivalent_img`（是否已有视觉/语义等价 img）；观看视频可加 `representative_thumbnail`。这些是人工/具名代理语义结论，必须写明依据，未确认则不填。所有旗标必须为布尔值。

各目录合并方法：新 manifest 可放在所有子目录的共同父目录，将 proof.path 加子目录前缀。capture 内 screenshot.path 原来相对采集目录，当前加载器将它相对于 capture 文件所在目录解析；保持该路径与原始 capture 字节不变。review 的 capture_sha256 绑定原 capture 文件，而非仅 HTML。报告中保留所有缺口，不通过重写原文件消除错误。

返回 declared_checks_complete 仅对应声明的页面设备组合及已观察媒体；`all_declared_resources_verified`、`full_site_proven`、`video_indexing_verified` 等维持 false。未选候选列表表示不在本次 currentSrc 中，不等于资源未使用或可删除。
