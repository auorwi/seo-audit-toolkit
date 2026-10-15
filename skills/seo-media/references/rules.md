# 013 规则与修复

| 观察 | 结论范围 | 修复或下一步 |
|---|---|---|
| 同源绑定图片 error 事件 + complete + 零自然尺寸 | 此设备此时浏览器加载失败 | 查看当前资源的真实状态、发布路径、类型与访问限制；不同 CDN/设备分别复测 |
| decode 拒绝，缺少绑定错误事件 | 候选，可能有源切换或上下文影响 | 补同次网络/事件证据，不判全站坏图 |
| 404/410 | 当前请求资源不存在 | 查引用路径和资源发布/撤下策略；保留错误响应 |
| 403/429、网络超时 | 限制/取证缺口 | 查相同上下文的访问与限流，不当永久死链 |
| 图片响应实际为 HTML | 当前媒体响应内容错误 | 查错误页回退、重定向及 CDN 配置，不能仅修改扩展名 |
| Content-Type 与嗅探签名不符 | 实际类型冲突线索 | 对照完整响应/解码后修正发布 MIME；文件前缀不是完整解码 |
| 未完成且屏幕外 lazy | 当前未触发 | 有必要时单独滚动再采集，前后阶段保留 |
| 重要首屏图 loading=lazy | 011 性能复核线索 | 测量实际 LCP 与加载依赖再决定优先级；不是 CWV 失败证明 |
| 装饰空 alt | 无此项问题 | 不补无意义描述；缺 alt/功能名称交 006 |
| 需图片搜索发现的重要信息仅 CSS 承载 | 用途复核支持的可发现性问题 | 提供可抓取 img/picture，核对等价内容；不推断实际已收录 |
| 辅助教程 iframe/video | 可接受页面形态 | 核验具体资源与语义，不强制改独立观看页 |
| 观看页缺已确认代表缩略图 | 候选 | 核验稳定缩略图及 008 声明，再对照 014 视频索引；当前工具不点击播放 |

主要原始资料（2026-09-17 核对）：

- [Google 图片最佳实践](https://developers.google.com/search/docs/appearance/google-images)：图片发现、img/picture/src、支持类型、alt 与 CSS 图片边界。
- [Google 视频最佳实践](https://developers.google.com/search/docs/appearance/video)：观看页与辅助视频、缩略图、发现性及索引条件。
- [WHATWG images](https://html.spec.whatwg.org/multipage/images.html)：srcset 候选与选择，密度与自然尺寸。
- [WHATWG embedded content](https://html.spec.whatwg.org/multipage/embedded-content.html)：currentSrc、complete、图片和视频元素状态。
- [W3C 装饰图片](https://www.w3.org/WAI/tutorials/images/decorative/)：装饰图空替代文本与上下文。
- [CSSOM View 可见性检查草案](https://drafts.csswg.org/cssom-view/#dom-element-checkvisibility)：当前 Chrome 受控测试验证了透明祖先及 content-visibility 隐藏；矩形相交仍不证明无遮挡，复杂叠层需截图复核。
