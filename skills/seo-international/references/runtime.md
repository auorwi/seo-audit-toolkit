> Portable setup: run the toolkit runtime setup for the required optional capability, and pass its returned runtime/browser paths. Historical version counts below describe source development only; validate on the current machine. Set SEO_SITE_PROFILE explicitly for each run.

# 运行与验证

审查使用Python标准库；须同级安装003 `seo-crawlability`、009 `seo-internal-links`。浏览器采集须同级007 `seo-tdk`，以及Node、playwright-core、Chrome。不会自动运行这几个完整技能。

当前环境已验证：Python3.14、Node24.4、playwright-core1.63.0、Chrome153.0.8010.36。运行时清单位于 `<RUNTIME_DIR>`。审查状态建议 `<SITE_DATA_DIR>`。移机须重定位运行时与浏览器，不能把本机路径当跨机依赖安装器。

```bash
python3 -m unittest discover -s "<SKILL_DIR>/tests" -p 'test_*.py' -v
SEMANTICS_RUNTIME="<NODE_RUNTIME>" SEMANTICS_CHROME="<CHROME>" python3 -m unittest discover -s "<SKILL_DIR>/tests" -p browser_integration.py -v
```

受控浏览器测试使用真实Chrome和本地HTML，验证等待、可见正文、字段、真实点击和快照绑定；不是线上问题证明。线上采集另存原始HTML、DOM、HTTP元数据、浏览器正文、配置及复核输入。沙箱限制Chrome启动时使用当前环境批准的隔离浏览器执行方式。

采集器拒绝公开站点白名单之外的起始URL、带凭据URL和非HTTPS地址；不登录、不购买、不改生产配置。访问失败保留已采集阶段和collection.json，不以旧成功代替本次失败。hash绑定保障文件一致性，不认证模型判断或平台实际采纳。

报告退出2是保留证据缺口和待审结论的正常结果。历史账本使用003已测试原语，稳定问题ID包含010规则、URL及目标/字段维度；同一执行幂等，新增观察累计，缺少本轮证据不关闭问题。
