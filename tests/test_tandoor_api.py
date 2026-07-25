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
    def test_date_range_is_the_last_n_days(self, mock_now, api):
        """Window is [today - days, today] — the recent cruft, not old plans."""
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

        # from_date = 7 days ago, to_date = today (NOT a year back, NOT ending at the cutoff)
        expected_from = (fake_now - timedelta(days=7)).strftime("%Y-%m-%d")
        expected_to = fake_now.strftime("%Y-%m-%d")

        meal_plan_call = api.session.get.call_args_list[0]
        params = meal_plan_call.kwargs.get("params") or meal_plan_call[1].get("params")
        assert params["from_date"] == expected_from, (
            f"from_date should be {expected_from} (days ago), got {params['from_date']}"
        )
        assert params["to_date"] == expected_to, (
            f"to_date should be today ({expected_to}), got {params['to_date']}"
        )

    @patch("morsl.tandoor_api.now")
    def test_deletes_uncooked_spares_cooked(self, mock_now, api):
        """Plans without a cook-log on/after their date get deleted; cooked ones survive."""
        fake_now = datetime(2026, 5, 8, 12, 0, 0)
        mock_now.return_value = fake_now

        plans_resp = MagicMock()
        plans_resp.status_code = 200
        plans_resp.json.return_value = [
            {"id": 10, "recipe": {"id": 100}, "from_date": "2026-05-01"},  # uncooked → delete
            {"id": 11, "recipe": {"id": 200}, "from_date": "2026-05-01"},  # cooked → survive
        ]

        cook_resp = MagicMock()
        cook_resp.status_code = 200
        cook_resp.json.return_value = [{"recipe": 200, "created_at": "2026-05-01T18:30:00Z"}]

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

    @patch("morsl.tandoor_api.now")
    def test_recipe_cooked_earlier_does_not_spare_later_plan(self, mock_now, api):
        """The core bug: cooking a recipe last week must NOT spare a later uncooked plan."""
        fake_now = datetime(2026, 5, 8, 12, 0, 0)
        mock_now.return_value = fake_now

        plans_resp = MagicMock()
        plans_resp.status_code = 200
        plans_resp.json.return_value = [
            {"id": 20, "recipe": {"id": 300}, "from_date": "2026-05-06"},  # this plan uncooked
        ]

        cook_resp = MagicMock()
        cook_resp.status_code = 200
        # Recipe 300 WAS cooked — but a week before this plan's date.
        cook_resp.json.return_value = [{"recipe": 300, "created_at": "2026-04-29T19:00:00Z"}]

        del_resp = MagicMock()
        del_resp.status_code = 204

        api.session.get.side_effect = [plans_resp, cook_resp]
        api.session.delete.return_value = del_resp

        deleted = api.cleanup_uncooked_meal_plans(meal_plan_type=3, days=1)

        assert deleted == 1, "a stale-recipe cook must not spare a newer uncooked plan"
        api.session.delete.assert_called_once_with(
            "http://tandoor.local/api/meal-plan/20/",
            timeout=DEFAULT_TIMEOUT,
        )

    @patch("morsl.tandoor_api.now")
    def test_cooked_next_day_still_spares_plan(self, mock_now, api):
        """Rating a meal the day after (created_at > from_date) still counts as cooked."""
        fake_now = datetime(2026, 5, 8, 12, 0, 0)
        mock_now.return_value = fake_now

        plans_resp = MagicMock()
        plans_resp.status_code = 200
        plans_resp.json.return_value = [
            {"id": 30, "recipe": {"id": 400}, "from_date": "2026-05-05"},
        ]

        cook_resp = MagicMock()
        cook_resp.status_code = 200
        cook_resp.json.return_value = [{"recipe": 400, "created_at": "2026-05-06T08:00:00Z"}]

        api.session.get.side_effect = [plans_resp, cook_resp]

        deleted = api.cleanup_uncooked_meal_plans(meal_plan_type=3, days=1)

        assert deleted == 0
        api.session.delete.assert_not_called()

    @patch("morsl.tandoor_api.now")
    def test_datetime_from_date_is_truncated_to_day(self, mock_now, api):
        """Tandoor stores from_date as a datetime; comparison must use the date part."""
        fake_now = datetime(2026, 5, 8, 12, 0, 0)
        mock_now.return_value = fake_now

        plans_resp = MagicMock()
        plans_resp.status_code = 200
        plans_resp.json.return_value = [
            {"id": 40, "recipe": {"id": 500}, "from_date": "2026-05-06T00:00:00Z"},
        ]

        cook_resp = MagicMock()
        cook_resp.status_code = 200
        cook_resp.json.return_value = [{"recipe": 500, "created_at": "2026-05-06T20:00:00Z"}]

        api.session.get.side_effect = [plans_resp, cook_resp]

        deleted = api.cleanup_uncooked_meal_plans(meal_plan_type=3, days=1)

        assert deleted == 0, "same-day cook should spare despite the datetime suffix"
        api.session.delete.assert_not_called()
