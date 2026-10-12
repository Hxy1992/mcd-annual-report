"""命令行入口。

用法：
    python -m src.cli --demo             # 示例数据，无需 Token，完整体验
    python -m src.cli --mock             # Mock 传输层，走完整解析链路（测试用）
    python -m src.cli                    # 真实模式：读取环境变量 MCD_MCP_TOKEN
    python -m src.cli -o out/report.html # 指定输出文件

安全约定：Token 只从环境变量 MCD_MCP_TOKEN 读取，绝不写入任何输出文件。
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime
from pathlib import Path

from .aggregator import Aggregator, build_user_data_from_responses
from .analyzer import analyze, empty_state_stats
from .card import write_card
from .demo_data import demo_user_data, mock_tool_responses
from .models import UserData
from .persona import infer_persona
from .report_html import write_report


class MockTransport:
    """用预置响应模拟 MCP 客户端（--mock 模式）。"""

    def __init__(self, responses: dict) -> None:
        self._responses = responses
        self.calls: list[str] = []

    def call_tool(self, name: str, arguments: dict | None = None) -> object:
        self.calls.append(name)
        if name not in self._responses:
            raise RuntimeError(f"mock 中没有工具 {name} 的响应")
        return self._responses[name]


def load_user_data(mode: str) -> UserData:
    if mode == "demo":
        return demo_user_data()
    if mode == "mock":
        return build_user_data_from_responses(mock_tool_responses())
    # 真实模式
    token = os.environ.get("MCD_MCP_TOKEN", "").strip()
    if not token:
        print(
            "[error] 未检测到环境变量 MCD_MCP_TOKEN。\n"
            "  1. 前往 https://open.mcd.cn/mcp 申请 Token；\n"
            "  2. 设置环境变量后重试，或先用 --demo 体验。",
            file=sys.stderr,
        )
        raise SystemExit(2)
    from .mcp_client import McDonaldsMCP

    client = McDonaldsMCP(token)
    return Aggregator(client).collect()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="mcd-annual-report",
        description="麦麦年报 MCD Wrapped —— 你的麦当劳年度美食报告（非官方参赛作品）",
    )
    parser.add_argument("--demo", action="store_true", help="使用示例数据（无需 Token）")
    parser.add_argument("--mock", action="store_true", help="Mock 传输层跑完整链路（测试用）")
    parser.add_argument("-o", "--output", default="output/mcd-annual-report.html", help="HTML 报告输出路径")
    parser.add_argument("--card", default=None, help="分享卡片 SVG 输出路径（可选）")
    args = parser.parse_args(argv)

    mode = "demo" if args.demo else ("mock" if args.mock else "real")
    print(f"[info] 数据模式：{mode}")

    data = load_user_data(mode)
    stats = analyze(data) if data.has_data else empty_state_stats()
    persona = infer_persona(stats)

    out = Path(args.output)
    write_report(data, stats, persona, out)
    print(f"[ok] 年报已生成：{out.resolve()}")

    if args.card:
        card_path = write_card(data.nickname, persona, stats, Path(args.card))
        print(f"[ok] 分享卡片已生成：{card_path.resolve()}")

    if data.has_data:
        print(
            f"[ok] 共 {stats.total_orders} 单 / {stats.total_spend:.1f} 元 / "
            f"麦格：{persona.code} {persona.type_name}"
        )
    else:
        print("[warn] 没有订单数据，已生成空状态引导页（Demo 模式除外，请检查账号订单）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
