from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from microshop.shared.events import publish, read_events
from microshop.shared.http import RawResponse
from services.gateway.app import static_file
from services.catalog.app import parse_product
from services.users.app import validate_user


class ValidationTests(unittest.TestCase):
    def test_valid_user_is_normalized(self):
        self.assertEqual(validate_user({"email": "A@Example.COM", "name": "Ada"}), ("a@example.com", "Ada"))

    def test_valid_product_converts_price_to_cents(self):
        self.assertEqual(
            parse_product({"sku": "book-1", "name": "Book", "price": "12.50", "stock": 3}),
            ("BOOK-1", "Book", 1250, 3),
        )


class EventTests(unittest.TestCase):
    def test_publish_and_read_events(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "events.jsonl"
            event = publish("order.created", {"order": {"id": 1}}, path)
            events = read_events(path)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].id, event.id)
        self.assertEqual(events[0].payload["order"]["id"], 1)


class FrontendTests(unittest.TestCase):
    def test_gateway_serves_frontend_asset(self):
        ctx = type("Ctx", (), {"path_params": {"asset": "app.js"}})()
        status, response = static_file(ctx)
        self.assertEqual(status, 200)
        self.assertIsInstance(response, RawResponse)
        self.assertIn(b"loadData", response.body)
        self.assertEqual(response.content_type, "application/javascript; charset=utf-8")


if __name__ == "__main__":
    unittest.main()
