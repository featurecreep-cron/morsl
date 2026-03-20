from __future__ import annotations

import asyncio
import json
from unittest.mock import MagicMock, patch

import pytest

from morsl.constants import API_CACHE_TTL_MINUTES
from morsl.services.config_service import ConfigService
from morsl.services.generation_service import GenerationService, GenerationState
from morsl.services.menu_service import MenuService


class TestMenuService:
    def test_init_with_defaults(self, mock_logger):
        config = {
            "choices": 5,
            "cache": API_CACHE_TTL_MINUTES,
            "constraints": [],
        }
        with patch("morsl.services.menu_service.TandoorAPI"):
            service = MenuService(
                url="http://localhost", token="test", config=config, logger=mock_logger
            )
        assert service.choices == 5
        assert service.min_choices is None

    def test_init_with_min_choices(self, mock_logger):
        config = {
            "choices": 5,
            "min_choices": 3,
            "cache": 0,
        }
        with patch("morsl.services.menu_service.TandoorAPI"):
            service = MenuService(
                url="http://localhost", token="test", config=config, logger=mock_logger
            )
        assert service.min_choices == 3

    def test_parse_constraints_v2_format(self, mock_logger):
        """Test parsing v2 constraint format."""
        config = {
            "choices": 5,
            "cache": 0,
            "constraints": [
                {
                    "type": "keyword",
                    "items": [{"id": 1, "name": "Test"}],
                    "count": 3,
                    "operator": ">=",
                },
                {
                    "type": "food",
                    "items": [{"id": 10, "name": "Whiskey"}],
                    "count": 2,
                    "operator": ">=",
                },
            ],
        }
        with patch("morsl.services.menu_service.TandoorAPI"):
            service = MenuService(
                url="http://localhost", token="test", config=config, logger=mock_logger
            )

        assert len(service.constraints) == 2
        assert service.constraints[0]["type"] == "keyword"
        assert service.constraints[0]["item_ids"] == [1]
        assert service.constraints[0]["count"] == 3
        assert service.constraints[1]["type"] == "food"
        assert service.constraints[1]["item_ids"] == [10]

    def test_parse_constraints_with_except(self, mock_logger):
        """Test parsing constraints with except clause."""
        config = {
            "choices": 5,
            "cache": 0,
            "constraints": [
                {
                    "type": "food",
                    "items": [{"id": 1, "name": "Syrup"}],
                    "except": [{"id": 2, "name": "Sugar Syrup"}],
                    "count": 2,
                    "operator": ">=",
                },
            ],
        }
        with patch("morsl.services.menu_service.TandoorAPI"):
            service = MenuService(
                url="http://localhost", token="test", config=config, logger=mock_logger
            )

        assert service.constraints[0]["except_ids"] == [2]

    def test_parse_constraints_empty(self, mock_logger):
        config = {"choices": 5, "cache": 0, "constraints": []}
        with patch("morsl.services.menu_service.TandoorAPI"):
            service = MenuService(
                url="http://localhost", token="test", config=config, logger=mock_logger
            )
        assert service.constraints == []

    def test_prepare_recipes_all(self, mock_logger):
        config = {"choices": 2, "cache": 0, "constraints": []}
        mock_recipe_data = [
            {
                "id": 1,
                "name": "R1",
                "description": "",
                "new": False,
                "servings": 4,
                "keywords": [],
                "rating": 3.0,
                "last_cooked": None,
                "created_at": "2024-01-01T12:00:00+00:00",
            },
        ]
        with patch("morsl.services.menu_service.TandoorAPI") as MockAPI:
            api = MockAPI.return_value
            api.get_recipes.return_value = mock_recipe_data
            service = MenuService(
                url="http://localhost", token="test", config=config, logger=mock_logger
            )
            service.prepare_recipes()
        assert len(service.recipes) == 1
        assert service.recipes[0].id == 1


class TestConfigService:
    def test_load_profile(self, tmp_path):
        """Test loading a v2 JSON profile."""
        profiles_dir = tmp_path / "profiles"
        profiles_dir.mkdir()
        (profiles_dir / "base.json").write_text(
            json.dumps({"cache": 120, "choices": 3, "constraints": []})
        )
        (profiles_dir / "test.json").write_text(
            json.dumps(
                {
                    "choices": 7,
                    "constraints": [
                        {
                            "type": "keyword",
                            "items": [{"id": 1, "name": "Test"}],
                            "count": 7,
                            "operator": "==",
                        }
                    ],
                }
            )
        )

        svc = ConfigService(profiles_dir=str(profiles_dir))
        config = svc.load_profile("test")
        assert config["choices"] == 7
        assert config["cache"] == 120  # inherited from base
        assert len(config["constraints"]) == 1

    def test_load_profile_no_base(self, tmp_path):
        """Test loading profile without a base."""
        profiles_dir = tmp_path / "profiles"
        profiles_dir.mkdir()
        (profiles_dir / "solo.json").write_text(json.dumps({"choices": 4}))

        svc = ConfigService(profiles_dir=str(profiles_dir))
        config = svc.load_profile("solo")
        assert config["choices"] == 4

    def test_load_profile_missing(self, tmp_path):
        svc = ConfigService(profiles_dir=str(tmp_path))
        with pytest.raises(FileNotFoundError, match="Profile not found"):
            svc.load_profile("nonexistent")

    def test_list_profiles(self, tmp_path):
        """Test listing profiles shows constraint count."""
        profiles_dir = tmp_path / "profiles"
        profiles_dir.mkdir()
        (profiles_dir / "base.json").write_text(json.dumps({"choices": 5}))
        (profiles_dir / "weekday.json").write_text(
            json.dumps(
                {
                    "choices": 5,
                    "constraints": [
                        {"type": "keyword", "items": [], "count": 1, "operator": ">="}
                    ],
                }
            )
        )
        (profiles_dir / "weekend.json").write_text(json.dumps({"choices": 3, "constraints": []}))

        svc = ConfigService(profiles_dir=str(profiles_dir))
        profiles = svc.list_profiles()
        assert len(profiles) == 2
        names = [p.name for p in profiles]
        assert "weekday" in names
        assert "weekend" in names
        # base.json should not appear
        assert "base" not in names

        # Check constraint count
        weekday = next(p for p in profiles if p.name == "weekday")
        assert weekday.constraint_count == 1

    def test_list_profiles_empty_dir(self, tmp_path):
        svc = ConfigService(profiles_dir=str(tmp_path))
        assert svc.list_profiles() == []

    def test_list_profiles_nonexistent_dir(self):
        svc = ConfigService(profiles_dir="/nonexistent")
        assert svc.list_profiles() == []

    def test_profile_constraints_concatenated(self, tmp_path):
        """Test that constraints from base and profile are concatenated."""
        profiles_dir = tmp_path / "profiles"
        profiles_dir.mkdir()
        (profiles_dir / "base.json").write_text(
            json.dumps(
                {
                    "cache": API_CACHE_TTL_MINUTES,
                    "choices": 5,
                    "constraints": [
                        {
                            "type": "keyword",
                            "items": [{"id": 1, "name": "Base KW"}],
                            "count": 1,
                            "operator": ">=",
                        }
                    ],
                }
            )
        )
        (profiles_dir / "custom.json").write_text(
            json.dumps(
                {
                    "choices": 3,
                    "constraints": [
                        {
                            "type": "food",
                            "items": [{"id": 10, "name": "Whiskey"}],
                            "count": 2,
                            "operator": ">=",
                        }
                    ],
                }
            )
        )

        svc = ConfigService(profiles_dir=str(profiles_dir))
        config = svc.load_profile("custom")
        # choices overridden, constraints concatenated
        assert config["choices"] == 3
        assert len(config["constraints"]) == 2
        assert config["constraints"][0]["type"] == "keyword"
        assert config["constraints"][1]["type"] == "food"

    def test_create_profile(self, tmp_path):
        profiles_dir = tmp_path / "profiles"
        profiles_dir.mkdir()
        svc = ConfigService(profiles_dir=str(profiles_dir))

        result = svc.create_profile("new_profile", {"choices": 7, "description": "Fresh"})
        assert result["choices"] == 7
        assert (profiles_dir / "new_profile.json").is_file()

    def test_create_profile_duplicate_raises(self, tmp_path):
        profiles_dir = tmp_path / "profiles"
        profiles_dir.mkdir()
        (profiles_dir / "existing.json").write_text('{"choices": 5}')

        svc = ConfigService(profiles_dir=str(profiles_dir))
        with pytest.raises(FileExistsError):
            svc.create_profile("existing", {"choices": 5})

    def test_update_profile(self, tmp_path):
        profiles_dir = tmp_path / "profiles"
        profiles_dir.mkdir()
        (profiles_dir / "editable.json").write_text('{"choices": 5}')

        svc = ConfigService(profiles_dir=str(profiles_dir))
        result = svc.update_profile("editable", {"choices": 12})
        assert result["choices"] == 12

        saved = json.loads((profiles_dir / "editable.json").read_text())
        assert saved["choices"] == 12

    def test_update_profile_not_found(self, tmp_path):
        svc = ConfigService(profiles_dir=str(tmp_path))
        with pytest.raises(FileNotFoundError):
            svc.update_profile("ghost", {"choices": 5})

    def test_delete_profile(self, tmp_path):
        profiles_dir = tmp_path / "profiles"
        profiles_dir.mkdir()
        (profiles_dir / "doomed.json").write_text('{"choices": 5}')

        svc = ConfigService(profiles_dir=str(profiles_dir))
        svc.delete_profile("doomed")
        assert not (profiles_dir / "doomed.json").is_file()

    def test_delete_profile_not_found(self, tmp_path):
        svc = ConfigService(profiles_dir=str(tmp_path))
        with pytest.raises(FileNotFoundError):
            svc.delete_profile("ghost")

    def test_get_profile_raw(self, tmp_path):
        """Test getting raw profile without base merge."""
        profiles_dir = tmp_path / "profiles"
        profiles_dir.mkdir()
        (profiles_dir / "base.json").write_text(json.dumps({"cache": 300, "choices": 5}))
        (profiles_dir / "child.json").write_text(json.dumps({"choices": 8}))

        svc = ConfigService(profiles_dir=str(profiles_dir))
        raw = svc.get_profile_raw("child")
        assert raw["choices"] == 8
        assert "cache" not in raw  # Not merged with base

    @pytest.mark.parametrize(
        "name",
        [
            "../../settings",
            "../secret",
            "foo/bar",
            "",
            ".hidden",
        ],
    )
    def test_path_traversal_blocked(self, tmp_path, name):
        """Profile names with path separators or leading dots are rejected."""
        svc = ConfigService(profiles_dir=str(tmp_path))
        with pytest.raises(ValueError, match="Invalid profile name"):
            svc.get_profile_raw(name)
        with pytest.raises(ValueError, match="Invalid profile name"):
            svc.load_profile(name)
        with pytest.raises(ValueError, match="Invalid profile name"):
            svc.update_profile(name, {"choices": 5})
        with pytest.raises(ValueError, match="Invalid profile name"):
            svc.delete_profile(name)


@pytest.mark.slow
class TestOnHandSubstitution:
    """Tests for on-hand food substitution in GenerationService._sync_generate()."""

    def _make_solver_result(self):
        from morsl.models import SolverResult, make_recipe

        r = make_recipe(
            {
                "id": 1,
                "name": "Mojito",
                "description": "Minty",
                "new": False,
                "servings": 1,
                "keywords": [],
                "rating": 4.0,
                "last_cooked": None,
                "created_at": "2024-01-01T12:00:00+00:00",
            }
        )
        return SolverResult(recipes=(r,), requested_count=1, constraint_count=0)

    def _make_details(self, food_onhand=False):
        return {
            "image": "http://img/mojito.jpg",
            "working_time": 5,
            "cooking_time": 0,
            "steps": [
                {
                    "name": "Mix",
                    "instruction": "Muddle mint and lime.",
                    "time": 5,
                    "order": 0,
                    "ingredients": [
                        {
                            "amount": 2,
                            "unit": {"name": "oz"},
                            "food": {"id": 100, "name": "Lime Juice", "food_onhand": food_onhand},
                        }
                    ],
                }
            ],
        }

    def test_substitution_when_not_onhand(self, mock_logger):
        """When food is not on hand, substitute with an on-hand alternative."""
        with patch("morsl.services.generation_service.MenuService") as MockMS:
            ms = MockMS.return_value
            ms.prepare_data.return_value = None
            ms.recipes = [MagicMock()]
            ms.choices = 1
            ms.select_recipes.return_value = self._make_solver_result()
            ms.tandoor = MagicMock()
            ms.tandoor.get_recipe_details.return_value = self._make_details(food_onhand=False)
            ms.tandoor.get_food_substitutes.return_value = [{"id": 200}]
            ms.tandoor.get_food.return_value = {
                "id": 200,
                "name": "Lemon Juice",
                "food_onhand": True,
            }

            result = GenerationService._sync_generate(
                {"choices": 1, "cache": 0}, "http://localhost", "test", mock_logger
            )

        assert len(result["recipes"]) == 1
        assert result["recipes"][0]["ingredients"][0]["food"] == "Lemon Juice"
        ms.tandoor.get_food_substitutes.assert_called_once_with(100, substitute="food")

    def test_no_substitution_when_onhand(self, mock_logger):
        """When food is already on hand, no substitution occurs."""
        with patch("morsl.services.generation_service.MenuService") as MockMS:
            ms = MockMS.return_value
            ms.prepare_data.return_value = None
            ms.recipes = [MagicMock()]
            ms.choices = 1
            ms.select_recipes.return_value = self._make_solver_result()
            ms.tandoor = MagicMock()
            ms.tandoor.get_recipe_details.return_value = self._make_details(food_onhand=True)

            result = GenerationService._sync_generate(
                {"choices": 1, "cache": 0}, "http://localhost", "test", mock_logger
            )

        assert result["recipes"][0]["ingredients"][0]["food"] == "Lime Juice"
        ms.tandoor.get_food_substitutes.assert_not_called()

    def test_steps_and_timing_extracted(self, mock_logger):
        """Steps and timing are extracted from recipe details."""
        with patch("morsl.services.generation_service.MenuService") as MockMS:
            ms = MockMS.return_value
            ms.prepare_data.return_value = None
            ms.recipes = [MagicMock()]
            ms.choices = 1
            ms.select_recipes.return_value = self._make_solver_result()
            ms.tandoor = MagicMock()
            ms.tandoor.get_recipe_details.return_value = self._make_details(food_onhand=True)

            result = GenerationService._sync_generate(
                {"choices": 1, "cache": 0}, "http://localhost", "test", mock_logger
            )

        recipe = result["recipes"][0]
        assert recipe["working_time"] == 5
        assert recipe["cooking_time"] == 0
        assert len(recipe["steps"]) == 1
        assert recipe["steps"][0]["name"] == "Mix"
        assert recipe["steps"][0]["instruction"] == "Muddle mint and lime."
        assert recipe["steps"][0]["time"] == 5
        assert recipe["steps"][0]["order"] == 0

    def test_substitution_no_subs_available(self, mock_logger):
        """When no substitutes are available, keep original food."""
        with patch("morsl.services.generation_service.MenuService") as MockMS:
            ms = MockMS.return_value
            ms.prepare_data.return_value = None
            ms.recipes = [MagicMock()]
            ms.choices = 1
            ms.select_recipes.return_value = self._make_solver_result()
            ms.tandoor = MagicMock()
            ms.tandoor.get_recipe_details.return_value = self._make_details(food_onhand=False)
            ms.tandoor.get_food_substitutes.return_value = []

            result = GenerationService._sync_generate(
                {"choices": 1, "cache": 0}, "http://localhost", "test", mock_logger
            )

        assert result["recipes"][0]["ingredients"][0]["food"] == "Lime Juice"


class TestGenerationService:
    def test_initial_state_idle(self):
        svc = GenerationService(data_dir="/tmp/test_gen")
        status = svc.get_status()
        assert status.state == GenerationState.IDLE
        assert status.request_id is None

    def test_get_current_menu_none(self, tmp_path):
        svc = GenerationService(data_dir=str(tmp_path))
        assert svc.get_current_menu() is None

    def test_get_current_menu_from_file(self, tmp_path):
        menu_data = {"recipes": [{"id": 1, "name": "Test"}], "generated_at": "2024-01-01T00:00:00"}
        (tmp_path / "current_menu.json").write_text(json.dumps(menu_data))

        svc = GenerationService(data_dir=str(tmp_path))
        result = svc.get_current_menu()
        assert result is not None
        assert len(result["recipes"]) == 1

    def test_save_menu_atomic(self, tmp_path):
        svc = GenerationService(data_dir=str(tmp_path))
        menu_data = {"recipes": [], "generated_at": "2024-01-01T00:00:00"}
        svc._save_menu(menu_data)

        saved = json.loads((tmp_path / "current_menu.json").read_text())
        assert saved["generated_at"] == "2024-01-01T00:00:00"

    def test_start_generation_returns_request_id(self, mock_logger, tmp_path):
        svc = GenerationService(data_dir=str(tmp_path))
        config = {"choices": 5, "cache": 0}

        loop = asyncio.new_event_loop()
        try:
            # We mock _sync_generate to avoid actual solver execution
            with patch.object(
                svc,
                "_sync_generate",
                return_value={
                    "recipes": [{"id": 1, "name": "Test", "description": "", "rating": 3.0}],
                    "generated_at": "2024-01-01T00:00:00",
                    "requested_count": 5,
                    "constraint_count": 0,
                    "status": "optimal",
                    "warnings": [],
                    "relaxed_constraints": [],
                },
            ):
                request_id = loop.run_until_complete(self._async_start(svc, config, mock_logger))
            assert request_id is not None
            assert len(request_id) == 36  # UUID format
        finally:
            loop.close()

    async def _async_start(self, svc, config, logger):
        request_id = await svc.start_generation(
            config=config, url="http://localhost", token="test", logger=logger
        )
        # Wait for task to complete
        if svc._current_task:
            await svc._current_task
        return request_id

    def test_duplicate_generation_raises(self, mock_logger, tmp_path):
        svc = GenerationService(data_dir=str(tmp_path))
        svc._status.state = GenerationState.GENERATING
        with pytest.raises(RuntimeError, match="already in progress"):  # noqa: PT012
            # Must run in event loop context
            loop = asyncio.new_event_loop()
            try:
                loop.run_until_complete(self._async_start(svc, {}, mock_logger))
            finally:
                loop.close()

    def test_clear_menu(self, tmp_path):
        menu_data = {"recipes": [{"id": 1, "name": "Test"}]}
        (tmp_path / "current_menu.json").write_text(json.dumps(menu_data))
        svc = GenerationService(data_dir=str(tmp_path))
        assert svc.get_current_menu() is not None

        result = svc.clear_menu()
        assert result is True
        assert svc.get_current_menu() is None
        assert not (tmp_path / "current_menu.json").exists()

    def test_clear_menu_nothing_to_clear(self, tmp_path):
        svc = GenerationService(data_dir=str(tmp_path))
        result = svc.clear_menu()
        assert result is False
