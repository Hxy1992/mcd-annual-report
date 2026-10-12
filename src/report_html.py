"""交互式 HTML 年报生成器：把统计结果渲染成单文件 HTML。

- 所有数据在 Python 侧烘焙进 HTML（无 JS 也完整可读）；
- JS 只负责滚动显现、数字滚动、条形图生长与分享卡片导出；
- CSS/JS 模板在 src/templates/ 下维护，构建时内联，保证单文件离线可用。
"""

from __future__ import annotations

import html
import json
from datetime import datetime
from pathlib import Path

from .analyzer import SLOT_ORDER, YearStats
from .models import UserData
from .persona import Persona

TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"

MONEY = lambda v: f"¥{v:,.1f}"


def esc(s) -> str:
    return html.escape(str(s), quote=True)


def _bar_rows(time_slots: dict) -> str:
    mx = max(time_slots.values()) if time_slots else 0
    rows = []
    for name in SLOT_ORDER:
        c = time_slots.get(name, 0)
        w = round(c / mx * 100) if mx else 0
        rows.append(
            f'<div class="bar-row"><span class="lb">{esc(name)}</span>'
            f'<span class="track"><span class="fill" data-w="{w}"></span></span>'
            f'<span class="val">{c}</span></div>'
        )
    return "".join(rows)


def _month_bars(monthly) -> str:
    mx = max((m.orders for m in monthly), default=0)
    cells = []
    for m in monthly:
        h = round(m.orders / mx * 100) if mx else 0
        cells.append(
            f'<div class="m"><span class="b" data-h="{h}" title="{m.orders}单"></span>'
            f'<span class="t">{m.month}月</span></div>'
        )
    return "".join(cells)


def _top_list(items: list[tuple], unit: str = "件") -> str:
    lis = []
    for i, (name, qty, spend) in enumerate(items[:5], 1):
        lis.append(
            f'<li><span class="rank">{i}</span><span class="grow">{esc(name)}</span>'
            f'<span class="v">{qty}{unit} · {MONEY(spend)}</span></li>'
        )
    return "".join(lis)


def _nutrition_rows(n) -> str:
    eq = n.fun_equivalents()
    rows = [
        ("总热量", f'{n.as_dict()["energy"]:,.0f}', "kcal", f'≈ {eq["rice_bowls"]} 碗米饭'),
        ("蛋白质", f'{n.as_dict()["protein"]:,.0f}', "g", f'≈ {eq["eggs"]} 个鸡蛋'),
        ("脂肪", f'{n.as_dict()["fat"]:,.0f}', "g", "快乐来源"),
        ("碳水", f'{n.as_dict()["carbs"]:,.0f}', "g", "幸福燃料"),
        ("钠", f'{n.as_dict()["sodium"]:,.0f}', "mg", f'≈ {eq["salt_grams"]} g 盐'),
        ("钙", f'{n.as_dict()["calcium"]:,.0f}', "mg", f'≈ {eq["milk_cups"]} 杯牛奶'),
    ]
    lis = []
    for name, v, unit, note in rows:
        lis.append(
            f'<li><span class="rank">{esc(name)}</span><span class="grow" style="opacity:.65;font-size:13px">{esc(note)}</span>'
            f'<span class="v">{v} {unit}</span></li>'
        )
    return "".join(lis)


def _prize_list(prizes: list[dict]) -> str:
    if not prizes:
        return '<li><span class="grow" style="opacity:.65">今年还没有抽奖记录，去试试手气吧</span></li>'
    lis = []
    for p in prizes[:6]:
        when = p.get("won_at") or ""
        lis.append(
            f'<li><span class="rank">🎁</span><span class="grow">{esc(p.get("name", ""))}</span>'
            f'<span class="v" style="font-weight:500;opacity:.7">{esc(when)}</span></li>'
        )
    return "".join(lis)


def _empty_pages(data: UserData, stats: YearStats) -> str:
    return f"""
<section class="page p-cover">
  <div class="kicker">MCD WRAPPED</div>
  <h1 class="title">麦麦年报</h1>
  <p class="subtitle">你好，{esc(data.nickname)}<br>这一年，你的麦麦故事还没开始书写</p>
  <div class="scroll-hint">下滑看看怎么开始 ↓</div>
</section>
<section class="page p-light">
  <div class="kicker reveal">EMPTY STATE</div>
  <h2 class="title reveal d1">还没有订单数据</h2>
  <p class="subtitle reveal d2">接入了真实的麦当劳 MCP Token 后，<br>这里会变成你的专属年度报告。</p>
  <div class="callout reveal d3">
    当前是 <b>Demo 模式</b>。生成真实年报只需：<br>
    1. 在 open.mcd.cn/mcp 申请 MCP Token；<br>
    2. 设置环境变量 <b>MCD_MCP_TOKEN</b>；<br>
    3. 重新运行本工具（去掉 --demo 参数）。
  </div>
  <p class="foot reveal d3">非麦当劳官方产品，仅供娱乐参考；餐品信息以麦当劳官方渠道实时结果为准。</p>
</section>"""


def render_report(data: UserData, stats: YearStats, persona: Persona) -> str:
    """渲染完整单文件 HTML 年报。"""
    css = (TEMPLATE_DIR / "report.css").read_text(encoding="utf-8")
    js = (TEMPLATE_DIR / "report.js").read_text(encoding="utf-8")

    if not data.has_data:
        body = _empty_pages(data, stats)
        payload = {"persona": {"code": persona.code, "name": persona.type_name, "tagline": persona.tagline, "highlights": []}}
    else:
        top_slot = max(stats.time_slots.items(), key=lambda x: x[1])[0] if stats.time_slots else "午餐"
        rhythm_word = "夜猫子" if stats.night_ratio >= 0.2 else "作息稳定派"
        best_store = stats.top_stores[0][0] if stats.top_stores else "未知门店"
        best_item = stats.top_items[0][0] if stats.top_items else "未知餐品"
        exp = stats.most_expensive
        exp_items = "、".join(i.name for i in exp.items[:3]) if exp else "-"
        eq = stats.nutrition.fun_equivalents()
        body = f"""
<section class="page p-cover">
  <div class="kicker">MCD WRAPPED · 年度美食报告</div>
  <h1 class="title reveal">这一年，<br>麦麦陪你走过</h1>
  <p class="subtitle reveal d1">{esc(data.nickname)} 的麦当劳年度盘点<br>{stats.total_orders} 单 · {MONEY(stats.total_spend)} · {stats.total_items} 件</p>
  <div class="scroll-hint">下滑开启 ↓</div>
</section>

<section class="page p-white">
  <div class="kicker reveal">总览</div>
  <h2 class="title reveal d1">你的年度麦麦账单</h2>
  <div class="num-row">
    <div class="num-cell reveal d1"><div class="n" data-target="{stats.total_orders}">0</div><div class="l">累计订单</div></div>
    <div class="num-cell reveal d2"><div class="n" data-target="{stats.total_spend}" data-decimals="1" data-prefix="¥">0</div><div class="l">总花费</div></div>
    <div class="num-cell reveal d3"><div class="n" data-target="{stats.total_items}">0</div><div class="l">吃掉件数</div></div>
  </div>
  <div class="num-row" style="margin-top:34px">
    <div class="num-cell reveal d1"><div class="n" data-target="{stats.active_days}">0</div><div class="l">麦麦活跃天</div></div>
    <div class="num-cell reveal d2"><div class="n" data-target="{stats.total_discount}" data-decimals="1" data-prefix="¥">0</div><div class="l">优惠合计</div></div>
    <div class="num-cell reveal d3"><div class="n" data-target="{stats.avg_order_price}" data-decimals="1" data-prefix="¥">0</div><div class="l">单均消费</div></div>
  </div>
</section>

<section class="page p-dark">
  <div class="kicker reveal">年度之最</div>
  <h2 class="title reveal d1">这些瞬间，值得存档</h2>
  <ul class="list reveal d2">
    <li><span class="rank">👑</span><span class="grow">最贵一单 · {esc(best_store)}</span><span class="v">{MONEY(exp.total_price) if exp else "-"}</span></li>
    <li><span class="rank">🏪</span><span class="grow">最常光临 · {esc(best_store)}</span><span class="v">{stats.top_stores[0][1] if stats.top_stores else 0} 次</span></li>
    <li><span class="rank">❤️</span><span class="grow">本命餐品 · {esc(best_item)}</span><span class="v">{stats.top_items[0][1] if stats.top_items else 0} 件</span></li>
    <li><span class="rank">🧾</span><span class="grow">那一单点了</span><span class="v" style="font-weight:500">{esc(exp_items)}</span></li>
  </ul>
  <div class="callout reveal d3">最爱餐品 TOP5：<ul class="list" style="margin-top:8px">{_top_list(stats.top_items)}</ul></div>
</section>

<section class="page p-light">
  <div class="kicker reveal">时间节奏</div>
  <h2 class="title reveal d1">你是「{esc(top_slot)}」型选手</h2>
  <div class="chart reveal d2">{_bar_rows(stats.time_slots)}</div>
  <div class="callout reveal d3">全年 {stats.total_orders} 单中，{esc(top_slot)}时段出场最多，夜宵单占比 {(stats.night_ratio * 100):.0f}% —— 鉴定为<b>{esc(rhythm_word)}</b>。</div>
</section>

<section class="page p-gold">
  <div class="kicker reveal">月度趋势</div>
  <h2 class="title reveal d1">一年 12 个月的麦麦曲线</h2>
  <div class="months reveal d2">{_month_bars(stats.monthly)}</div>
  <p class="subtitle reveal d3" style="margin-top:14px">最厚的那个月，发生了什么故事？</p>
</section>

<section class="page p-dark">
  <div class="kicker reveal">营养盘点</div>
  <h2 class="title reveal d1">这一年，你吃进了多少能量</h2>
  <div class="big-num reveal d2"><span data-target="{stats.nutrition.as_dict()['energy']:.0f}">0</span><span class="unit">kcal</span></div>
  <p class="subtitle reveal d2">≈ {eq['rice_bowls']} 碗米饭 · 蛋白质 ≈ {eq['eggs']} 个鸡蛋</p>
  <ul class="list reveal d3" style="margin-top:22px">{_nutrition_rows(stats.nutrition)}</ul>
  <p class="foot reveal d3">营养数据基于官方餐品营养信息估算，仅供参考，不构成营养建议。</p>
</section>

<section class="page p-white">
  <div class="kicker reveal">积分与奖品</div>
  <h2 class="title reveal d1">麦门资产年报</h2>
  <div class="num-row">
    <div class="num-cell reveal d1"><div class="n" data-target="{stats.points.get('available', 0)}">0</div><div class="l">当前可用积分</div></div>
    <div class="num-cell reveal d2"><div class="n" data-target="{stats.points.get('total_earned', 0)}">0</div><div class="l">累计获得积分</div></div>
    <div class="num-cell reveal d3"><div class="n" data-target="{stats.points.get('expiring', 0)}">0</div><div class="l">即将过期积分</div></div>
  </div>
  <div class="callout reveal d2" style="margin-top:26px">
    积分商城兑换 {stats.mall.get('count', 0)} 次（消耗 {stats.mall.get('points_spent', 0)} 积分）；抽奖战绩如下：
    <ul class="list" style="margin-top:8px">{_prize_list(stats.prizes)}</ul>
  </div>
</section>

<section class="page p-persona">
  <div class="kicker reveal">麦格鉴定</div>
  <p class="subtitle reveal d1">基于全年订单，你的麦门人格是</p>
  <div class="persona-name reveal d1">{esc(persona.type_name)}</div>
  <div class="persona-tag reveal d2">「{esc(persona.tagline)}」</div>
  <div class="persona-code reveal d2">
    <div class="dim"><div class="k">{esc(persona.dims.get('loyalty', 'L'))}</div><div class="t">{'探索型' if persona.dims.get('loyalty') == 'E' else '忠诚型'}</div></div>
    <div class="dim"><div class="k">{esc(persona.dims.get('rhythm', 'M'))}</div><div class="t">{'夜型' if persona.dims.get('rhythm') == 'N' else '晨型'}</div></div>
    <div class="dim"><div class="k">{esc(persona.dims.get('social', 'S'))}</div><div class="t">{'群享' if persona.dims.get('social') == 'G' else '独食'}</div></div>
    <div class="dim"><div class="k">{esc(persona.dims.get('taste', 'C'))}</div><div class="t">{'尝鲜型' if persona.dims.get('taste') == 'T' else '守旧型'}</div></div>
  </div>
  <div class="callout reveal d3" style="max-width:520px">{esc(persona.desc)}<br><br>{'<br>'.join('· ' + esc(h) for h in persona.highlights)}</div>
</section>

<section class="page p-dark">
  <div class="kicker reveal">SHARE</div>
  <h2 class="title reveal d1">晒出你的麦麦年报</h2>
  <p class="subtitle reveal d2">长按或点击按钮保存分享卡片</p>
  <div class="card-wrap reveal d2"><canvas id="share-canvas" width="750" height="1000"></canvas></div>
  <button class="btn reveal d3" id="dl-btn">保存分享卡片</button>
  <p class="foot reveal d3">麦麦年报 MCD Wrapped · 麦当劳程序员创意开发大赛参赛作品<br>非麦当劳官方产品，由参赛者独立开发；项目输出仅供娱乐参考，不构成医疗、营养或其他专业建议；餐品信息、价格及供应状态以麦当劳官方渠道的实时结果为准。</p>
</section>"""
        payload = {
            "persona": {
                "code": persona.code,
                "name": persona.type_name,
                "tagline": persona.tagline,
                "highlights": persona.highlights,
            }
        }

    year = stats.year
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="description" content="麦麦年报 MCD Wrapped —— 你的麦当劳年度美食报告（非官方参赛作品）">
<title>麦麦年报 MCD Wrapped · {esc(data.nickname)}</title>
<style>{css}</style>
</head>
<body>
{body}
<script>window.REPORT = {json.dumps(payload, ensure_ascii=False)};</script>
<script>{js}</script>
</body>
</html>
"""


def write_report(data: UserData, stats: YearStats, persona: Persona, output: Path) -> Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_report(data, stats, persona), encoding="utf-8")
    return output
