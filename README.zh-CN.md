# Codex SEO 检测工具包

[English](README.md) · [安装说明](docs/installation.md) · [模块能力与限制](docs/capabilities.md)

包含 **18 个 SEO 专项技能**，以及 `seo-setup` 配置入口和 `seo-audit` 检测入口。配置自己的目标网站后，可以在 Codex 中检查页面、保存真实证据、汇总问题和复测修复。

## 安装

需要 Codex 和 Python 3.10+。支持目标为 macOS／Linux；Windows 路线是在 WSL2 中运行 Codex CLI、Python 和 Node，本版本不支持原生 Windows。浏览器检查还需要 Node.js 20+ 和 npm。Codex 账号或模型访问由使用者自行准备。

从 [Releases](https://github.com/auorwi/seo-audit-toolkit/releases) 下载 ZIP 并解压，或者：

```bash
git clone https://github.com/auorwi/seo-audit-toolkit.git
cd seo-audit-toolkit
python3 install.py
python3 seo.py doctor
python3 seo.py init --site https://example.org/
```

把示例域名换成自己的网站。最后一条命令会返回网站配置文件的位置；每个网站有单独的数据目录。需要子域名时，通过 `--allow-host` 明确添加，或编辑配置的 `allowed_hosts`。

安装器将完整程序保存到用户自己的数据目录，并把技能链接到 `~/.agents/skills`。如果 Codex 还没有发现新技能，新建一个聊天。然后可以直接说：

> 使用 $seo-audit，按我的网站配置检查标题、内链和 Sitemap，最多访问 10 个页面请求，报告保存在本地。

## 第一次检查

无需安装浏览器或登录飞书，即可运行基础 HTTP 检查：

```bash
python3 seo.py audit --profile /绝对路径/profile.json --max-pages 10 --max-requests 40
```

结果包含 Markdown 报告、CSV 问题清单、JSON 记录、原始响应证据和网站历史。**基础命令只检查初始 HTML，不等于完成全部 18 个专项。** 针对 JavaScript 渲染、结构化数据、性能或站长平台的要求，Codex 会按技能说明执行对应专项，并列出缺失的证据。

## 按需安装附加能力

```bash
python3 seo.py setup --extras browser
python3 seo.py doctor --probe-browser
python3 seo.py setup --extras structured cwv
```

- `browser`：Playwright、axe-core 和隔离 Chromium；也可通过 `--system-browser` 指定已有浏览器。
- `structured`：Microdata／RDFa 提取所需的 extruct 独立 Python 环境。
- `cwv`：Lighthouse CI 实验室性能采集依赖；还需要可用浏览器。

Linux 缺少浏览器系统库时，需要按 [安装说明](docs/installation.md) 补齐。安装后通过真实浏览器探测，才能说明运行环境可用。

GSC、Bing、Yandex 需要使用者自己的权限、导出或授权工具。飞书仅为可选输出渠道；没有这些账号，不影响公开页面检查和本地报告。行情接口、交易路由等原始 BingX 业务规则只在显式选择对应配置时启用。

## 升级、卸载和测试

下载新版本后再次执行 `python3 install.py`。已有非本工具包管理的同名技能会导致安装停止，不会被覆盖。升级保留旧程序版本、网站数据和依赖环境。

```bash
python3 install.py --uninstall
python3 seo.py test
```

卸载命令仅注销本工具包管理的技能链接；数据、依赖和程序版本副本会保留，便于恢复和自行清理。

检测报告区分问题、待确认、未完成和未检查。退出码 `0` 表示该操作完成，不代表全站没有问题。测试报告分别列出失败与跳过；实际验证范围见 [验证记录](docs/validation.md)。

原始代码采用 MIT 许可；第三方资料保留独立许可证。安装包不包含个人凭据、浏览器会话或实际网站检测台账。
