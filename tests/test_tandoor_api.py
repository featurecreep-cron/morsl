"""Tests for TandoorAPI._unpack_list — forward-compatibility with Tandoor Next."""

from __future__ import annotations

import json
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
