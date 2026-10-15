---
name: seo-update-url
description: 盘点和持续更新 目标网站 的 URL 与路由资产，合并 Sitemap、站内链接、浏览器及站长平台导出，保留来源、历史差异和未检查范围。用于 updateURL、URL 清单更新、路由盘点；不修改线上路由，不代替完整 SEO 审核。
---

运行前设置 `SEO_SITE_PROFILE=/absolute/path/site.json`。使用 `seo.py init` 为目标站点创建显式配置；主机采用精确白名单，不自动扩展子域。默认使用通用网站规则；`business_profile: "bingx"` 为可选业务扩展，只有明确选择它才启用对应路由和市场参考逻辑。缺少 profile 时不进行线上采集。

默认交付本地报告或问题清单。只有用户明确要求外部发布并指定或确认目的地时，才调用相应飞书/外部工具写入；无需发布时不要求外部账户授权。所有输出、证据和状态库存放在技能目录之外，按站点隔离。示例、fixtures 和既有历史记录仅用于显式选择的离线演练，不自动导入真实报告。浏览器的通用就绪信号仅证明可见正文与有限稳定性，不证明业务实体正确；如提供身份/模板信号则保持这些更强要求。


# 001 · 目标网站 updateURL

使用随附的 Python 工具建立持久资产库。不要临时重写 URL 去重、抓取和历史比对。脚本要求 Python 3.10+，使用标准库；当前支持 macOS／Linux。

## 运行前

1. 定位本技能目录 `SKILL_DIR`；默认数据目录为 `<DATA_DIR>/<SITE_HOST>/update-url`。用户指定的数据目录优先；数据不要放到安装的技能文件夹里。
2. 执行 `status`，确认是否已有资产和未完成 run。已有数据不重新清空。配置优先使用显式 `--profile`，其次已有 `<DATA_DIR>/profile.json`，再使用 `SEO_SITE_PROFILE`；没有配置时停止。主机只使用配置中的 `allowed_hosts`。其他子域先记录为范围外，不因父域授权而自动扩扫。
3. 选择本次范围：只合并来源、更新公开发现、补浏览器链接，或继续某次运行。不要自动打开另两个平台或执行全部 SEO 专项。

命令示例中的 `<SKILL_DIR>`、`<DATA_DIR>`、`<REPORT_DIR>` 需要替换为实际绝对路径；用结构化参数或正确 shell 引号处理路径。

```bash
python3 "<SKILL_DIR>/scripts/update_url.py" status --data "<DATA_DIR>"
```

## 执行

- **合并已有清单／平台导出**：使用 `import`。读取 [来源接入说明](references/sources.md)，按真实来源时间、范围和字段导入。不要把样例标为完整来源。
- **更新公开 URL**：使用 `discover`，程序自动解析 robots、递归 Sitemap，并提取被访问页面中的公开链接、canonical 与语言关联。默认有请求、深度与 Sitemap 上限；更大任务按用户范围调整，保留未完成队列。
- **补充客户端或受工具限制的页面**：用已授权浏览器读取实际页面链接，按 `import-dom` 结构导入。见 [浏览器与来源接入](references/sources.md)。不要绕过登录或防护；一个访问失败不代表页面已下线。
- **恢复**：同一个 run 使用 `--resume`；保持原 profile、深度、Sitemap 与资产上限，只提高总请求预算。失败／受阻的任务通过新一轮重新检查，不能把续跑当作全部重新验证。
- **分类规则升级**：执行 `reclassify --data "<DATA_DIR>"`，刷新已有资产的语言和模板分类，再生成报告。此操作不发网络请求，不重置来源、发现时间或 HTTP 历史。语言路由前缀（例如 目标网站 的 `zh-tc`）仅用于资产分组，不据此判断 hreflang 规范性。

建议先做小批，观察来源变化和请求状态，再扩到更多模板。完整解析一个 Sitemap 文件可能发现很多 URL，并不意味着每个 URL 都已访问。

```bash
python3 "<SKILL_DIR>/scripts/update_url.py" discover --data "<DATA_DIR>" --max-requests 50 --max-depth 1 --max-sitemaps 10 --max-urls 500000
python3 "<SKILL_DIR>/scripts/update_url.py" report --data "<DATA_DIR>" --output "<REPORT_DIR>"
```

`assets/initial-sample-2026-09-16.json` 是仅供显式选择的历史 BingX 样例（114 主样本＋34 条件候选），不是目标网站的资产清单。只有用户明确要求 BingX 历史演练时，才可在隔离数据目录按 historical/sample 导入；通用网站审查不得自动导入。

## 必须保留的区别

- 原始 URL、路由模板、声明 canonical 与实际跳转关系分别保存。`currency`、`type`、大小写和查询顺序不能擅自合并；未知模板保持字面路径并标未分类。
- 发现时间与 HTTP 检查时间不同。导入、Sitemap 收录、浏览器发现、HTTP 200 均不是搜索引擎索引证明。
- `complete` 只表示一个明确来源的完整快照。来源中消失只记 `missing_candidate`，从不删除资产；平台样例没出现不推断下线。
- 不用 Sitemap 自身证明全站完整。未取得 CMS／权威路由总量时，明确称“已发现 URL”，真实全站总量未知。
- 本技能负责资产发现与盘点，TDK、Schema、CWV、Sitemap 质量及修复发布由其他能力处理。提取元信息只是为后续检查保存证据。

## 交付

读取 JSON 输出和退出码：`0` 表示命令完成；`2` 表示部分完成或有拒绝行；`1` 表示执行错误。退出码 0 不代表网站没有问题。错误信息、排队和范围外记录不能丢弃。

生成并检查 `report.md`、`inventory.csv`、`routes.csv`、`languages.csv`、`source-coverage.csv`、`source-snapshots.csv`、`changes.csv`、`relations.csv`、`tasks.csv`、`fetches.csv`、`exclusions.csv` 与 `snapshot.json`。用 [数据合同](references/data-contract.md) 解释数量与状态。

给用户报告：本次新增／来源缺失／重新出现数量、当前已发现页面与技术文件数量、已识别模板与未分类情况、本轮实际请求量、受阻／延期项及报告位置。只在本次具有独立权威全集时讨论全站覆盖率。

用户需要飞书文档时，使用当前可用的飞书文档工具发布本报告并回读验证；此技能不自带或假定飞书凭证。默认交付本地报告，不发送消息、不提交索引、不修改生产路由。

## 验证与维护

修改规则或代码前先添加能复现预期缺陷的失败测试，再实现并运行：

```bash
python3 -m unittest discover -s "<SKILL_DIR>/tests" -v
```

网络取数与后台授权是外部能力，必须通过实际运行验证，不能用离线测试冒充接入完成。版本升级时保留数据目录和全部来源／问题历史。
