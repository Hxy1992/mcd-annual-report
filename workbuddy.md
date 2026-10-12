# workbuddy.md — WorkBuddy 开发上下文存档

> 本文件记录「麦麦年报 MCD Wrapped」使用腾讯 WorkBuddy 智能体开发的完整过程，用于麦当劳程序员创意开发大赛 WorkBuddy 专项奖励核验。
> 开发时间：2026-10-12（赛事报名窗口内）

## 一、开发方式声明

本项目（含需求分析、架构设计、全部源代码、测试、文档与配图）由参赛者使用 **WorkBuddy**（腾讯智能体工作台）辅助开发完成：

- 赛事调研：WorkBuddy 抓取微信公众号推文、官方赛事仓库 README/活动规则/参赛声明/排行榜、MCP 官方文档、500+ 个报名 Issue，完成竞品分析
- 架构设计与编码：WorkBuddy 生成全部 Python 源码（约 1200 行）与 HTML/CSS/JS 报表模板
- 测试：WorkBuddy 编写并运行 21 个离线单元测试，全部通过
- 配图：WorkBuddy 通过浏览器自动化对 Demo 报告逐屏截图，产出 README 所用全部预览图

## 二、开发过程实录

### 阶段 1：赛事调研与头脑风暴（2026-10-12 上午）

WorkBuddy 完成的信息收集：

1. 微信公众号「通往AGI之路」推文（正文为海报，下载原图存档）
2. 官方赛事仓库 `M-China/mcd-developer-innovation-challenge`：
   - README（参与方式、必交文件清单、Issue 报名格式）
   - activityGuidelines.md（完整活动规则：时间线/排名/奖励/合规红线）
   - CONTEST_DECLARATION.md（官方参赛声明，原文件下载）
   - RANKING.md（排行榜快照：#1 175★，第 100 名 4★）
3. MCP 官方仓库 `M-China/mcd-mcp-server`：接入方式、33 个工具清单、限流规则
4. 竞品 Issue 区：500+ 报名项目的创意方向扫描

关键判断：省钱/营养/派对/人格赛道严重同质化；「个人年度报告」需求已被 Spotify Wrapped/网易云年度报告验证，但参赛作品最高仅 11★ 且实现简陋 → 确定「麦麦年报」方向。

### 阶段 2：架构设计（2026-10-12 下午）

WorkBuddy 设计的分层架构（纯标准库、零第三方依赖）：

```
cli.py ──▶ mcp_client.py ──▶ aggregator.py ──▶ analyzer.py ──▶ report_html.py
   │            │                  │                │               │
 demo/mock   Streamable HTTP    防御式字段解析     统计计算       单文件 HTML
 双模式      + 限流退避         + 稳定数据模型     + 麦格人格      + 内联 CSS/JS
```

核心设计决策（均由 WorkBuddy 提出并实现）：

1. **只读优先**：只用 order-list / mall-order-list / query-my-account / query-my-prizes / list-nutrition-foods / now-time-info 六个只读工具，从设计上杜绝误下单，合规零风险
2. **防御式解析**：官方文档无字段级 schema（社区 issue #16 反馈文档与实测有出入），聚合层对每个字段做多候选名兼容（camelCase/snake_case/嵌套包裹）
3. **Demo/Mock 双模式**：无 Token 用户可用示例数据完整体验；Mock 模式让完整解析链路可离线测试
4. **数据烘焙进 HTML**：Python 侧渲染全部内容，JS 只做动画增强，禁用 JS 也完整可读
5. **分享卡片双实现**：SVG（Python 生成，仓库预览用）+ canvas（浏览器内导出 PNG，用户晒图用）

### 阶段 3：实现与测试（2026-10-12 下午至晚间）

WorkBuddy 实际执行的开发动作：

| 动作 | 产出 |
|---|---|
| 编写数据模型 | `src/models.py`（Order/OrderItem/MallOrder/PointsInfo/Prize/Nutrition/UserData） |
| 编写 MCP 客户端 | `src/mcp_client.py`（JSON-RPC over Streamable HTTP、SSE 解析、401/429 处理、指数退避） |
| 编写聚合层 | `src/aggregator.py`（6 个工具的响应解析 + 多候选字段兼容） |
| 编写计算引擎 | `src/analyzer.py`（月度趋势/时段分布/TOP 排行/营养汇总/趣味换算） |
| 编写人格模型 | `src/persona.py`（四维 16 型 + 原创文案，避开 MBTI 商标） |
| 编写报表生成器 | `src/report_html.py` + `src/templates/report.css` + `src/templates/report.js`（9 屏 Wrapped 式年报） |
| 编写分享卡片 | `src/card.py`（SVG 版） |
| 编写 CLI | `src/cli.py`（--demo / --mock / 真实模式 / --card） |
| 编写测试 | `tests/test_pipeline.py` 21 个用例，`python -m unittest discover -s tests` 全绿 |
| Demo 数据调优 | 修正「本命餐品是可乐」「人格标签与时段分布矛盾」两处演示数据问题，使四维标签与数据自洽 |
| 浏览器截图 | 通过 playwright-cli + Edge 以 414×896 移动视口逐屏截图 9 张，产出 README 预览图 |

### 阶段 4：联调待办（需参赛者本人参与）

- 申请 MCP Token（open.mcd.cn/mcp）后设置环境变量 `MCD_MCP_TOKEN`
- 以真实 Token 运行 `python -m src.cli`，核对真实返回字段与解析层兼容性（如字段名与预期不符，按 aggregator 的多候选机制补充候选名）
- 确认报名 Issue 提交（赛事仓库，格式见 01-赛事速览.md）

## 三、WorkBuddy 使用小结

- **效率**：从零到可运行、可测试、有配图的完整参赛项目，单日完成（约 8 小时工作量压缩为一次会话）
- **质量保障**：测试先行思维——每个模块配离线测试；浏览器实测截图替代"我觉得没问题"
- **人机分工**：WorkBuddy 负责调研、编码、测试、文档；参赛者负责账号凭证（Token/GitHub）、合规决策与最终提交

---

_本文档由 WorkBuddy 辅助生成，内容真实反映开发过程。_
