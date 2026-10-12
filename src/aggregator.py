"""数据聚合层：把 MCP 工具响应规范化为 models.py 中的稳定结构。

设计要点：
- 官方文档只给了工具语义，未给字段级 schema（社区反馈文档与实测有出入），
  因此这里对每个字段都做多候选名解析与类型兜底，绝不假设单一格式；
- 只读取年报需要的字段，不做任何缓存落盘，每次运行实时拉取；
- 全部为只读工具调用，不触发任何写操作。
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Iterable, Optional

from .models import MallOrder, Nutrition, Order, OrderItem, PointsInfo, Prize, UserData

# --------------------------------------------------------------------------- #
# 通用解析工具
# --------------------------------------------------------------------------- #


def _as_list(obj: Any, *keys: str) -> list:
    """按候选 key 依次尝试取出列表；对象本身是列表则直接返回。"""
    if isinstance(obj, list):
        return obj
    if isinstance(obj, dict):
        for k in keys:
            v = obj.get(k)
            if isinstance(v, list):
                return v
            if isinstance(v, dict):
                # 形如 {"list": {...}, "total": n} 的包裹
                for kk in ("list", "records", "items", "data"):
                    vv = v.get(kk)
                    if isinstance(vv, list):
                        return vv
    return []


def _pick(d: dict, *keys: str, default: Any = None) -> Any:
    """按候选 key 取第一个非空值；对 camelCase 候选自动兼容 snake_case。"""
    if not isinstance(d, dict):
        return default
    candidates: list[str] = []
    for k in keys:
        candidates.append(k)
        if "_" not in k and any(c.isupper() for c in k):
            snake = "".join("_" + c.lower() if c.isupper() else c for c in k).lstrip("_")
            candidates.append(snake)
    for k in candidates:
        if k in d and d[k] not in (None, ""):
            return d[k]
    return default


def _to_float(v: Any, default: float = 0.0) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _to_int(v: Any, default: int = 0) -> int:
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return default


def _to_dt(v: Any) -> Optional[datetime]:
    """尽量把各种时间表示解析为 datetime。"""
    if isinstance(v, datetime):
        return v
    if isinstance(v, (int, float)):
        # 秒级或毫秒级时间戳
        ts = float(v)
        if ts > 1e12:
            ts /= 1000.0
        try:
            return datetime.fromtimestamp(ts)
        except (OverflowError, OSError, ValueError):
            return None
    if isinstance(v, str):
        s = v.strip()
        if not s:
            return None
        for fmt in (
            "%Y-%m-%dT%H:%M:%S.%f%z",
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d",
            "%Y/%m/%d %H:%M:%S",
            "%Y/%m/%d",
        ):
            try:
                dt = datetime.strptime(s.replace("Z", "+0000"), fmt)
                return dt.replace(tzinfo=None) if dt.tzinfo else dt
            except ValueError:
                continue
        # 最后尝试 fromisoformat
        try:
            dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
            return dt.replace(tzinfo=None) if dt.tzinfo else dt
        except ValueError:
            return None
    return None


# --------------------------------------------------------------------------- #
# 各工具的响应解析
# --------------------------------------------------------------------------- #


def parse_orders(raw: Any) -> list[Order]:
    """解析 order-list / query-order 的订单列表。"""
    orders: list[Order] = []
    for entry in _as_list(raw, "orders", "orderList", "list", "data"):
        if not isinstance(entry, dict):
            continue
        items_raw = _as_list(entry, "items", "orderItems", "products", "mealItems", "detail")
        items: list[OrderItem] = []
        for it in items_raw:
            if not isinstance(it, dict):
                continue
            name = _pick(it, "name", "title", "productName", "mealName", "itemName", default="")
            if not name:
                continue
            qty = _to_int(_pick(it, "quantity", "qty", "count", "num", default=1), 1) or 1
            price = _to_float(_pick(it, "price", "amount", "totalPrice", "subtotal", "salePrice", default=0.0))
            code = str(_pick(it, "code", "productCode", "mealCode", "sku", "id", default="") or "")
            items.append(OrderItem(name=str(name), code=code, quantity=qty, price=price))
        created = _to_dt(_pick(entry, "createdAt", "createTime", "orderTime", "created_at", "date", "payTime"))
        if created is None:
            continue  # 没有时间的订单无法进入时间线统计，跳过
        origin = _to_float(_pick(entry, "originPrice", "originalPrice", "totalOriginPrice", "goodsAmount", default=0.0))
        total = _to_float(_pick(entry, "totalPrice", "payAmount", "paidAmount", "actualAmount", "orderAmount", default=0.0))
        discount = _to_float(_pick(entry, "discount", "discountAmount", "couponAmount", "preferentialAmount", default=0.0))
        delivery = _to_float(_pick(entry, "deliveryFee", "deliveryAmount", "shippingFee", default=0.0))
        if not total and not origin:
            total = round(sum(i.price for i in items), 2)
        orders.append(
            Order(
                order_id=str(_pick(entry, "orderId", "orderNo", "id", "orderSN", default="") or ""),
                store_name=str(_pick(entry, "storeName", "shopName", "store", "restaurantName", default="未知门店") or "未知门店"),
                created_at=created,
                items=items,
                total_price=total,
                origin_price=origin or round(total + discount, 2),
                discount=discount,
                delivery_fee=delivery,
                channel=str(_pick(entry, "channel", "orderType", "eatType", "scene", default="") or ""),
                status=str(_pick(entry, "status", "orderStatus", "state", default="") or ""),
            )
        )
    orders.sort(key=lambda o: o.created_at)
    return orders


def parse_mall_orders(raw: Any) -> list[MallOrder]:
    """解析 mall-order-list 的商城兑换订单。"""
    out: list[MallOrder] = []
    for entry in _as_list(raw, "orders", "orderList", "mallOrders", "list", "data"):
        if not isinstance(entry, dict):
            continue
        out.append(
            MallOrder(
                order_id=str(_pick(entry, "orderId", "orderNo", "id", default="") or ""),
                product_name=str(_pick(entry, "productName", "name", "title", "goodsName", default="积分兑换商品") or "积分兑换商品"),
                points_spent=_to_int(_pick(entry, "points", "pointsSpent", "payPoints", "usedPoints", "integral", default=0)),
                cash_spent=_to_float(_pick(entry, "cash", "cashSpent", "amount", "payAmount", "money", default=0.0)),
                created_at=_to_dt(_pick(entry, "createdAt", "createTime", "orderTime", "date")),
            )
        )
    return out


def parse_points(raw: Any) -> PointsInfo:
    """解析 query-my-account 的积分账户。"""
    if not isinstance(raw, dict):
        return PointsInfo()
    # 账户可能是嵌套结构
    for wrap in ("account", "data", "pointsAccount", "result"):
        if isinstance(raw.get(wrap), dict):
            raw = raw[wrap]
            break
    return PointsInfo(
        available=_to_int(_pick(raw, "availablePoints", "available", "usablePoints", "balance", "currentPoints", default=0)),
        total_earned=_to_int(_pick(raw, "totalPoints", "totalEarned", "cumulativePoints", "earnedPoints", "total", default=0)),
        used=_to_int(_pick(raw, "usedPoints", "consumedPoints", "spentPoints", "used", default=0)),
        expiring=_to_int(_pick(raw, "expiringPoints", "expiring", "willExpirePoints", "expirePoints", default=0)),
    )


def parse_prizes(raw: Any) -> list[Prize]:
    """解析 query-my-prizes 的抽奖记录。"""
    out: list[Prize] = []
    for entry in _as_list(raw, "prizes", "prizeList", "list", "records", "data"):
        if not isinstance(entry, dict):
            continue
        name = str(_pick(entry, "name", "prizeName", "title", "rewardName", default="神秘奖品") or "神秘奖品")
        kind = str(_pick(entry, "kind", "type", "prizeType", "rewardType", default="") or "").lower()
        out.append(
            Prize(
                name=name,
                kind=kind,
                won_at=_to_dt(_pick(entry, "wonAt", "winTime", "createdAt", "createTime", "date", "drawTime")),
            )
        )
    return out


def parse_nutrition(raw: Any) -> dict[str, Nutrition]:
    """解析 list-nutrition-foods 的营养表，返回 {餐品名/编码: Nutrition}。"""
    out: dict[str, Nutrition] = {}
    for entry in _as_list(raw, "foods", "nutritionFoods", "list", "data", "items"):
        if not isinstance(entry, dict):
            continue
        name = str(_pick(entry, "name", "foodName", "productName", "title", default="") or "")
        code = str(_pick(entry, "code", "productCode", "foodCode", "id", default="") or "")
        if not name and not code:
            continue
        n = Nutrition(
            code=code or name,
            name=name or code,
            energy=_to_float(_pick(entry, "energy", "energyKcal", "calorie", "calories", "kcal", default=0.0)),
            protein=_to_float(_pick(entry, "protein", "proteinG", default=0.0)),
            fat=_to_float(_pick(entry, "fat", "fatG", default=0.0)),
            carbs=_to_float(_pick(entry, "carbs", "carbohydrate", "carbohydrates", default=0.0)),
            sodium=_to_float(_pick(entry, "sodium", "sodiumMg", "na", default=0.0)),
            calcium=_to_float(_pick(entry, "calcium", "calciumMg", "ca", default=0.0)),
        )
        # 同时按名称与编码建索引，方便订单按任一字段匹配
        if n.name:
            out[n.name] = n
        if n.code and n.code not in out:
            out[n.code] = n
    return out


# --------------------------------------------------------------------------- #
# 聚合入口
# --------------------------------------------------------------------------- #


class Aggregator:
    """通过 MCP 客户端拉取并聚合年报数据（只读工具）。"""

    # 年报实际用到的只读工具（设计上不调用任何写操作）
    TOOLS_USED = (
        "now-time-info",
        "order-list",
        "mall-order-list",
        "query-my-account",
        "query-my-prizes",
        "list-nutrition-foods",
    )

    def __init__(self, client) -> None:
        self.client = client

    def _safe_call(self, name: str, arguments: Optional[dict] = None) -> Any:
        """单工具调用失败不致命：记录并返回 None，年报对缺失数据有兜底。"""
        try:
            return self.client.call_tool(name, arguments)
        except Exception as e:  # noqa: BLE001 - 聚合层统一降级
            print(f"[warn] 工具 {name} 调用失败，将使用空数据兜底：{e}")
            return None

    def collect(self) -> UserData:
        orders = parse_orders(self._safe_call("order-list"))
        mall_orders = parse_mall_orders(self._safe_call("mall-order-list"))
        points = parse_points(self._safe_call("query-my-account"))
        prizes = parse_prizes(self._safe_call("query-my-prizes"))
        nutrition = parse_nutrition(self._safe_call("list-nutrition-foods"))
        return UserData(
            orders=orders,
            mall_orders=mall_orders,
            points=points,
            prizes=prizes,
            nutrition_map=nutrition,
            generated_at=datetime.now(),
            source="real",
        )


def build_user_data_from_responses(responses: dict[str, Any]) -> UserData:
    """把 {工具名: 原始响应} 直接聚合成 UserData（Mock 模式/测试用）。"""
    return UserData(
        orders=parse_orders(responses.get("order-list")),
        mall_orders=parse_mall_orders(responses.get("mall-order-list")),
        points=parse_points(responses.get("query-my-account")),
        prizes=parse_prizes(responses.get("query-my-prizes")),
        nutrition_map=parse_nutrition(responses.get("list-nutrition-foods")),
        generated_at=datetime.now(),
        source="mock",
    )
