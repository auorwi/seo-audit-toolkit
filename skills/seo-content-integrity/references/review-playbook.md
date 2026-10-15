> Historical/opt-in BingX example. Apply to generic sites only after replacing URLs, selectors, and business assumptions with current evidence from the selected profile; never auto-import example evidence.

# 012 复核方法

## 从旧线索到新证据

历史 SEO-04 涉及 XRP 供应量、方向词与负值、BTC/NEU 预测年份、OCEANS/EUR 换算与更新时间、WRESTLER/NXM/ALEO 状态等。这是抽样入口，不是当前故障列表。每次重新访问并记录本轮时间、实际最终 URL 和字段原文；未访问、重定向或未加载完整的页面留在缺口里。

1. 同一模板选主要资产、极小价格资产、缺数据资产和生命周期异常资产；分别保留独立实体与市场。
2. 对数值比较，先写字段定义再写判断。比如两个字段都明确声称 circulating supply，可以检查同页表达；若一项实际是 total supply，应修标签或解释，不能为了数值相同而修改业务数据。
3. 对预测页，读取当前增长率和完整年份表，按年份构造观察。测试 1%、2%、5% 时必须实际改变输入并确认 UI 生效，不能仅改 review 中的 scenario。未完成切换时只报告已观察情景。
4. 对换算器，输入数量与输出变化是两个事实。输出保持 0 可能由汇率缺失、舍入或计算逻辑引起；没有有效汇率不得擅自认定算错。极小值向 0 舍入列精度问题；非法 `E`/NaN 等列格式问题并附实际文本。
5. 对实时宣传，记录对应更新时间及页面时区。不能把静态历史表的旧日期当实时过期。对长时间旧数据加实时标签的组合，建议显示数据不可用/最后更新时间并检查缓存与资产状态，根因需要数据链路确认。
6. 对上架文案，只比较相同实体、相同产品、相同市场的状态。预市场活动结束与普通现货可交易不互相否定；教程 buy CTA 与实际已上市不同。交易权限、地区可用性与法律合规不从公开单页推断。

## 工程修复验收

要求数据契约明确字段语义、单位、时间戳、缺失态和精度；模板中的数值、标签与摘要从同一声明对象生成。预测摘要引用按年份索引的表数据。换算器对双向输入、极小值、大数、缺数据和加载/失败态做回归。修复后用相同样本重新获取证据，核对内容与交互；未复现只是本轮观察，不自动关闭历史问题。

## 依据与参考

- [Python Decimal](https://docs.python.org/3.14/library/decimal.html)：十进制精度、上下文和舍入。没有采用二进制 float 比较金融展示值。
- [BingX 官方公开行情接口资料](https://github.com/BingX-API/api-ai-skills/blob/main/skills/spot-market/api-reference.md)：仅作现货市场/单位/时间语义参考，未运行其交易能力。真实接口返回及适用市场仍需验证；API 失败或缺少交易对不是全站下架证据。

这是 Technical SEO 的内容一致性检查，不构成投资预测或交易建议，也不能承诺搜索引擎采用页面声明。
