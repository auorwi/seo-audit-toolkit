> Historical/opt-in BingX example. Apply to generic sites only after replacing URLs, selectors, and business assumptions with current evidence from the selected profile; never auto-import example evidence.

> Portable setup: run the toolkit runtime setup for the required optional capability, and pass its returned runtime/browser paths. Historical version counts below describe source development only; validate on the current machine. Set SEO_SITE_PROFILE explicitly for each run.

# 运行与测试

Python 3.10+，同级seo-crawlability v1.0.1+。Node浏览器采集需要playwright-core及Chromium，安装在技能目录外；不需要axe或Nu。

本机已验证运行时可以复用 `<RUNTIME_DIR>` 中的playwright-core1.63.0。尽管目录也安装了axe，007不会加载它。浏览器 `<CHROME_EXECUTABLE>`，Node24.4。运行时不包含在技能zip中；其他机器自行配置相同能力的官方依赖，不硬编码本机路径。

常规测试不联网：`python3 -m unittest discover -s "<SKILL_DIR>/tests" -v`。

真实浏览器受控用例（本地页面，不等于BingX线上）：

```bash
SEMANTICS_RUNTIME="<NODE_RUNTIME_DIR>" SEMANTICS_CHROME="<CHROME_PATH>" python3 "<SKILL_DIR>/tests/browser_integration.py" -v
```

变量名沿用006已配置环境，测试不调用006。未配置浏览器会skip，不能把skip算通过。浏览器使用临时profile；有些沙箱禁止Chrome启动，需要允许该只读测试的进程权限，不能把环境启动失败登记为网站问题。Chrome退出偶尔需约30秒，测试进程预算60秒，页面预算独立。

新增行为先观察测试失败，再实现、回归。现场验收要保留manifest、HTML、上下文、采集时间、日志和实际结果，不能以fixture冒充线上证据。安装后再次测试并比对文件哈希。
