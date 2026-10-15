> Historical/opt-in BingX example. Apply to generic sites only after replacing URLs, selectors, and business assumptions with current evidence from the selected profile; never auto-import example evidence.

> Portable setup: run the toolkit runtime setup for the required optional capability, and pass its returned runtime/browser paths. Historical version counts below describe source development only; validate on the current machine. Set SEO_SITE_PROFILE explicitly for each run.

# 环境与测试

验证环境Python3.14、Node24.4、Chrome153.0.8010.36、playwright-core1.63.0。Python审查依赖同级003；浏览器采集仅复用同级007的readiness函数，不运行Nu/axe。

本机runtime：`<RUNTIME_DIR>`；Chrome：`<CHROME_EXECUTABLE>`。其他机器先验证路径和依赖，再运行集成测试。

```bash
python3 -m unittest discover -s "<SKILL_DIR>/tests" -p 'test_*.py' -v
SEMANTICS_RUNTIME="<NODE_RUNTIME>" SEMANTICS_CHROME="<CHROME>" python3 "<SKILL_DIR>/tests/browser_integration.py" -v
```

139项常规测试；7项真实Chrome受控页面/本机HTTP链测试。缺少环境会skip，不能把skip说成通过。受控页面不是BingX线上证据；实际验收保存独立文件。HTTP跳转测试使用临时本机服务器，外部fixture域被代理阻断的失败记录已保留。

浏览器可能因执行沙箱而无法启动，按当前Codex权限机制处理；这不是网站问题。每次使用新输出目录。集成测试单次子进程上限60秒；线上页面采集每阶段默认30秒，不无限等待。分页涉及多个阶段，因此整个CLI可能较长。

目标响应采集仅覆盖实际访问的公开页面/跳转链，不自动验证提取到的所有链接。扩展巡查应从001库存和本次高优先级发现选择目标，限速分批采集，再合并带proof的HTTP证据。未采集目标照实报告。
