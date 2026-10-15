---
name: seo-bing
description: 专项读取 目标网站 Bing Webmaster 的索引、实时URL、抓取、SEO建议、Sitemap及既有扫描，逐URL对照线上证据并维护问题历史。用于Bing后台巡查或单页复核；区分旧快照、实时测试、提交记录与当前页面，不把平台建议当成已确认根因。
---

运行前设置 `SEO_SITE_PROFILE=/absolute/path/site.json`。使用 `seo.py init` 为目标站点创建显式配置；主机采用精确白名单，不自动扩展子域。默认使用通用网站规则；`business_profile: "bingx"` 为可选业务扩展，只有明确选择它才启用对应路由和市场参考逻辑。缺少 profile 时不进行线上采集。

默认交付本地报告或问题清单。只有用户明确要求外部发布并指定或确认目的地时，才调用相应飞书/外部工具写入；无需发布时不要求外部账户授权。所有输出、证据和状态库存放在技能目录之外，按站点隔离。示例、fixtures 和既有历史记录仅用于显式选择的离线演练，不自动导入真实报告。浏览器的通用就绪信号仅证明可见正文与有限稳定性，不证明业务实体正确；如提供身份/模板信号则保持这些更强要求。


# 目标网站 015 · Bing Webmaster

独立入口，只检查 Bing 范围。用户指定 URL/问题时按指定范围；否则从当前后台按问题类型、模板、主机与业务重要度选样，分别报告平台数量、取得样例和实际逐页检查数量。不运行总入口或其他站长平台。

Codex 通过已授权浏览器或现有只读连接器采集；Python 负责绑定证据、逐URL比较和去重，不自行登录或获取 API Key。需要 Python 3.10+ 及同级已安装的 `seo-crawlability`，只复用其身份/时间/历史/报告原语。

## 执行

1. 读取 [采集流程](references/collection.md)，核对当前选站和实际 `siteUrl`。目标网站 报表可能包含 www、其他子域或 HTTP 变体，保留原 URL，不把测试/服务子域全部算作主站问题；本地检查范围默认严格前缀，这是工具的范围约束，不是对 Bing 站点归属的通用断言。
2. 保存实际 UI 原文/导出或只读 JSON/HTTP 响应。记录筛选、报告/扫描日期、采集时间、数量单位、源 URL 和 SHA256。按 [输入合同](references/evidence.md) 映射；哈希只证明字节未改变，语义和来源仍由实际读取者核对。没有读到的内容不补造。
3. 对选定 URL 读取 Bing Index，再取同一完整 URL 的当前 GET/浏览器证据；必要时使用单 URL 的 Live URL。保留参数、历史/实时 HTTP 状态和跳转链。设备未展示写 UNKNOWN；可以对照记录，但不能声称网络、地区或客户端条件相同。Live URL 成功、IsPage=true、HTTP 200、提交接受都不证明已经索引。
4. 打开平台保存的 HTML/响应时，先判断它是内容页还是跳转/挑战页。301 跳转正文缺少 title/H1 不应直接当作最终内容页故障；检查完整跳转和目标。页面只显示 Failed 而无 HTTP 码时不得补成 5xx。当天读取旧 Site Scan 不等于今天扫描。
5. 运行相关专业核查：抓取003、路由004、渲染005、语义006、TDK007、结构化008、内链009、语言010、媒体013、Sitemap002。仅执行当前问题所需部分，说明真正执行的步骤与仍待转交部分。平台 High/Warning 不直接映射成业务修复优先级；长度/Meta Language/IndexNow 建议需结合页面用途。
6. 运行审查器，阅读差异、证据缺口与历史，补充根因证据、可执行修复方向和复测方法。底层根因与平台观察分开，未复现保留历史，不自动关闭。

```bash
python3 <skill-dir>/scripts/audit_bing.py \
  --manifest <run-dir>/manifest.json \
  --state <persistent-data>/bing \
  --output <new-report-dir>
```

默认采集时效24小时；旧扫描完成日期另外保留并标明。`--at` 为重放时点；历史重放用 `run_kind=historical_replay`，不能更新采集时间伪装新巡查。输出目录必须新建，state 固定用于跨周去重。

退出码0仅表示声明组合可对照且没有已知证据缺口；2为部分报告，1为输入/运行错误。0不等于网站健康或全部专业项通过。产物为 report.md/json、checks.json、findings.csv、issue-history.json/csv、referrals.json。

## 边界

- 相同站点、完整URL、规则保持问题ID；同一原因跨索引/实时/旧扫描保留不同模式，不重复建档。同一输入和审查时点的重放幂等。修复验收留给017。
- API解析支持五个明确合同，见参考；真实凭据/配额未接通就如实注明。顶部查询/页面数据不是URL资产全集；点击位置与展示位置分别保留，不套用GSC平均位置算法。
- 不点击 Request indexing、Block URL、提交/删除Sitemap、IndexNow提交、修改站点设置或 Start new scan。已有扫描和单URL只读检查可以读取。
- 登录/验证码/锁屏由用户处理；不导出会话凭证、个人浏览器数据库或把API Key保存进证据/报告。
- 飞书发布由018或当次明确的文档操作完成；未执行就不声称同步成功。没有创建定时任务。

测试：`python3 -m unittest discover -s <skill-dir>/tests -v`。
