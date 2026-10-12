"""示例数据（Demo 模式）。

重要说明：
- 本模块生成的所有订单/积分/奖品数据均为**构造数据**，用于无 Token 用户完整体验年报效果；
- 营养数据为公开渠道的近似值，仅供演示，真实数据以麦当劳 MCP 返回为准；
- 使用固定随机种子，保证每次生成结果一致，便于测试与截图。
"""

from __future__ import annotations

import random
from datetime import datetime, timedelta

from .models import MallOrder, Nutrition, Order, OrderItem, PointsInfo, Prize, UserData

# --------------------------------------------------------------------------- #
# 演示菜单库（近似价格与营养值，仅供演示）
# --------------------------------------------------------------------------- #

DEMO_MENU: dict[str, dict] = {
    "巨无霸": {"price": 23.0, "energy": 531, "protein": 27, "fat": 30, "carbs": 44, "sodium": 1030, "calcium": 190},
    "麦辣鸡腿堡": {"price": 22.0, "energy": 547, "protein": 26, "fat": 29, "carbs": 51, "sodium": 1070, "calcium": 120},
    "板烧鸡腿堡": {"price": 23.0, "energy": 430, "protein": 24, "fat": 19, "carbs": 42, "sodium": 900, "calcium": 100},
    "双层鳕鱼堡": {"price": 23.0, "energy": 470, "protein": 22, "fat": 24, "carbs": 43, "sodium": 860, "calcium": 90},
    "麦香鱼": {"price": 13.0, "energy": 330, "protein": 15, "fat": 16, "carbs": 35, "sodium": 600, "calcium": 80},
    "吉士汉堡": {"price": 12.5, "energy": 300, "protein": 15, "fat": 13, "carbs": 32, "sodium": 700, "calcium": 180},
    "双层吉士汉堡": {"price": 18.5, "energy": 460, "protein": 24, "fat": 24, "carbs": 36, "sodium": 1120, "calcium": 280},
    "麦乐鸡(5块)": {"price": 12.0, "energy": 230, "protein": 12, "fat": 14, "carbs": 19, "sodium": 470, "calcium": 40},
    "薯条(小)": {"price": 7.5, "energy": 230, "protein": 3, "fat": 11, "carbs": 30, "sodium": 190, "calcium": 15},
    "薯条(中)": {"price": 9.5, "energy": 330, "protein": 4, "fat": 16, "carbs": 44, "sodium": 290, "calcium": 20},
    "薯条(大)": {"price": 11.5, "energy": 430, "protein": 5, "fat": 21, "carbs": 57, "sodium": 380, "calcium": 25},
    "麦辣鸡翅(2块)": {"price": 11.5, "energy": 220, "protein": 14, "fat": 13, "carbs": 12, "sodium": 520, "calcium": 30},
    "可乐(中)": {"price": 10.0, "energy": 170, "protein": 0, "fat": 0, "carbs": 42, "sodium": 30, "calcium": 6},
    "零度可乐(中)": {"price": 10.0, "energy": 0, "protein": 0, "fat": 0, "carbs": 0, "sodium": 34, "calcium": 6},
    "玉米杯": {"price": 8.0, "energy": 130, "protein": 5, "fat": 3, "carbs": 24, "sodium": 320, "calcium": 10},
    "圆筒冰淇淋": {"price": 4.0, "energy": 150, "protein": 4, "fat": 5, "carbs": 23, "sodium": 55, "calcium": 130},
    "麦旋风(奥利奥)": {"price": 12.0, "energy": 280, "protein": 6, "fat": 10, "carbs": 42, "sodium": 190, "calcium": 180},
    "菠萝派": {"price": 7.5, "energy": 240, "protein": 2, "fat": 12, "carbs": 31, "sodium": 130, "calcium": 10},
    "香芋派": {"price": 7.5, "energy": 230, "protein": 2, "fat": 11, "carbs": 30, "sodium": 125, "calcium": 10},
    "猪柳蛋麦满分": {"price": 16.0, "energy": 400, "protein": 19, "fat": 20, "carbs": 39, "sodium": 860, "calcium": 180},
    "脆薯饼": {"price": 6.0, "energy": 150, "protein": 2, "fat": 9, "carbs": 16, "sodium": 350, "calcium": 8},
    "麦咖啡拿铁(中)": {"price": 19.0, "energy": 190, "protein": 10, "fat": 8, "carbs": 21, "sodium": 90, "calcium": 260},
    "麦咖啡美式(中)": {"price": 14.0, "energy": 15, "protein": 1, "fat": 0, "carbs": 2, "sodium": 10, "calcium": 12},
    "椰子水": {"price": 12.0, "energy": 90, "protein": 0, "fat": 0, "carbs": 21, "sodium": 60, "calcium": 40},
    "阳光橙": {"price": 9.5, "energy": 110, "protein": 1, "fat": 0, "carbs": 26, "sodium": 20, "calcium": 15},
}

DEMO_STORES = [
    "麦当劳(中关村大街餐厅)",
    "麦当劳(西单大悦城餐厅)",
    "麦当劳(国贸三期餐厅)",
    "麦当劳(望京 SOHO 餐厅)",
    "麦当劳(五道口购物中心餐厅)",
    "麦当劳(三里屯太古里餐厅)",
    "麦当劳(上地信息路餐厅)",
]

# 常见组合（更贴近真实点餐习惯；汉堡类权重更高，演示效果更好）
DEMO_COMBOS: list[list[tuple[str, int]]] = [
    [("巨无霸", 1), ("薯条(中)", 1), ("可乐(中)", 1)],
    [("巨无霸", 1), ("麦辣鸡翅(2块)", 1), ("可乐(中)", 1)],
    [("巨无霸", 1), ("菠萝派", 1), ("零度可乐(中)", 1)],
    [("巨无霸", 1), ("玉米杯", 1), ("零度可乐(中)", 1)],
    [("巨无霸", 1), ("圆筒冰淇淋", 1)],
    [("麦辣鸡腿堡", 1), ("薯条(中)", 1), ("可乐(中)", 1)],
    [("板烧鸡腿堡", 1), ("玉米杯", 1), ("零度可乐(中)", 1)],
    [("双层吉士汉堡", 1), ("薯条(小)", 1), ("可乐(中)", 1)],
    [("麦乐鸡(5块)", 1), ("薯条(中)", 1), ("圆筒冰淇淋", 1)],
    [("猪柳蛋麦满分", 1), ("脆薯饼", 1), ("麦咖啡美式(中)", 1)],
    [("麦咖啡拿铁(中)", 1), ("香芋派", 1)],
    [("吉士汉堡", 1), ("零度可乐(中)", 1), ("薯条(小)", 1)],
    [("双层鳕鱼堡", 1), ("阳光橙", 1)],
    [("麦旋风(奥利奥)", 1), ("麦辣鸡翅(2块)", 1)],
    [("椰子水", 1), ("吉士汉堡", 1)],
]


def demo_nutrition_map() -> dict[str, Nutrition]:
    """演示用营养表（以餐品名做 key，兼容真实数据的 code 匹配逻辑）。"""
    out: dict[str, Nutrition] = {}
    for name, n in DEMO_MENU.items():
        out[name] = Nutrition(
            code=name,
            name=name,
            energy=float(n["energy"]),
            protein=float(n["protein"]),
            fat=float(n["fat"]),
            carbs=float(n["carbs"]),
            sodium=float(n["sodium"]),
            calcium=float(n["calcium"]),
        )
    return out


def demo_user_data(reference: datetime | None = None) -> UserData:
    """生成一份覆盖近 12 个月的演示数据。"""
    rng = random.Random(20261012)
    now = reference or datetime.now()
    orders: list[Order] = []

    # 从 12 个月前滚动生成，周末与晚间权重更高（贴近真实作息）
    for days_ago in range(360, -1, -1):
        day = now - timedelta(days=days_ago)
        weekday = day.weekday()
        # 约每 8 天 1 单，周末概率更高
        base = 0.12 if weekday >= 5 else 0.10
        if rng.random() > base:
            continue
        # 时段偏向午晚市与夜宵（与"夜型"人设自洽）
        hour_choices = [12, 12, 18, 19, 19, 20, 21, 21, 22, 22, 23, 23, 15]
        hour = rng.choice(hour_choices)
        minute = rng.randint(0, 59)
        created = day.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if created > now:
            continue

        combo = rng.choice(DEMO_COMBOS)
        items = [OrderItem(name=n, code=n, quantity=q, price=round(DEMO_MENU[n]["price"] * q, 2)) for n, q in combo]
        origin = round(sum(i.price for i in items), 2)
        # 约 70% 的订单有优惠
        discount = round(origin * rng.uniform(0.08, 0.3), 2) if rng.random() < 0.7 else 0.0
        delivery_fee = round(rng.uniform(0, 6), 1) if rng.random() < 0.35 else 0.0
        total = round(origin - discount + delivery_fee, 2)
        channel = "delivery" if delivery_fee > 0 else ("dinein" if rng.random() < 0.6 else "pickup")
        orders.append(
            Order(
                order_id=f"MCD{created:%Y%m%d%H%M}{rng.randint(100, 999)}",
                store_name=rng.choice(DEMO_STORES),
                created_at=created,
                items=items,
                total_price=total,
                origin_price=origin,
                discount=discount,
                delivery_fee=delivery_fee,
                channel=channel,
                status="已完成",
            )
        )

    mall_orders = [
        MallOrder("MALL20260315001", "麦麦商城·积分兑换券", 500, 0.0, now - timedelta(days=210)),
        MallOrder("MALL20260622002", "圆筒冰淇淋兑换券", 300, 0.0, now - timedelta(days=110)),
        MallOrder("MALL20260810003", "程序员节限定徽章", 1500, 9.9, now - timedelta(days=60)),
    ]
    prizes = [
        Prize("麦辣鸡腿堡兑换券", "coupon", now - timedelta(days=95)),
        Prize("积分 88", "points", now - timedelta(days=70)),
        Prize("麦麦周边冰箱贴", "physical", now - timedelta(days=35)),
        Prize("薯条(中)兑换券", "coupon", now - timedelta(days=12)),
    ]
    points = PointsInfo(available=3250, total_earned=18600, used=15350, expiring=800)

    return UserData(
        nickname="麦麦体验用户",
        orders=orders,
        mall_orders=mall_orders,
        points=points,
        prizes=prizes,
        nutrition_map=demo_nutrition_map(),
        generated_at=now,
        source="demo",
    )


def _order_to_dict(o: Order) -> dict:
    """序列化为接近真实 API 的形状（camelCase + ISO 时间 + 餐品明细为 dict）。"""
    return {
        "orderId": o.order_id,
        "storeName": o.store_name,
        "createdAt": o.created_at.isoformat(),
        "status": o.status,
        "channel": o.channel,
        "totalPrice": o.total_price,
        "originPrice": o.origin_price,
        "discount": o.discount,
        "deliveryFee": o.delivery_fee,
        "items": [
            {"name": i.name, "code": i.code, "quantity": i.quantity, "price": i.price}
            for i in o.items
        ],
    }


def mock_tool_responses(reference: datetime | None = None) -> dict[str, object]:
    """把演示数据包装成"工具响应"的形状，供 Mock 传输层走完整解析链路。"""
    data = demo_user_data(reference)
    return {
        "order-list": {"orders": [_order_to_dict(o) for o in data.orders]},
        "mall-order-list": {
            "orders": [
                {
                    "orderId": m.order_id,
                    "productName": m.product_name,
                    "points": m.points_spent,
                    "cash": m.cash_spent,
                    "createdAt": m.created_at.isoformat() if m.created_at else None,
                }
                for m in data.mall_orders
            ]
        },
        "query-my-account": {
            "availablePoints": data.points.available,
            "totalPoints": data.points.total_earned,
            "usedPoints": data.points.used,
            "expiringPoints": data.points.expiring,
        },
        "query-my-prizes": {
            "prizes": [
                {
                    "name": p.name,
                    "type": p.kind,
                    "wonAt": p.won_at.isoformat() if p.won_at else None,
                }
                for p in data.prizes
            ]
        },
        "list-nutrition-foods": {
            "foods": [
                {
                    "code": n.code,
                    "name": n.name,
                    "energy": n.energy,
                    "protein": n.protein,
                    "fat": n.fat,
                    "carbs": n.carbs,
                    "sodium": n.sodium,
                    "calcium": n.calcium,
                }
                for n in data.nutrition_map.values()
            ]
        },
        "now-time-info": {"currentTime": (reference or datetime.now()).isoformat()},
    }
