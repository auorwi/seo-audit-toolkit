---
name: seo-media
description: 专项核验 目标网站 图片与视频的实际加载、响应式选图、资源响应、CSS 主图和媒体用途，输出证据绑定的修复清单与稳定问题历史。用于坏图、图片返回 HTML、移动端资源、主图懒加载及视频可发现性排查；不把资源声明当加载成功，不替代 CWV 或视频索引核验。
---

运行前设置 `SEO_SITE_PROFILE=/absolute/path/site.json`。使用 `seo.py init` 为目标站点创建显式配置；主机采用精确白名单，不自动扩展子域。默认使用通用网站规则；`business_profile: "bingx"` 为可选业务扩展，只有明确选择它才启用对应路由和市场参考逻辑。缺少 profile 时不进行线上采集。

默认交付本地报告或问题清单。只有用户明确要求外部发布并指定或确认目的地时，才调用相应飞书/外部工具写入；无需发布时不要求外部账户授权。所有输出、证据和状态库存放在技能目录之外，按站点隔离。示例、fixtures 和既有历史记录仅用于显式选择的离线演练，不自动导入真实报告。浏览器的通用就绪信号仅证明可见正文与有限稳定性，不证明业务实体正确；如提供身份/模板信号则保持这些更强要求。


# 013 图片与视频

按用户指定 URL 或 001 的既有资产清单运行本专项。记录 URL、模板、设备、采集阶段与预算；保持原始路由和参数。只读访问授权范围内的公开页面，不展开总入口。Codex 负责实际页面识别和具名用途复核，脚本负责采集、确定性判断、证据绑定和历史去重。

## 工作顺序

1. 检查已有 URL 清单与 013 历史。先覆盖异常 URL、重要模板和代表性媒体页面；移动、桌面分开采集。历史问题是复测线索，不能替代本轮证据。
2. 观察实际主体、实体标题与 loading/error 节点，配置唯一且可见的页面识别信号。`references/templates/` 是已观察的 目标网站 示例，营销标题和选择器可能变化，使用前核对；错误配置不算网站故障。
3. 用 `scripts/collect_page.mjs` 在隔离 Chrome 中读取当前 DOM、`currentSrc`、视口、CSS 背景、图片加载/解码和视频元数据。记录资源真实响应；仅有限读取已知小型且未压缩的图片体。无需登录，不使用个人 Chrome 配置。
4. 查看实际截图、可见正文、媒体节点及响应，对重要图/装饰图/功能图/辅助视频/观看页分别复核。依据 [证据格式](references/evidence-contract.md) 新建具名 review，并绑定整个 capture 文件和截图哈希。无法确认用途时保留未知，不批量猜测。截图只覆盖其实际视口，不能用它宣称评审了屏幕外图片。
5. 如果需要检查屏幕外懒加载或辅助视频，使用已观察到的唯一 `scrollSelector`；采集前后分成两个快照。不点击播放、登录、买入或提交；确需播放器交互时依据用户任务另行限定范围，不能由 HTTP 200 或 iframe 页面推断播放成功。
6. 执行 `scripts/audit_media.py`，查看逐项结果、声明资源、实际选图、缺口和跨技能转交。保持“已观察 / 候选 / 未验证”区分；按实际错误修复路径、资源发布或加载方式，不由单次失败断言整个网站失效。
7. 每轮创建新报告目录并复用持久 state。相同 URL、媒体槽位和规则族更新同一问题历史；多设备证据聚合，未出现不自动关闭。完成本专项后按用户要求继续其他技能，不自动运行全部库。

## 运行

依赖同级已安装的 003 `seo-crawlability`（证据、时间、账本）、006 `seo-semantics`（有界 HTML 声明提取）和 007 `seo-tdk`（页面就绪原语）；不会执行它们的完整审查。Python 使用标准库；浏览器需要现有 `playwright-core` 与 Chrome。先确认真实运行路径。

```bash
node scripts/collect_page.mjs --url 'https://example.com/products/example' \
  --device mobile --config /absolute/path/observed-template.json \
  --runtime /absolute/path/playwright-runtime \
  --browser-executable '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' \
  --output /absolute/path/new-capture

python3 scripts/audit_media.py --manifest /absolute/path/reviewed/manifest.json \
  --state /absolute/path/persistent-media-state --output /absolute/path/new-report
```

采集器分别输出原始 capture、截图、manifest 和事件记录。审查输出 Markdown、JSON、CSV、专业技能转交和持久问题历史。合并多个采集目录时重写 proof 的相对路径，同时保留原始文件与哈希；capture 内截图路径也需保持可解析，不能改 capture 后沿用旧 proof。

默认新鲜度 24 小时；`--max-age-hours` 可明确调整。`--at` 仅用于明确标注的历史证据回放。退出码 0 表示声明的观察范围完成，2 表示有未知或未完成，1 表示输入/执行错误。0 不表示没有发现问题，更不表示全站无问题。

## 关键判断

- `srcset`、`picture/source` 是候选声明，实际选择以 `currentSrc` 为准；保留设备、DPR、视口和阶段，不猜测未选中的资源。
- `complete=true` 也可能是损坏或没有资源；结合实际错误事件、自然尺寸和源绑定的 decode。对未完成的 lazy 图片不主动调用 decode 触发加载。
- HTTP 状态、Content-Type、有限前缀、图片解码是不同层次证据。403/429 是访问限制，超时是未取到；不一律叫死链。iframe 的 HTML 响应正常，但不能证明视频播放或索引。
- 自然尺寸是密度校正后的 CSS 像素，不反推编码像素或传输浪费。缺 width/height 不证明 CLS 超标，首屏重要图懒加载仅转交 011 测量。
- 装饰图空 alt 不误报。功能图名称、信息图描述交给 006；013 保存用途证据，避免重复创建修复任务。信息型 CSS 背景也不必全部改成 img，需先确认它是否确实需要被图片搜索发现以及是否已有等价 img。
- 辅助教程视频不一律要求成为独立观看页。观看页缩略图和标题需结合实际上下文；VideoObject 交给 008，实际引擎视频索引交给 014。
- 一个浏览器/地区样本的失败不推断全球结果；同 URL 独立 HTTP 请求与已解码的浏览器图片冲突时保留差异，不能用前者覆盖后者。

运行 `python3 -m unittest discover -s tests -p 'test_*.py'`；真实浏览器受控测试为 `tests/browser_integration.mjs`，使用 `SEMANTICS_RUNTIME`、`SEMANTICS_CHROME`。受控页面与实际线上证据分开。安装后用同一证据和审查时点回放，比对报告与去重历史。

详见 [证据格式](references/evidence-contract.md) 和 [规则与修复方向](references/rules.md)。
