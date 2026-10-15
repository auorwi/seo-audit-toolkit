> Historical/opt-in BingX example. Apply to generic sites only after replacing URLs, selectors, and business assumptions with current evidence from the selected profile; never auto-import example evidence.

> Portable setup: run the toolkit runtime setup for the required optional capability, and pass its returned runtime/browser paths. Historical version counts below describe source development only; validate on the current machine. Set SEO_SITE_PROFILE explicitly for each run.

# 环境与验证

已验证：Python3.14、Node24.4、Chrome153.0.8010.36、playwright-core1.63.0、extruct0.18.0。Python审查代码仅标准库与同级003；浏览器函数依赖同级007。不要复制整套旧审查来执行008。

当前本机工具：
- extruct Python：`<RUNTIME_DIR>`
- Node runtime：`<RUNTIME_DIR>`（这里只使用playwright-core）
- Chrome：`<CHROME_EXECUTABLE>`
- 状态库建议：`<SITE_DATA_DIR>`

不要对venv的python路径做realpath/resolve再执行：它可能解析成系统Python并丢失venv包。迁移机器时创建新venv，根据[锁定依赖](extruct-requirements.lock.txt)安装，重新做真实提取集成。工具路径和当前机器浏览器权限不能跨机器假设。

```bash
python3 -m unittest discover -s "<SKILL_DIR>/tests" -p 'test_*.py' -v
EXTRUCT_PYTHON="<VENV>/bin/python" python3 "<SKILL_DIR>/tests/extruct_integration.py" -v
SEMANTICS_RUNTIME="<NODE_RUNTIME>" SEMANTICS_CHROME="<CHROME>" python3 "<SKILL_DIR>/tests/browser_integration.py" -v
```

常规147项测试；extruct真实库5项、实际Chromium受控页面6项，明确分开计数。后两组没有运行环境会skip，skip不得报告成通过。集成页面是控制样例，不是BingX线上证据。实际线上验收另存HTML、DOM、可见文本、原生提取及来源校验。

提取worker由调用方限制超时（建议单页60秒）；不要无限等待。Chrome权限失败是采集环境故障，不是BingX SEO错误。输出目录不可覆盖。对于被隐藏/打开新标签的内部链接，当前CLI可能失败；应报告失败并使用真实浏览器完成相应路径，不能强制改成direct后声称internal成功。
