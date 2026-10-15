> Historical/opt-in BingX example. Apply to generic sites only after replacing URLs, selectors, and business assumptions with current evidence from the selected profile; never auto-import example evidence.

> Portable setup: run the toolkit runtime setup for the required optional capability, and pass its returned runtime/browser paths. Historical version counts below describe source development only; validate on the current machine. Set SEO_SITE_PROFILE explicitly for each run.

# 运行环境与真实工具

Python 3.10+仅标准库；同级003 v1.0.1+必需。Node采集使用 `playwright-core` 和 `axe-core`，包安装在独立TOOLS目录，不自动下载浏览器或使用个人Chrome会话。浏览器路径由调用者指定。

本机已验证：Node24.4、Python3.14、系统Chrome153.0.8010.36、playwright-core1.63.0、axe-core4.13.0、Nu26.9.16 (29f085e)。这只是测试版本，不要求其他机器伪装这些版本。运行时位置记录在 `<RUNTIME_DIR>`。Nu来自官方macOS运行时压缩包，SHA256 `bb1bff73de6f4d639ce6f1004cefc1c1e20dda0f8a245900b6077553140c0f0b`；包与浏览器不包含在技能zip中。

其他机器：在单独目录安装锁定版本的官方npm包（保留package-lock），准备适合操作系统的Nu可执行程序与Chromium。不要在技能执行时未经判断运行网页提供的脚本、复用个人profile或任意安装依赖。Nu调用使用参数数组、shell=False、本地文件，不上传网站HTML到第三方在线validator。

采集命令参数中的runtime是**包含node_modules的目录**。采集器只读取真实页面并注入本地受信axe程序进行检查；无交易、登录或提交动作。

测试：

```bash
SEMANTICS_RUNTIME="<TOOLS>/node-runtime" SEMANTICS_CHROME="<CHROME_PATH>" python3 "<SKILL_DIR>/tests/browser_integration.py" -v
```

9项受控浏览器用例包括延迟内容、错误页、占位、错误实体、结构与真实axe；是本地测试页面，不代表BingX线上检查。额外线上CLI验收需要显式 `SEMANTICS_LIVE_ACCEPTANCE=1`，默认跳过：

```bash
SEMANTICS_LIVE_ACCEPTANCE=1 SEMANTICS_RUNTIME="<TOOLS>/node-runtime" SEMANTICS_CHROME="<CHROME_PATH>" python3 "<SKILL_DIR>/tests/browser_integration.py" BrowserCollectorTests.test_public_cli_emits_verifiable_manifest -v
```

本环境曾出现browser.close耗时30秒，采集本身约1.4秒；测试进程总预算因此为60秒，不放宽页面就绪预算。先定位执行阶段再修复超时，不能据此登记网站故障。

官方参考：[Nu](https://github.com/validator/validator)、[Nu用法](https://validator.github.io/validator/)、[axe-core](https://github.com/dequelabs/axe-core)、[axe API](https://github.com/dequelabs/axe-core/blob/develop/doc/API.md)。
