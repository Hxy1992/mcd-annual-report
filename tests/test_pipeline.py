"""离线测试：全部基于演示数据与 Mock 响应，无需 Token 即可运行。

运行：python -m unittest discover -s tests -v
"""

from __future__ import annotations

import json
import sys
import unittest
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.aggregator import build_user_data_from_responses, parse_orders, parse_points  # noqa: E402
from src.analyzer import analyze, empty_state_stats, slot_of  # noqa: E402
from src.card import render_card_svg  # noqa: E402
from src.demo_data import demo_user_data, mock_tool_responses  # noqa: E402
from src.models import Order, OrderItem, UserData  # noqa: E402
from src.persona import PERSONA_TYPES, infer_persona  # noqa: E402
from src.report_html import render_report  # noqa: E402


class TestDemoData(unittest.TestCase):
    def test_demo_has_orders(self):
        data = demo_user_data(datetime(2026, 10, 12, 12, 0, 0))
        self.assertGreater(len(data.orders), 20)
        self.assertTrue(all(o.items for o in data.orders))
        self.assertTrue(data.nutrition_map)

    def test_demo_deterministic(self):
        a = demo_user_data(datetime(2026, 10, 12, 12, 0, 0))
        b = demo_user_data(datetime(2026, 10, 12, 12, 0, 0))
        self.assertEqual(len(a.orders), len(b.orders))
        self.assertEqual(a.orders[0].order_id, b.orders[0].order_id)


class TestAggregator(unittest.TestCase):
    def test_mock_chain_matches_demo(self):
        demo = demo_user_data(datetime(2026, 10, 12, 12, 0, 0))
        mock = build_user_data_from_responses(mock_tool_responses(datetime(2026, 10, 12, 12, 0, 0)))
        self.assertEqual(len(demo.orders), len(mock.orders))
        self.assertEqual(demo.points.available, mock.points.available)
        self.assertEqual(len(demo.prizes), len(mock.prizes))
        self.assertEqual(len(demo.nutrition_map), len(mock.nutrition_map))

    def test_parse_orders_snake_case(self):
        raw = {
            "orders": [
                {
                    "order_id": "X1",
                    "store_name": "测试店",
                    "created_at": "2026-01-02T12:00:00",
                    "total_price": 30.0,
                    "discount": 5.0,
                    "items": [{"name": "巨无霸", "quantity": 2, "price": 23.0}],
                }
            ]
        }
        orders = parse_orders(raw)
        self.assertEqual(len(orders), 1)
        self.assertEqual(orders[0].total_price, 30.0)
        self.assertEqual(orders[0].item_count, 2)

    def test_parse_orders_skips_no_time(self):
        self.assertEqual(parse_orders({"orders": [{"storeName": "x"}]}), [])

    def test_parse_points_nested(self):
        p = parse_points({"account": {"availablePoints": 100, "totalPoints": 500}})
        self.assertEqual((p.available, p.total_earned), (100, 500))

    def test_parse_points_garbage(self):
        p = parse_points("not-a-dict")
        self.assertEqual(p.available, 0)


class TestAnalyzer(unittest.TestCase):
    def setUp(self):
        self.data = demo_user_data(datetime(2026, 10, 12, 12, 0, 0))
        self.stats = analyze(self.data)

    def test_basic_totals(self):
        self.assertEqual(self.stats.total_orders, len(self.data.orders))
        self.assertGreater(self.stats.total_spend, 0)
        self.assertGreater(self.stats.total_items, self.stats.total_orders)
        self.assertAlmostEqual(self.stats.avg_order_price, self.stats.total_spend / self.stats.total_orders, places=1)

    def test_monthly_has_12(self):
        self.assertEqual(len(self.stats.monthly), 12)
        self.assertEqual(sum(m.orders for m in self.stats.monthly), self.stats.total_orders)

    def test_slots_sum(self):
        self.assertEqual(sum(self.stats.time_slots.values()), self.stats.total_orders)

    def test_nutrition_matched(self):
        self.assertEqual(self.stats.nutrition.matched_items, self.stats.total_items)
        self.assertEqual(self.stats.nutrition.unmatched_items, 0)
        self.assertGreater(self.stats.nutrition.energy, 0)

    def test_slot_boundaries(self):
        self.assertEqual(slot_of(7), "早餐")
        self.assertEqual(slot_of(12), "午餐")
        self.assertEqual(slot_of(15), "下午茶")
        self.assertEqual(slot_of(19), "晚餐")
        self.assertEqual(slot_of(23), "夜宵")
        self.assertEqual(slot_of(2), "夜宵")

    def test_empty_state(self):
        s = empty_state_stats()
        self.assertEqual(s.total_orders, 0)
        self.assertEqual(sum(s.time_slots.values()), 0)


class TestPersona(unittest.TestCase):
    def test_demo_persona_complete(self):
        data = demo_user_data(datetime(2026, 10, 12, 12, 0, 0))
        persona = infer_persona(analyze(data))
        self.assertIn(persona.code, PERSONA_TYPES)
        self.assertTrue(persona.type_name)
        self.assertTrue(persona.desc)
        self.assertTrue(persona.highlights)

    def test_all_16_types_have_copy(self):
        for code, t in PERSONA_TYPES.items():
            self.assertIn("name", t)
            self.assertIn("tagline", t)
            self.assertIn("desc", t)

    def test_night_persona(self):
        orders = [
            Order(f"O{i}", "店", datetime(2026, 1, i + 1, 23, 0), [OrderItem("巨无霸", quantity=1, price=23.0)],
                  total_price=23.0, origin_price=23.0)
            for i in range(5)
        ]
        stats = analyze(UserData(orders=orders))
        persona = infer_persona(stats)
        self.assertEqual(persona.dims["rhythm"], "N")
        self.assertIn("N", persona.code)

    def test_empty_data_default_persona(self):
        persona = infer_persona(empty_state_stats())
        self.assertEqual(persona.code, "LMGC")


class TestReport(unittest.TestCase):
    def test_demo_report_html(self):
        data = demo_user_data(datetime(2026, 10, 12, 12, 0, 0))
        stats = analyze(data)
        persona = infer_persona(stats)
        html_text = render_report(data, stats, persona)
        self.assertIn("麦麦年报", html_text)
        self.assertIn(persona.code, html_text)
        self.assertIn("share-canvas", html_text)
        self.assertIn("非麦当劳官方产品", html_text)

    def test_empty_report_html(self):
        data = UserData(nickname="测试")
        stats = empty_state_stats()
        persona = infer_persona(stats)
        html_text = render_report(data, stats, persona)
        self.assertIn("还没有订单数据", html_text)

    def test_no_token_leak_in_output(self):
        data = demo_user_data(datetime(2026, 10, 12, 12, 0, 0))
        html_text = render_report(data, analyze(data), infer_persona(analyze(data)))
        self.assertNotIn("MCD_MCP_TOKEN=", html_text)
        self.assertNotIn("Bearer ", html_text)

    def test_card_svg(self):
        data = demo_user_data(datetime(2026, 10, 12, 12, 0, 0))
        svg = render_card_svg(data.nickname, infer_persona(analyze(data)), analyze(data))
        self.assertIn("<svg", svg)
        self.assertIn("仅供娱乐参考", svg)


if __name__ == "__main__":
    unittest.main()
