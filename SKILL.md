---
name: mcd-annual-report
description: 麦麦年报 MCD Wrapped —— 一键生成个人麦当劳年度美食报告。拉取麦当劳官方 MCP 的订单、积分、商城兑换与抽奖记录，产出可交互 HTML 年报、原创「麦格」人格标签与分享卡片。当用户说"麦当劳年报/年度报告/麦麦年报/我的麦当劳总结/年度美食报告/MCD Wrapped"时使用。仅调用只读工具，无需手动提供任何数据。
---

# 麦麦年报 MCD Wrapped

把用户的麦当劳消费数据变成一份值得晒的年度报告。

## 何时使用

- 用户想生成自己的麦当劳年度/月度报告
- 用户想了解自己一年在麦当劳花了多少、最爱吃什么
- 用户想获得趣味性的「麦门人格」鉴定与分享卡片

## 前置条件

- 已配置麦当劳 MCP（见 mcp-config.example.json），或已设置环境变量 `MCD_MCP_TOKEN`
- 未配置时，先用 `--demo` 模式体验，并引导用户去 open.mcd.cn/mcp 申请 Token

## 执行流程

1. **确定模式**：有 Token → 真实模式；无 Token → 先用 `--demo` 生成示例报告供预览，并提示申请方式
2. **拉取数据**（只读，串行调用，控制频率）：
   - `order-list` 历史订单
   - `mall-order-list` 商城兑换订单
   - `query-my-account` 积分账户
   - `query-my-prizes` 抽奖记录
   - `list-nutrition-foods` 餐品营养表
3. **生成报告**：运行 `python -m src.cli -o output/mcd-annual-report.html`（可加 `--card` 导出 SVG 卡片）
4. **交付结果**：向用户展示 HTML 报告路径，并说明其中包含：年度总览、年度之最、时间节奏、月度趋势、营养盘点、积分奖品、麦格人格、分享卡片

## 硬性约束（合规）

- **只调用只读工具**，绝不调用 `create-order`、`draw-lottery`、`mall-create-order`、`cancel-order`、`auto-bind-coupons`、`delivery-create-address` 等任何写操作工具
- Token 只从环境变量读取，**绝不把 Token 写入任何文件或输出**
- 报告中必须保留免责声明：非麦当劳官方产品、输出仅供娱乐参考、餐品信息以官方渠道为准
- 不使用麦当劳官方 Logo/商标素材
- 单工具调用失败时降级为空数据继续生成，不得中断整体流程

## 常见问题

- **没有订单数据**：生成空状态引导页，提示接入 Token 后重试
- **401**：Token 无效，引导用户重新申请
- **429**：限流，等待后串行重试，避免并发调用
- **数据字段与文档不符**：解析层已做多候选兼容，以实际返回为准
