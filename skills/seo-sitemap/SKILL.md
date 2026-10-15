---
name: seo-sitemap
description: 专项检查 目标网站 Sitemap 的文件、索引组织、条目与线上状态及独立发布清单的差异，输出五类修复清单与持久问题历史。用于 Sitemap 审核、遗漏或污染排查；不替代 URL 资产盘点，也不自动修改或提交线上文件。
---

运行前设置 `SEO_SITE_PROFILE=/absolute/path/site.json`。使用 `seo.py init` 为目标站点创建显式配置；主机采用精确白名单，不自动扩展子域。默认使用通用网站规则；`business_profile: "bingx"` 为可选业务扩展，只有明确选择它才启用对应路由和市场参考逻辑。缺少 profile 时不进行线上采集。

默认交付本地报告或问题清单。只有用户明确要求外部发布并指定或确认目的地时，才调用相应飞书/外部工具写入；无需发布时不要求外部账户授权。所有输出、证据和状态库存放在技能目录之外，按站点隔离。示例、fixtures 和既有历史记录仅用于显式选择的离线演练，不自动导入真实报告。浏览器的通用就绪信号仅证明可见正文与有限稳定性，不证明业务实体正确；如提供身份/模板信号则保持这些更强要求。


# 002 · 目标网站 Sitemap 检查

使用随附 Python 工具读取实际文件与页面证据。它负责确定性核对，Codex 负责取数、必要的浏览器内容复核和解释业务条件。不要把未取到的文件、旧数据或未知索引意图当成通过。

## 选择输入并更新证据

默认读取 `<DATA_DIR>/<SITE_HOST>/update-url/inventory.sqlite`，问题账本放在 `<DATA_DIR>/<SITE_HOST>/sitemap`。两者分离，002 只读 001。

1. 从用户指定入口或 001 的 profile 获取 Sitemap 根文件，记录本轮入口范围。Sitemap 入口从目标配置的 `sitemaps` 或用户指定位置获取；示例不是真实入口。
2. 如需当前线上检查，使用已安装的 `seo-update-url` 补采。沿用授权主机、robots、限速与系统网络配置；临时 profile 可以设置本轮 Sitemap 和代表页面，避免改写用户长期 profile。文件检查应覆盖所有已取得文件；页面 GET 按实际请求预算单独计数。
3. 需要更全面时扩大 Sitemap 文件预算并继续补采未读文件；001 的请求续跑必须沿用原 scope。001 当前单响应约 8 MB 上限，小于协议的 50 MB；遇到此限制标为采集受限，不能判网站超出协议。可以用已授权工具取得更大文件及 SHA-256，按 [输入合同](references/input-contract.md) 的 manifest 导入。
4. HTTP 200 但怀疑错误正文时，用已授权浏览器逐条复核实际页面，记录错误元素／正文片段与时间。没有该证据，不仅凭“404”等标题字样判断软 404。模型判断通过 `content_verdict` 留痕。

不需要联网或 001 时，也可以使用带本地正文与哈希的独立 manifest。读取 [输入合同](references/input-contract.md)；它说明 CMS／路由预期清单、证据字段和导入边界。

## 执行

把命令中的目录替换为真实绝对路径。`--output` 采用当次报告目录，历史保存在 `--state` 中。

```bash
python3 "<SKILL_DIR>/scripts/audit_sitemap.py" \
  --inventory "<URL_DATA_DIR>/inventory.sqlite" \
  --root https://example.com/sitemap.xml \
  --state "<SITEMAP_DATA_DIR>" --output "<REPORT_DIR>"
```

- 多个根文件重复传 `--root`；默认证据新鲜窗口 168 小时，可用 `--max-age-hours` 明确调整。
- 有独立预期清单时加 `--expected 文件.json`。完整性分母必须来自独立业务清单，且 `scope_roots` 与本轮一致；否则保持未知／候选。
- 只有已经核实跨站提交配置的主机才传 `--cross-site-host`。URL 资产库允许访问某子域，不等于已证明跨站 Sitemap 提交合法。
- 使用其他工具取得的证据时，以 `--manifest 文件.json` 替代 `--inventory`。

## 判读与交付

读取 `report.json` 的 coverage、findings、ledger 和返回码。0 表示已执行所选文件／页面范围，2 表示仍有未核验或未知项，1 表示输入或执行失败。0 不代表没有缺陷或全站完整。

交付 `report.md` 与五类清单：`add.csv`、`remove.csv`、`retarget.csv`、`repair.csv`、`confirm.csv`。附 `findings.csv`、`files.csv`、`memberships.csv`、`pending.csv` 与 `issue-history.json` 供逐项核对。问题 ID 跨周稳定，重复输入不增重复快照，未再观察不自动关闭。

每项方案包括准确 URL／文件、记录时间、证据、影响范围、处理条件和复测方法。分别报告确认缺陷、候选冲突与证据缺口的数量，不把后者合称网站故障。必要时按模板和语言汇总影响，但只计实际条目。

严格保留以下区别：

- 旧 `lastmod` 不等于过期，HTTP 404 不自动证明业务退役，403／429／5xx 不自动建议移除。
- Sitemap 中的 canonical 冲突先核对实体、语言及业务参数；不能直接删除 `currency` 参数或规范到另一语言。
- Google 不支持索引嵌套；检查器可以递归读取，是为了定位证据，不代表引擎支持该组织方式。
- 预期缺失只针对指定入口的可达集合。文件未读齐、预期来源不独立或范围不一致时，只输出候选。
- 元数据、HTTP 与实际索引状态分开；本技能不提交索引、不启动平台扫描、不发布修复。

具体规则和证据强度见 [规则与限制](references/rules.md)。用户要求飞书时，使用可用且已授权的飞书工具发布并回读；本包不存储飞书或站长平台凭证。

## 开发验证

修改前添加复现缺陷的失败测试，再实现并运行：

```bash
python3 -X dev -W error -m unittest discover -s "<SKILL_DIR>/tests" -v
```

要求 Python 3.10+，macOS／Linux，标准库运行。真实平台读取与网站访问必须另有实测记录，不能由离线测试代替。
