"""年报计算引擎：把规范化的订单数据加工成报告所需的统计结果。

原则：
- 纯函数式加工，不碰网络、不写文件；
- 对空数据/少数据完全友好（空数据走专门的空状态，绝不出错）；
- 所有"相当于"类比仅为趣味表达，报告页脚有免责声明。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from .models import Nutrition, Order, UserData

# 时段划分（小时）
TIME_SLOTS = [
    ("早餐", 5, 10.5),
    ("午餐", 10.5, 14),
    ("下午茶", 14, 17),
    ("晚餐", 17, 21),
    ("夜宵", 21, 5),
]
SLOT_ORDER = ["早餐", "午餐", "下午茶", "晚餐", "夜宵"]

# 趣味换算口径（近似值，仅用于表达）
RICE_BOWL_KCAL = 200.0  # 一碗米饭
EGG_PROTEIN_G = 6.0  # 一个鸡蛋
MILK_CALCIUM_MG = 250.0  # 一杯牛奶
SALT_PER_G_NA_MG = 400.0  # 1 克盐 ≈ 400mg 钠


def slot_of(hour: int) -> str:
    for name, start, end in TIME_SLOTS:
        if start <= hour < end or (start > end and (hour >= start or hour < end)):
            return name
    return "午餐"


@dataclass
class MonthlyPoint:
    month: int
    orders: int = 0
    spend: float = 0.0


@dataclass
class NutritionTotals:
    energy: float = 0.0
    protein: float = 0.0
    fat: float = 0.0
    carbs: float = 0.0
    sodium: float = 0.0
    calcium: float = 0.0
    matched_items: int = 0
    unmatched_items: int = 0

    def as_dict(self) -> dict:
        return {
            "energy": round(self.energy, 1),
            "protein": round(self.protein, 1),
            "fat": round(self.fat, 1),
            "carbs": round(self.carbs, 1),
            "sodium": round(self.sodium, 1),
            "calcium": round(self.calcium, 1),
        }

    def fun_equivalents(self) -> dict:
        return {
            "rice_bowls": round(self.energy / RICE_BOWL_KCAL, 1),
            "eggs": round(self.protein / EGG_PROTEIN_G, 1),
            "milk_cups": round(self.calcium / MILK_CALCIUM_MG, 1),
            "salt_grams": round(self.sodium / SALT_PER_G_NA_MG, 1),
        }


@dataclass
class YearStats:
    year: int
    total_orders: int = 0
    total_spend: float = 0.0
    total_items: int = 0
    total_discount: float = 0.0
    total_delivery_fee: float = 0.0
    avg_order_price: float = 0.0
    monthly: list[MonthlyPoint] = field(default_factory=list)
    time_slots: dict[str, int] = field(default_factory=dict)
    top_stores: list[tuple[str, int, float]] = field(default_factory=list)
    top_items: list[tuple[str, int, float]] = field(default_factory=list)
    most_expensive: Optional[Order] = None
    nutrition: NutritionTotals = field(default_factory=NutritionTotals)
    channels: dict[str, int] = field(default_factory=dict)
    first_order: Optional[datetime] = None
    last_order: Optional[datetime] = None
    active_days: int = 0
    night_ratio: float = 0.0
    unique_items: int = 0
    top_item_ratio: float = 0.0
    avg_items_per_order: float = 0.0
    points: dict = field(default_factory=dict)
    prizes: list[dict] = field(default_factory=list)
    mall: dict = field(default_factory=dict)


def analyze(data: UserData, year: Optional[int] = None) -> YearStats:
    """计算年报统计。默认覆盖全部订单（不强制按年过滤，少数据用户更友好）。"""
    orders = sorted(data.orders, key=lambda o: o.created_at)
    stats = YearStats(year=year or (orders[-1].created_at.year if orders else datetime.now().year))

    if not orders:
        stats.time_slots = {s: 0 for s in SLOT_ORDER}
        return stats

    stats.total_orders = len(orders)
    stats.total_spend = round(sum(o.total_price for o in orders), 2)
    stats.total_items = sum(o.item_count for o in orders)
    stats.total_discount = round(sum(o.discount for o in orders), 2)
    stats.total_delivery_fee = round(sum(o.delivery_fee for o in orders), 2)
    stats.avg_order_price = round(stats.total_spend / len(orders), 2)
    stats.avg_items_per_order = round(stats.total_items / len(orders), 2)
    stats.first_order = orders[0].created_at
    stats.last_order = orders[-1].created_at
    stats.active_days = len({o.created_at.date() for o in orders})

    # 月度趋势
    monthly_map: dict[int, MonthlyPoint] = {}
    for o in orders:
        m = o.created_at.month
        mp = monthly_map.setdefault(m, MonthlyPoint(month=m))
        mp.orders += 1
        mp.spend += o.total_price
    stats.monthly = [monthly_map.get(m, MonthlyPoint(month=m)) for m in range(1, 13)]

    # 时段分布
    slots = {s: 0 for s in SLOT_ORDER}
    night = 0
    for o in orders:
        s = slot_of(o.created_at.hour)
        slots[s] += 1
        if s == "夜宵":
            night += 1
    stats.time_slots = slots
    stats.night_ratio = round(night / len(orders), 3)

    # 渠道分布
    channels: dict[str, int] = {}
    for o in orders:
        key = o.channel or "unknown"
        channels[key] = channels.get(key, 0) + 1
    stats.channels = channels

    # 门店与餐品排行
    store_counter: dict[str, int] = {}
    store_spend: dict[str, float] = {}
    item_counter: dict[str, int] = {}
    item_spend: dict[str, float] = {}
    for o in orders:
        store_counter[o.store_name] = store_counter.get(o.store_name, 0) + 1
        store_spend[o.store_name] = store_spend.get(o.store_name, 0.0) + o.total_price
        for it in o.items:
            item_counter[it.name] = item_counter.get(it.name, 0) + it.quantity
            item_spend[it.name] = item_spend.get(it.name, 0.0) + it.price
    stats.top_stores = sorted(
        ((n, c, round(store_spend[n], 2)) for n, c in store_counter.items()),
        key=lambda x: (-x[1], -x[2]),
    )
    stats.top_items = sorted(
        ((n, c, round(item_spend[n], 2)) for n, c in item_counter.items()),
        key=lambda x: (-x[1], -x[2]),
    )
    stats.unique_items = len(item_counter)
    if item_counter:
        top_name, top_qty = max(item_counter.items(), key=lambda x: x[1])
        stats.top_item_ratio = round(top_qty / max(stats.total_items, 1), 3)

    # 最贵一单
    stats.most_expensive = max(orders, key=lambda o: o.total_price)

    # 营养汇总（按餐品名或编码匹配）
    totals = NutritionTotals()
    for o in orders:
        for it in o.items:
            n = data.nutrition_map.get(it.name) or data.nutrition_map.get(it.code)
            if n is None:
                totals.unmatched_items += it.quantity
                continue
            totals.matched_items += it.quantity
            totals.energy += n.energy * it.quantity
            totals.protein += n.protein * it.quantity
            totals.fat += n.fat * it.quantity
            totals.carbs += n.carbs * it.quantity
            totals.sodium += n.sodium * it.quantity
            totals.calcium += n.calcium * it.quantity
    stats.nutrition = totals

    # 积分与奖品
    stats.points = {
        "available": data.points.available,
        "total_earned": data.points.total_earned,
        "used": data.points.used,
        "expiring": data.points.expiring,
    }
    stats.prizes = [
        {"name": p.name, "kind": p.kind, "won_at": p.won_at.strftime("%Y-%m-%d") if p.won_at else ""}
        for p in sorted(data.prizes, key=lambda p: (p.won_at is None, p.won_at or datetime.min), reverse=True)
    ]
    stats.mall = {
        "count": len(data.mall_orders),
        "points_spent": sum(m.points_spent for m in data.mall_orders),
        "cash_spent": round(sum(m.cash_spent for m in data.mall_orders), 2),
        "items": [{"name": m.product_name, "points": m.points_spent} for m in data.mall_orders],
    }
    return stats


def empty_state_stats() -> YearStats:
    """空数据统计（报告显示引导页）。"""
    s = YearStats(year=datetime.now().year)
    s.time_slots = {name: 0 for name in SLOT_ORDER}
    return s
