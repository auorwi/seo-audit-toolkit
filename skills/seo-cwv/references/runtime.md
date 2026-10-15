> Historical/opt-in BingX example. Apply to generic sites only after replacing URLs, selectors, and business assumptions with current evidence from the selected profile; never auto-import example evidence.

> Portable setup: run the toolkit runtime setup for the required optional capability, and pass its returned runtime/browser paths. Historical version counts below describe source development only; validate on the current machine. Set SEO_SITE_PROFILE explicitly for each run.

# 运行方法

Python审查依赖同级003证据/账本模块。性能主工具为官方@lhci/cli 0.15.1，依赖Lighthouse12.6.1；当前固定Chrome153.0.8010.36、Node24.4、Python3.14。运行时位于 `<RUNTIME_DIR>`，元数据见其上级tools.json，依赖锁随包保存为package-lock.json。版本改变须重新跑兼容性与受控实测，再建立新基线。

urls.json可为URL数组或含url字段的对象数组。默认设备mobile与desktop、每单元3次。冷配置使用storage reset，模拟节流固定：移动rtt150ms/1638.4Kbps/CPU×4；桌面rtt40ms/10240Kbps/CPU×1；实际完整配置以plan.json和每份LHR为准。这是仿真配置，不声称等同所有真实手机。

Lighthouse的locale=en-US是审计报告语言，不能当成浏览器Accept-Language或navigator.language的取证。当前采集器没有独立记录后二者，也没有证实实际出口地区；页面语言和落地路由以实际LHR及截图为准，跳到别的语言/业务页面时先排除目标基线。若后续要比较地区/语言配置，需补充明确的请求/浏览器语言与出口证据，另建基线。

仅运行lhci collect，不调用autorun或upload。hook依赖固定版本LHCI内部runner，在每次真实子进程执行时保存开始、成功或错误，补足上游重试只保留最终结果的缺口。不要设置LHCITEST_MOCK_LHR等模拟环境变量；采集器会清除LHCI/LHCITEST前缀的继承配置，使用显式计划。

`--plan-only`只生成计划与空的待采集矩阵，不能视为测量完成。`--resume`要求URL、设备、工具路径/版本、环境与计划哈希相同，跳过已保存cell。预算到期未开始的单元可续跑；已失败或中断的单元保留原始文件并先审查，补测使用新目录/manifest合并，不能覆盖或删除旧结果。字段抓取每调用仅发一次请求，不在429后自动重复耗配额。

每单元启动前检查1分钟主机load/逻辑CPU；超过2或缺数据时退出2并保存暂停事件，整个expected_cells清单保留。机器恢复后可续跑尚未采集的单元；此前受高负载污染的测量不能混入新的干净基线，应另建目录重测相应范围。load不等于CPU使用率，该门禁是保守的工程规则；本机其他任务仍需操作者协调。不要为了完成次数而提高阈值、关闭未知进程或删掉异常记录。

性能锁使用fcntl，适合本机macOS/Linux；Windows需替换锁实现后重测。运行环境路径需按设备重定位。本机Chrome启动可能需要当前环境的执行批准，但不用修改个人Chrome用户资料或调试配置。DevTools MCP当前连接不可用时，本skill继续以独立LHCI和已有原始数据工作；交互trace缺口保留，不伪装采集成功。

正常超时和一次用户中断会先识别本次测量的下属进程组（含Chrome另建的进程组），请求终止并保留已有输出与cell.json，再释放锁；已退出进程的竞态不会丢弃输出。进程发现失败会记录cleanup警告；共享外部进程组不会整组终止。系统强杀/断电可能留下未完成目录，不能声称自动恢复所有崩溃场景，也不要直接删除证据继续凑样本。中断后可用相同计划的--resume --plan-only刷新已有cell清单，再审查与补测。

测试入口：
```bash
python3 -m unittest discover -s "<SKILL_DIR>/tests" -p 'test_*.py' -v
CWV_RUNTIME="<LHCI_RUNTIME>" CWV_CHROME="<CHROME>" python3 -m unittest discover -s "<SKILL_DIR>/tests" -p runtime_integration.py -v
python3 -m unittest discover -s "<SKILL_DIR>/tests" -p field_http_integration.py -v
python3 -m unittest discover -s "<SKILL_DIR>/tests" -p runner_process_integration.py -v
```

runtime_integration使用真实LHCI/Chrome与本地200/404页面，field_http_integration使用本地200/429服务。需要允许本地端口与浏览器执行；这些是受控测试，不是BingX线上故障证据。线上测量另行保留原始LHR、每次尝试与环境，不能把受控测试数字写进真实巡查报告。
