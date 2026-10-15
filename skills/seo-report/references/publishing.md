# 飞书发布与故障恢复

默认交付本地报告。本参考及 publish/adopt 仅在用户明确要求飞书发布并指定或确认目的地后适用；没有此请求时不创建或更新远程文档，也不要求飞书授权。

发布顺序：持续台账 → 本轮报告 → 固定入口。固定入口保留以前每轮链接；台账按来源技能与ID哈希桶分块更新，每问题只有一行。飞书不存完整大型原始HTML；摘要说明截断，原结构在本地report.json及源报告里。

使用用户身份：lark-cli docs +create/+fetch/+update --as user。XML经转义后stdin传入，不使用shell拼接。文档/块标记只用于查找，成功必须比较完整规范化文本和href目标。非零退出、ok=false、partial_success/failed均不当成功。

publication-state.json独立保存已知URL、内容签名、写入前pending日志；publish.lock防同目录并发。不可变report的run_id不能复用来发布不同内容。升级脚本导致格式变化也要使用新run_id，原文档不覆盖。持久台账仅替换本技能创建的块，人工追加块保留；人工修改生成块或删除标记后停止，不能覆盖手工工作。

创建响应不确定时，保持pending，绝不盲目新建。用飞书搜索/已授权浏览器定位标题与SEODOC标记，确认是本次创建的文档，再执行：

```bash
python3 "<SKILL_DIR>/scripts/report_seo.py" adopt --key "ledger" \
  --url "https://<tenant>.feishu.cn/docx/<token>" --state "<PERSISTENT>/report"
```

key也可为entry或report-<run_id>。adopt会读取验证文档标记，仅允许接管未知URL的pending创建，不接受任意已有文档。

插入/替换超时后重跑：若回读已是完整目标内容，标记成功且不重写；否则停止人工核对。不能因为一次读取暂未见块就重发写入。无需用户反复授权已授权范围内的正常读写；登录/权限确实失效时只请求必要授权。保存错误日志在state/private-logs，仅本地排错，不打包账户信息。

源码测试里的Remote仅为故障模型；真实验收应首次发布后以同一文件再次发布，验证文档数/块内容及写操作数不增加。不要为测试创建垃圾文档后再删；对用户实际需要的产物执行验收。
