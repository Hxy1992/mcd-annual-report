"""数据模型定义：麦当劳年报内部统一数据结构。

所有来自 MCP 的原始响应都会在 aggregator 层被规范化为这里的数据结构，
分析、人格、报告三层只面对这些稳定结构，不直接依赖 MCP 返回格式。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class OrderItem:
    """订单中的单个餐品。"""

    name: str
    code: str = ""
    quantity: int = 1
    price: float = 0.0  # 该餐品小计金额（元）


@dataclass
class Order:
    """一笔点餐订单（到店/外送）。"""

    order_id: str
    store_name: str
    created_at: datetime
    items: list[OrderItem] = field(default_factory=list)
    total_price: float = 0.0  # 实付金额（元）
    origin_price: float = 0.0  # 原价金额（元）
    discount: float = 0.0  # 优惠金额（元）
    delivery_fee: float = 0.0  # 配送费（元）
    channel: str = ""  # delivery=外送 / dinein=堂食 / pickup=自取
    status: str = ""

    @property
    def item_count(self) -> int:
        return sum(i.quantity for i in self.items)


@dataclass
class MallOrder:
    """麦麦商城积分兑换订单。"""

    order_id: str
    product_name: str
    points_spent: int = 0
    cash_spent: float = 0.0
    created_at: Optional[datetime] = None


@dataclass
class PointsInfo:
    """积分账户信息。"""

    available: int = 0  # 可用积分
    total_earned: int = 0  # 累计获得积分
    used: int = 0  # 累计消耗积分
    expiring: int = 0  # 即将过期积分


@dataclass
class Prize:
    """积分抽奖中奖记录。"""

    name: str
    kind: str = ""  # coupon=券 / physical=实物 / points=积分 / other
    won_at: Optional[datetime] = None


@dataclass
class Nutrition:
    """餐品营养信息（单位见字段名）。"""

    code: str
    name: str
    energy: float = 0.0  # 能量 kcal
    protein: float = 0.0  # 蛋白质 g
    fat: float = 0.0  # 脂肪 g
    carbs: float = 0.0  # 碳水化合物 g
    sodium: float = 0.0  # 钠 mg
    calcium: float = 0.0  # 钙 mg


@dataclass
class UserData:
    """年报所需的全部用户数据（聚合后的稳定结构）。"""

    nickname: str = "麦麦会员"
    orders: list[Order] = field(default_factory=list)
    mall_orders: list[MallOrder] = field(default_factory=list)
    points: PointsInfo = field(default_factory=PointsInfo)
    prizes: list[Prize] = field(default_factory=list)
    nutrition_map: dict[str, Nutrition] = field(default_factory=dict)
    generated_at: Optional[datetime] = None
    # 数据来源标记：real=真实 MCP 数据 / demo=示例数据
    source: str = "demo"

    @property
    def has_data(self) -> bool:
        return len(self.orders) > 0 or len(self.mall_orders) > 0
