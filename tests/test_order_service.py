from __future__ import annotations

import asyncio
import threading
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from morsl.services.order_service import OrderService


@pytest.fixture
def mock_api():
    api = MagicMock()
    api.get_meal_types.return_value = [{"id": 42, "name": "Dinner"}]
    return api


@pytest.fixture
def order_service():
    svc = OrderService(url="http://localhost/api/", token="test-token")
    return svc


class TestOrderService:
    def test_init(self, order_service):
        assert order_service.url == "http://localhost/api/"
        assert order_service.token == "test-token"
        assert order_service._api is None
        assert order_service._cached_meal_type is None

    def test_get_api_lazy_init(self, order_service):
        with patch("morsl.services.order_service.TandoorAPI") as MockAPI:
            MockAPI.return_value = MagicMock()
            api = order_service._get_api()
            assert api is not None
            # Second call returns same instance
            api2 = order_service._get_api()
            assert api is api2
            MockAPI.assert_called_once()

    def test_get_meal_type_uses_first_available(self, order_service, mock_api):
        order_service._api = mock_api
        mt = order_service._get_meal_type()
        assert mt["id"] == 42
        # Second call returns cached
        mt2 = order_service._get_meal_type()
        assert mt2 is mt
        mock_api.get_meal_types.assert_called_once()

    def test_place_order(self, order_service, mock_api):
        order_service._api = mock_api
        mock_api.create_order_meal_plan.return_value = {"id": 100}

        order = order_service.place_order(recipe_id=5, recipe_name="Mojito")
        assert order["recipe_id"] == 5
        assert order["recipe_name"] == "Mojito"
        assert order["meal_plan_id"] == 100
        assert order["servings"] == 1
        assert order["customer_name"] is None
        mock_api.create_order_meal_plan.assert_called_once()
        # Note should not contain "by" when no customer name
        call_kwargs = mock_api.create_order_meal_plan.call_args[1]
        assert "by" not in call_kwargs["note"]

    def test_place_order_with_customer_name(self, order_service, mock_api):
        order_service._api = mock_api
        mock_api.create_order_meal_plan.return_value = {"id": 102}

        order = order_service.place_order(recipe_id=5, recipe_name="Mojito", customer_name="Alice")
        assert order["customer_name"] == "Alice"
        call_kwargs = mock_api.create_order_meal_plan.call_args[1]
        assert "by Alice" in call_kwargs["note"]

    def test_place_order_notifies_subscribers(self, order_service, mock_api):
        order_service._api = mock_api
        mock_api.create_order_meal_plan.return_value = {"id": 101}

        q = order_service.subscribe()
        order_service.place_order(recipe_id=1, recipe_name="Daiquiri")

        assert not q.empty()
        notified = q.get_nowait()
        assert notified["recipe_name"] == "Daiquiri"

    def test_get_orders(self, order_service, mock_api):
        order_service._api = mock_api
        mock_api.get_meal_plans_by_type.return_value = [
            {
                "id": 10,
                "recipe": {"id": 1, "name": "Mojito"},
                "title": "Mojito",
                "from_date": "2024-01-01T12:00:00",
                "servings": 1,
                "note": "",
            },
            {
                "id": 11,
                "recipe": {"id": 2, "name": "Daiquiri"},
                "title": "Daiquiri",
                "from_date": "2024-01-01T12:30:00",
                "servings": 2,
                "note": "",
            },
        ]

        orders = order_service.get_orders()
        assert len(orders) == 2
        # Sorted by ID descending
        assert orders[0]["id"] == "11"
        assert orders[1]["id"] == "10"
        # No customer_name when note is empty
        assert orders[0]["customer_name"] is None
        assert orders[1]["customer_name"] is None

    def test_get_orders_parses_customer_name(self, order_service, mock_api):
        order_service._api = mock_api
        mock_api.get_meal_plans_by_type.return_value = [
            {
                "id": 10,
                "recipe": {"id": 1, "name": "Mojito"},
                "title": "Mojito",
                "from_date": "2024-01-01T12:00:00",
                "servings": 1,
                "note": "Ordered by Alice at 12:00:00",
            },
            {
                "id": 11,
                "recipe": {"id": 2, "name": "Daiquiri"},
                "title": "Daiquiri",
                "from_date": "2024-01-01T12:30:00",
                "servings": 1,
                "note": "Ordered at 12:30:00",
            },
        ]

        orders = order_service.get_orders()
        # First order has name parsed from note
        assert orders[1]["customer_name"] == "Alice"  # id=10 sorted last
        # Second order has no name
        assert orders[0]["customer_name"] is None  # id=11 sorted first

    def test_get_order_counts(self, order_service, mock_api):
        order_service._api = mock_api
        mock_api.get_meal_plans_by_type.return_value = [
            {
                "id": 10,
                "recipe": {"id": 1, "name": "Mojito"},
                "title": "Mojito",
                "from_date": "2024-01-01",
                "servings": 1,
                "note": "",
            },
            {
                "id": 11,
                "recipe": {"id": 1, "name": "Mojito"},
                "title": "Mojito",
                "from_date": "2024-01-01",
                "servings": 2,
                "note": "",
            },
            {
                "id": 12,
                "recipe": {"id": 2, "name": "Daiquiri"},
                "title": "Daiquiri",
                "from_date": "2024-01-01",
                "servings": 1,
                "note": "",
            },
        ]

        counts = order_service.get_order_counts()
        assert counts[1]["count"] == 3  # 1 + 2 servings
        assert counts[2]["count"] == 1

    def test_clear_orders(self, order_service, mock_api):
        order_service._api = mock_api
        mock_api.get_meal_plans_by_type.return_value = [
            {
                "id": 10,
                "recipe": {"id": 1, "name": "Mojito"},
                "title": "Mojito",
                "from_date": "2024-01-01",
                "servings": 1,
                "note": "",
            },
            {
                "id": 11,
                "recipe": {"id": 2, "name": "Daiquiri"},
                "title": "Daiquiri",
                "from_date": "2024-01-01",
                "servings": 1,
                "note": "",
            },
        ]
        count = order_service.clear_orders()
        assert count == 2
        assert mock_api.delete_meal_plan.call_count == 2

    def test_subscribe_unsubscribe(self, order_service):
        q = order_service.subscribe()
        assert q in order_service._subscribers
        order_service.unsubscribe(q)
        assert q not in order_service._subscribers

    def test_unsubscribe_nonexistent(self, order_service):
        q = asyncio.Queue()
        # Should not raise
        order_service.unsubscribe(q)


class TestServerOrderStorage:
    def test_store_and_get_server_orders(self, order_service):
        today = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        order = {
            "id": "local-1000",
            "recipe_id": 5,
            "recipe_name": "Mojito",
            "timestamp": today,
            "servings": 1,
            "meal_plan_id": None,
            "customer_name": "Alice",
        }
        order_service.store_order(order)
        orders = order_service.get_server_orders()
        assert len(orders) == 1
        assert orders[0]["id"] == "local-1000"
        assert orders[0]["recipe_name"] == "Mojito"

    def test_delete_server_order(self, order_service):
        today = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        order_service.store_order(
            {
                "id": "local-2000",
                "recipe_id": 1,
                "recipe_name": "Daiquiri",
                "timestamp": today,
                "servings": 1,
                "meal_plan_id": None,
                "customer_name": None,
            }
        )
        assert len(order_service._server_orders) == 1
        order_service.delete_server_order("local-2000")
        assert len(order_service._server_orders) == 0

    def test_delete_server_order_not_found(self, order_service):
        with pytest.raises(RuntimeError):
            order_service.delete_server_order("local-nonexistent")

    def test_clear_server_orders(self, order_service):
        today = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        for i in range(3):
            order_service.store_order(
                {
                    "id": f"local-{3000 + i}",
                    "recipe_id": i,
                    "recipe_name": f"Drink {i}",
                    "timestamp": today,
                    "servings": 1,
                    "meal_plan_id": None,
                    "customer_name": None,
                }
            )
        count = order_service.clear_server_orders()
        assert count == 3
        assert len(order_service._server_orders) == 0

    def test_get_orders_merges_both_sources(self, order_service, mock_api):
        order_service._api = mock_api
        today = datetime.now()
        today_str = today.strftime("%Y-%m-%dT%H:%M:%S")
        mock_api.get_meal_plans_by_type.return_value = [
            {
                "id": 10,
                "recipe": {"id": 1, "name": "Mojito"},
                "title": "Mojito",
                "from_date": today.strftime("%Y-%m-%d"),
                "servings": 1,
                "note": "Ordered at 12:00:00",
            },
        ]
        order_service.store_order(
            {
                "id": "local-4000",
                "recipe_id": 2,
                "recipe_name": "Daiquiri",
                "timestamp": today_str,
                "servings": 1,
                "meal_plan_id": None,
                "customer_name": None,
            }
        )
        orders = order_service.get_orders()
        assert len(orders) == 2
        recipe_names = {o["recipe_name"] for o in orders}
        assert "Mojito" in recipe_names
        assert "Daiquiri" in recipe_names

    def test_delete_order_routes_local_to_server_store(self, order_service):
        today = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        order_service.store_order(
            {
                "id": "local-5000",
                "recipe_id": 1,
                "recipe_name": "Negroni",
                "timestamp": today,
                "servings": 1,
                "meal_plan_id": None,
                "customer_name": None,
            }
        )
        order_service.delete_order("local-5000")
        assert len(order_service._server_orders) == 0

    def test_delete_order_routes_numeric_to_tandoor(self, order_service, mock_api):
        order_service._api = mock_api
        order_service.delete_order("99")
        mock_api.delete_meal_plan.assert_called_once_with(99)

    def test_clear_orders_clears_both_sources(self, order_service, mock_api):
        order_service._api = mock_api
        today = datetime.now()
        today_str = today.strftime("%Y-%m-%dT%H:%M:%S")
        mock_api.get_meal_plans_by_type.return_value = [
            {
                "id": 10,
                "recipe": {"id": 1, "name": "Mojito"},
                "title": "Mojito",
                "from_date": today.strftime("%Y-%m-%d"),
                "servings": 1,
                "note": "",
            },
        ]
        order_service.store_order(
            {
                "id": "local-6000",
                "recipe_id": 2,
                "recipe_name": "Daiquiri",
                "timestamp": today_str,
                "servings": 1,
                "meal_plan_id": None,
                "customer_name": None,
            }
        )
        count = order_service.clear_orders()
        assert count == 2
        assert len(order_service._server_orders) == 0
        mock_api.delete_meal_plan.assert_called_once()


class TestThreadSafety:
    def test_concurrent_get_meal_type(self, order_service, mock_api):
        """10 threads calling _get_meal_type concurrently — API call count bounded."""
        order_service._api = mock_api
        mock_api.get_meal_type.return_value = {"id": 7, "name": "Brunch"}
        errors = []

        def worker():
            try:
                mt = order_service._get_meal_type(7)
                assert mt["id"] == 7
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors
        # Duplicate calls are benign (first-write-wins), but bounded
        assert 1 <= mock_api.get_meal_type.call_count <= 10

    def test_concurrent_get_api(self, order_service):
        """10 threads calling _get_api concurrently — only one TandoorAPI created."""
        errors = []

        with patch("morsl.services.order_service.TandoorAPI") as MockAPI:
            MockAPI.return_value = MagicMock()

            def worker():
                try:
                    order_service._get_api()
                except Exception as e:
                    errors.append(e)

            threads = [threading.Thread(target=worker) for _ in range(10)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()

            assert not errors
            MockAPI.assert_called_once()


class TestGetMealTypeAPI:
    def test_get_meal_type_specific_id(self, order_service, mock_api):
        order_service._api = mock_api
        mock_api.get_meal_type.return_value = {"id": 7, "name": "Brunch"}
        mt = order_service._get_meal_type(7)
        assert mt["id"] == 7
        mock_api.get_meal_type.assert_called_once_with(7)

    def test_get_meal_type_caches_result(self, order_service, mock_api):
        order_service._api = mock_api
        mock_api.get_meal_type.return_value = {"id": 7, "name": "Brunch"}
        order_service._get_meal_type(7)
        order_service._get_meal_type(7)
        # Second call should use cache, not hit API again
        mock_api.get_meal_type.assert_called_once()


class TestParseCustomerName:
    def test_with_name(self):
        assert OrderService._parse_customer_name("Ordered by Alice at 12:00:00") == "Alice"

    def test_without_name(self):
        assert OrderService._parse_customer_name("Ordered at 12:00:00") is None

    def test_empty_note(self):
        assert OrderService._parse_customer_name("") is None

    def test_name_containing_at(self):
        assert (
            OrderService._parse_customer_name("Ordered by Pat at the bar at 14:30:00")
            == "Pat at the bar"
        )

    def test_unrecognized_format(self):
        assert OrderService._parse_customer_name("some random note") is None
