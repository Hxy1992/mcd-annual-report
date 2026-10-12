"""分享卡片：生成独立 SVG 版（可直接预览/转图）。

HTML 年报内的 PNG 导出由前端 canvas 完成（见 templates/report.js），
本模块产出的 SVG 用于仓库内预览与测试。
"""

from __future__ import annotations

import html
from pathlib import Path

from .analyzer import YearStats
from .persona import Persona


def render_card_svg(data_nickname: str, persona: Persona, stats: YearStats) -> str:
    esc = lambda s: html.escape(str(s), quote=True)
    highlights = persona.highlights[:4]
    hl_lines = "".join(
        f'<text x="375" y="{560 + i * 52}" text-anchor="middle" font-size="26" fill="rgba(255,255,255,0.92)">{esc(h)}</text>'
        for i, h in enumerate(highlights)
    )
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="750" height="1000" viewBox="0 0 750 1000">
<defs><linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
<stop offset="0" stop-color="#da291c"/><stop offset="0.55" stop-color="#a8121b"/><stop offset="1" stop-color="#6d0d14"/>
</linearGradient></defs>
<rect width="750" height="1000" fill="url(#bg)"/>
<circle cx="645" cy="100" r="255" fill="#ffc72c" opacity="0.14"/>
<text x="375" y="96" text-anchor="middle" font-size="24" font-weight="600" fill="rgba(255,255,255,0.72)" letter-spacing="6">我 的 麦 麦 年 报</text>
<text x="375" y="210" text-anchor="middle" font-size="76" font-weight="800" fill="#ffc72c">{esc(persona.code)}</text>
<text x="375" y="292" text-anchor="middle" font-size="52" font-weight="800" fill="#ffffff">{esc(persona.type_name)}</text>
<text x="375" y="352" text-anchor="middle" font-size="24" fill="rgba(255,255,255,0.85)">{esc(persona.tagline)}</text>
<line x1="70" y1="460" x2="680" y2="460" stroke="rgba(255,199,44,0.55)" stroke-width="2"/>
{hl_lines}
<text x="375" y="870" text-anchor="middle" font-size="20" fill="rgba(255,255,255,0.55)">麦麦年报 MCD Wrapped</text>
<text x="375" y="908" text-anchor="middle" font-size="20" fill="rgba(255,255,255,0.55)">非麦当劳官方产品 · 仅供娱乐参考</text>
</svg>"""


def write_card(data_nickname: str, persona: Persona, stats: YearStats, output: Path) -> Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_card_svg(data_nickname, persona, stats), encoding="utf-8")
    return output
