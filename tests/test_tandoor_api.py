"""Tests for TandoorAPI."""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from morsl.constants import DEFAULT_TIMEOUT
from morsl.tandoor_api import TandoorAPI


@pytest.fixture
def api():
    """Create a TandoorAPI instance with mocked session."""
    with patch("morsl.tandoor_api.requests.Session"):
        instance = TandoorAPI(
            url="http://tandoor.local",
            token="test-token",
            logger=MagicMock(),
        )
    return instance


class TestUnpackList:
    """Test the three response shapes _unpack_list handles."""

    def test_raw_list(self, api):
        """Shape 1: Current Tandoor returns a plain list."""
        data = [{"id": 1}, {"id": 2}, {"id": 3}]
        assert api._unpack_list(data) == [{"id": 1}, {"id": 2}, {"id": 3}]

    def test_paginated_single_page(self, api):
        """Shape 2: Tandoor Next returns paginated dict, all results in one page."""
        data = {
            "count": 2,
            "next": None,
            "previous": None,
            "results": [{"id": 1}, {"id": 2}],
        }
        assert api._unpack_list(data) == [{"id": 1}, {"id": 2}]

    def test_paginated_multi_page(self, api):
        """Shape 3: Tandoor Next returns paginated dict spanning multiple pages."""
        page1 = {
            "count": 4,
            "next": "http://tandoor.local/api/meal-plan/?page=2",
            "previous": None,
            "results": [{"id": 1}, {"id": 2}],
        }
        page2_response = MagicMock()
        page2_response.status_code = 200
        page2_response.content = json.dumps(
            {
                "count": 4,
                "next": None,
                "previous": "http://tandoor.local/api/meal-plan/?page=1",
                "results": [{"id": 3}, {"id": 4}],
            }
        ).encode()

        api.session.get.return_value = page2_response
        result = api._unpack_list(page1)
        assert result == [{"id": 1}, {"id": 2}, {"id": 3}, {"id": 4}]
        api.session.get.assert_called_once_with(
            "http://tandoor.local/api/meal-plan/?page=2", timeout=DEFAULT_TIMEOUT
        )

    def test_paginated_page_error_returns_partial(self, api):
        """If a subsequent page fails, return what we have and log a warning."""
        page1 = {
            "count": 4,
            "next": "http://tandoor.local/api/meal-plan/?page=2",
            "results": [{"id": 1}, {"id": 2}],
        }
        error_response = MagicMock()
        error_response.status_code = 500

        api.session.get.return_value = error_response
        result = api._unpack_list(page1)
        assert result == [{"id": 1}, {"id": 2}]
        api.logger.warning.assert_called_once()

    def test_empty_list(self, api):
        assert api._unpack_list([]) == []

    def test_empty_paginated(self, api):
        data = {"count": 0, "next": None, "results": []}
        assert api._unpack_list(data) == []


class TestCleanupUncookedMealPlans:
    """Verify cleanup targets plans OLDER than the cutoff, not recent ones."""

    @patch("morsl.tandoor_api.now")
    def test_date_range_targets_old_plans(self, mock_now, api):
        """from_date..to_date must cover the past, ending at the cutoff day."""
        fake_now = datetime(2026, 5, 8, 12, 0, 0)
        mock_now.return_value = fake_now

        plans_resp = MagicMock()
        plans_resp.status_code = 200
        plans_resp.json.return_value = []

        cook_resp = MagicMock()
        cook_resp.status_code = 200
        cook_resp.json.return_value = []

        api.session.get.side_effect = [plans_resp, cook_resp]

        api.cleanup_uncooked_meal_plans(meal_plan_type=3, days=7)

        # to_date should be 7 days ago (the cutoff), NOT yesterday
        expected_to = (fake_now - timedelta(days=7)).strftime("%Y-%m-%d")
        expected_from = (fake_now - timedelta(days=365)).strftime("%Y-%m-%d")

        meal_plan_call = api.session.get.call_args_list[0]
        params = meal_plan_call.kwargs.get("params") or meal_plan_call[1].get("params")
        assert params["to_date"] == expected_to, (
            f"to_date should be the cutoff ({expected_to}), got {params['to_date']}"
        )
        assert params["from_date"] == expected_from

    @patch("morsl.tandoor_api.now")
    def test_deletes_uncooked_spares_cooked(self, mock_now, api):
        """Plans without cook-log entries get deleted; cooked ones survive."""
        fake_now = datetime(2026, 5, 8, 12, 0, 0)
        mock_now.return_value = fake_now

        plans_resp = MagicMock()
        plans_resp.status_code = 200
        plans_resp.json.return_value = [
            {"id": 10, "recipe": {"id": 100}},  # uncooked — should be deleted
            {"id": 11, "recipe": {"id": 200}},  # cooked — should survive
        ]

        cook_resp = MagicMock()
        cook_resp.status_code = 200
        cook_resp.json.return_value = [{"recipe": 200}]

        del_resp = MagicMock()
        del_resp.status_code = 204

        api.session.get.side_effect = [plans_resp, cook_resp]
        api.session.delete.return_value = del_resp

        deleted = api.cleanup_uncooked_meal_plans(meal_plan_type=3, days=7)

        assert deleted == 1
        api.session.delete.assert_called_once_with(
            "http://tandoor.local/api/meal-plan/10/",
            timeout=DEFAULT_TIMEOUT,
        )
