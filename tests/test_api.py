from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.dependencies import (
    _admin_tokens,
    create_admin_token,
    get_config_service,
    get_credentials,
    get_generation_service,
    get_logger,
    get_meal_plan_service,
    get_order_service,
    get_settings,
    get_settings_service,
    revoke_admin_tokens,
)
from app.config import Settings
from app.main import app
from constants import API_CACHE_TTL_MINUTES
from services.config_service import ConfigService, ProfileInfo
from services.generation_service import GenerationService, GenerationState, GenerationStatus
from services.meal_plan_service import MealPlanService
from services.order_service import OrderService
from services.settings_service import SettingsService


@pytest.fixture
def mock_settings():
    return Settings(
        tandoor_url="http://test.local",
        tandoor_token="test_token",
        log_level="INFO",
        profiles_dir="profiles",
        data_dir="data",
    )


@pytest.fixture
def mock_gen_service():
    svc = MagicMock(spec=GenerationService)
    svc.get_status.return_value = GenerationStatus(state=GenerationState.IDLE)
    svc.get_current_menu.return_value = None
    return svc


@pytest.fixture
def mock_config_service():
    svc = MagicMock(spec=ConfigService)
    svc.list_profiles.return_value = [
        ProfileInfo(name="default", choices=5, constraint_count=2),
        ProfileInfo(name="weekend", choices=3, constraint_count=1),
    ]
    svc.load_profile.return_value = {"choices": 5, "cache": API_CACHE_TTL_MINUTES}
    return svc


@pytest.fixture
def mock_app_logger():
    logger = MagicMock()
    logger.loglevel = 20
    return logger


@pytest.fixture
def mock_settings_service():
    svc = MagicMock(spec=SettingsService)
    svc.get_all.return_value = {
        "orders_enabled": True,
        "ratings_enabled": True,
        "save_orders_to_tandoor": True,
        "save_ratings_to_tandoor": True,
        "theme": "cast-iron",
    }
    return svc


@pytest.fixture
def mock_order_service():
    svc = MagicMock(spec=OrderService)
    svc.place_order.return_value = {
        "id": "99",
        "recipe_id": 1,
        "recipe_name": "Test Cocktail",
        "timestamp": "2026-01-01T12:00:00",
        "servings": 1,
        "meal_plan_id": 99,
    }
    return svc


@pytest.fixture
def client(mock_settings, mock_gen_service, mock_config_service, mock_app_logger):
    app.dependency_overrides[get_settings] = lambda: mock_settings
    app.dependency_overrides[get_generation_service] = lambda: mock_gen_service
    app.dependency_overrides[get_config_service] = lambda: mock_config_service
    app.dependency_overrides[get_logger] = lambda: mock_app_logger
    app.dependency_overrides[get_credentials] = lambda: ("http://test.local", "test_token")
    yield AsyncClient(transport=ASGITransport(app=app), base_url="http://test")
    app.dependency_overrides.clear()


@pytest.fixture
def settings_client(mock_settings, mock_gen_service, mock_config_service, mock_app_logger,
                    mock_settings_service, mock_order_service):
    app.dependency_overrides[get_settings] = lambda: mock_settings
    app.dependency_overrides[get_generation_service] = lambda: mock_gen_service
    app.dependency_overrides[get_config_service] = lambda: mock_config_service
    app.dependency_overrides[get_logger] = lambda: mock_app_logger
    app.dependency_overrides[get_credentials] = lambda: ("http://test.local", "test_token")
    app.dependency_overrides[get_settings_service] = lambda: mock_settings_service
    app.dependency_overrides[get_order_service] = lambda: mock_order_service
    yield AsyncClient(transport=ASGITransport(app=app), base_url="http://test")
    app.dependency_overrides.clear()


@pytest.mark.asyncio
class TestHealthCheck:
    async def test_health(self, client):
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "credentials_configured" in data
        assert "scheduler_running" in data


@pytest.mark.asyncio
class TestGenerationEndpoints:
    async def test_generate_default(self, client, mock_gen_service):
        mock_gen_service.start_generation.return_value = "test-uuid-1234"
        response = await client.post("/api/generate")
        assert response.status_code == 202
        data = response.json()
        assert data["request_id"] == "test-uuid-1234"
        assert data["status"] == "generating"

    async def test_generate_profile(self, client, mock_gen_service):
        mock_gen_service.start_generation.return_value = "test-uuid-5678"
        response = await client.post("/api/generate/weekend")
        assert response.status_code == 202
        assert response.json()["request_id"] == "test-uuid-5678"

    async def test_generate_missing_profile(self, client, mock_config_service):
        mock_config_service.load_profile.side_effect = FileNotFoundError("Profile not found: profiles/missing.ini")
        response = await client.post("/api/generate/missing")
        assert response.status_code == 404

    async def test_generate_while_running(self, client, mock_gen_service):
        mock_gen_service.get_status.return_value = GenerationStatus(state=GenerationState.GENERATING)
        response = await client.post("/api/generate")
        assert response.status_code == 409

    async def test_generate_custom(self, client, mock_gen_service):
        mock_gen_service.start_generation.return_value = "custom-uuid"
        response = await client.post("/api/generate/custom", json={"choices": 3})
        assert response.status_code == 202
        assert response.json()["request_id"] == "custom-uuid"


@pytest.mark.asyncio
class TestMenuEndpoints:
    async def test_menu_not_found(self, client, mock_gen_service):
        mock_gen_service.get_current_menu.return_value = None
        response = await client.get("/api/menu")
        assert response.status_code == 404

    async def test_menu_found(self, client, mock_gen_service):
        mock_gen_service.get_current_menu.return_value = {
            "recipes": [{"id": 1, "name": "Test", "description": "", "rating": 3.0}],
            "generated_at": "2024-01-01T00:00:00",
            "requested_count": 5,
            "constraint_count": 0,
            "status": "optimal",
            "warnings": [],
            "relaxed_constraints": [],
        }
        response = await client.get("/api/menu")
        assert response.status_code == 200
        data = response.json()
        assert len(data["recipes"]) == 1
        assert "version" in data

    async def test_status_idle(self, client, mock_gen_service):
        response = await client.get("/api/status")
        assert response.status_code == 200
        assert response.json()["state"] == "idle"

    async def test_status_generating(self, client, mock_gen_service):
        mock_gen_service.get_status.return_value = GenerationStatus(
            state=GenerationState.GENERATING,
            request_id="running-uuid",
        )
        response = await client.get("/api/status")
        assert response.status_code == 200
        data = response.json()
        assert data["state"] == "generating"
        assert data["request_id"] == "running-uuid"


@pytest.mark.asyncio
class TestProfileEndpoints:
    async def test_list_profiles(self, client):
        response = await client.get("/api/profiles")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["name"] == "default"
        assert data[1]["name"] == "weekend"


@pytest.mark.asyncio
class TestSettingsEnforcement:
    """Tests for settings flag enforcement in orders and ratings endpoints."""

    async def test_order_disabled_returns_403(self, settings_client, mock_settings_service):
        mock_settings_service.get_all.return_value = {"orders_enabled": False}
        response = await settings_client.post(
            "/api/orders", json={"recipe_id": 1, "recipe_name": "Martini"}
        )
        assert response.status_code == 403
        assert "disabled" in response.json()["detail"]

    async def test_order_no_tandoor_save(self, settings_client, mock_settings_service, mock_order_service):
        mock_settings_service.get_all.return_value = {
            "orders_enabled": True,
            "save_orders_to_tandoor": False,
        }
        response = await settings_client.post(
            "/api/orders", json={"recipe_id": 1, "recipe_name": "Martini"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["meal_plan_id"] is None
        assert data["recipe_name"] == "Martini"
        mock_order_service.place_order.assert_not_called()
        mock_order_service.store_and_notify.assert_called_once()

    async def test_order_with_customer_name(self, settings_client, mock_settings_service, mock_order_service):
        mock_settings_service.get_all.return_value = {
            "orders_enabled": True,
            "save_orders_to_tandoor": True,
        }
        response = await settings_client.post(
            "/api/orders", json={"recipe_id": 1, "recipe_name": "Martini", "customer_name": "Bob"}
        )
        assert response.status_code == 200
        mock_order_service.place_order.assert_called_once_with(
            recipe_id=1, recipe_name="Martini", servings=1, customer_name="Bob", meal_type_id=None
        )

    async def test_order_without_customer_name(self, settings_client, mock_settings_service, mock_order_service):
        mock_settings_service.get_all.return_value = {
            "orders_enabled": True,
            "save_orders_to_tandoor": True,
        }
        response = await settings_client.post(
            "/api/orders", json={"recipe_id": 1, "recipe_name": "Martini"}
        )
        assert response.status_code == 200
        mock_order_service.place_order.assert_called_once_with(
            recipe_id=1, recipe_name="Martini", servings=1, customer_name=None, meal_type_id=None
        )

    async def test_order_local_includes_customer_name(self, settings_client, mock_settings_service, mock_order_service):
        mock_settings_service.get_all.return_value = {
            "orders_enabled": True,
            "save_orders_to_tandoor": False,
        }
        response = await settings_client.post(
            "/api/orders", json={"recipe_id": 1, "recipe_name": "Martini", "customer_name": "Eve"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["customer_name"] == "Eve"
        assert data["meal_plan_id"] is None

    async def test_rating_disabled_returns_403(self, settings_client, mock_settings_service):
        mock_settings_service.get_all.return_value = {"ratings_enabled": False}
        response = await settings_client.patch(
            "/api/recipe/5/rating", json={"rating": 4.5}
        )
        assert response.status_code == 403
        assert "disabled" in response.json()["detail"]

    async def test_rating_no_tandoor_save(self, settings_client, mock_settings_service):
        mock_settings_service.get_all.return_value = {
            "ratings_enabled": True,
            "save_ratings_to_tandoor": False,
        }
        response = await settings_client.patch(
            "/api/recipe/5/rating", json={"rating": 4.5}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["rating"] == 4.5

    async def test_rating_enabled_forwards_to_tandoor(self, settings_client, mock_settings_service):
        mock_settings_service.get_all.return_value = {
            "ratings_enabled": True,
            "save_ratings_to_tandoor": True,
        }
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b'{"rating": 4.5}'
        mock_response.json.return_value = {"rating": 4.5}
        mock_post_response = MagicMock()
        mock_post_response.status_code = 201
        with patch("app.api.routes.proxy.requests.patch", return_value=mock_response) as mock_patch, \
             patch("app.api.routes.proxy.requests.post", return_value=mock_post_response) as mock_post:
            response = await settings_client.patch(
                "/api/recipe/5/rating", json={"rating": 4.5}
            )
            assert response.status_code == 200
            mock_patch.assert_called_once()
            # Cook log entry created
            mock_post.assert_called_once()

    async def test_rating_cook_log_includes_customer_name(self, settings_client, mock_settings_service):
        mock_settings_service.get_all.return_value = {
            "ratings_enabled": True,
            "save_ratings_to_tandoor": True,
        }
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b'{"rating": 3.0}'
        mock_response.json.return_value = {"rating": 3.0}
        mock_post_response = MagicMock()
        mock_post_response.status_code = 201
        with patch("app.api.routes.proxy.requests.patch", return_value=mock_response), \
             patch("app.api.routes.proxy.requests.post", return_value=mock_post_response) as mock_post:
            response = await settings_client.patch(
                "/api/recipe/5/rating", json={"rating": 3.0, "customer_name": "Bob"}
            )
            assert response.status_code == 200
            # Verify cook log includes the customer name in comment
            call_kwargs = mock_post.call_args
            assert "Rated by Bob" in call_kwargs[1]["json"]["comment"]


@pytest.mark.asyncio
class TestOrderServerStorage:
    """Tests for server-side order persistence via the API."""

    async def test_get_orders_returns_server_stored(self, settings_client, mock_order_service):
        mock_order_service.get_orders.return_value = [
            {
                "id": "local-100",
                "recipe_id": 1,
                "recipe_name": "Mojito",
                "timestamp": "2026-01-01T12:00:00",
                "servings": 1,
                "meal_plan_id": None,
                "customer_name": None,
            }
        ]
        response = await settings_client.get("/api/orders")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == "local-100"
        assert data[0]["recipe_name"] == "Mojito"

    async def test_delete_local_order(self, settings_client, mock_order_service):
        response = await settings_client.delete("/api/orders/local-100")
        assert response.status_code == 204
        mock_order_service.delete_order.assert_called_once_with("local-100")

    async def test_delete_local_order_not_found(self, settings_client, mock_order_service):
        mock_order_service.delete_order.side_effect = RuntimeError("Server order not found")
        response = await settings_client.delete("/api/orders/local-999")
        assert response.status_code == 404

    async def test_local_order_stored_on_post(self, settings_client, mock_settings_service, mock_order_service):
        mock_settings_service.get_all.return_value = {
            "orders_enabled": True,
            "save_orders_to_tandoor": False,
        }
        response = await settings_client.post(
            "/api/orders", json={"recipe_id": 1, "recipe_name": "Negroni", "customer_name": "Alice"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"].startswith("local-")
        mock_order_service.store_and_notify.assert_called_once()
        stored = mock_order_service.store_and_notify.call_args[0][0]
        assert stored["recipe_name"] == "Negroni"
        assert stored["customer_name"] == "Alice"


@pytest.mark.asyncio
class TestVerifyPin:
    """Tests for POST /api/settings/verify-pin kiosk PIN verification."""

    async def test_correct_pin(self, settings_client, mock_settings_service):
        mock_settings_service.get_all.return_value = {
            "kiosk_enabled": True,
            "kiosk_pin_enabled": True,
            "kiosk_pin": "1234",
        }
        response = await settings_client.post(
            "/api/settings/verify-pin", json={"pin": "1234"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True
        assert isinstance(data["token"], str) and len(data["token"]) == 32

    async def test_wrong_pin(self, settings_client, mock_settings_service):
        mock_settings_service.get_all.return_value = {
            "kiosk_enabled": True,
            "kiosk_pin_enabled": True,
            "kiosk_pin": "1234",
        }
        response = await settings_client.post(
            "/api/settings/verify-pin", json={"pin": "9999"}
        )
        assert response.status_code == 200
        assert response.json() == {"valid": False}

    async def test_kiosk_disabled(self, settings_client, mock_settings_service):
        mock_settings_service.get_all.return_value = {
            "kiosk_enabled": False,
            "kiosk_pin_enabled": True,
            "kiosk_pin": "1234",
        }
        response = await settings_client.post(
            "/api/settings/verify-pin", json={"pin": "wrong"}
        )
        assert response.status_code == 200
        assert response.json() == {"valid": True}

    async def test_pin_disabled(self, settings_client, mock_settings_service):
        mock_settings_service.get_all.return_value = {
            "kiosk_enabled": True,
            "kiosk_pin_enabled": False,
            "kiosk_pin": "1234",
        }
        response = await settings_client.post(
            "/api/settings/verify-pin", json={"pin": "wrong"}
        )
        assert response.status_code == 200
        assert response.json() == {"valid": True}

    async def test_empty_stored_pin(self, settings_client, mock_settings_service):
        mock_settings_service.get_all.return_value = {
            "kiosk_enabled": True,
            "kiosk_pin_enabled": True,
            "kiosk_pin": "",
        }
        response = await settings_client.post(
            "/api/settings/verify-pin", json={"pin": "anything"}
        )
        assert response.status_code == 200
        assert response.json() == {"valid": True}

    async def test_admin_pin_correct(self, settings_client, mock_settings_service):
        mock_settings_service.get_all.return_value = {
            "admin_pin_enabled": True,
            "kiosk_enabled": False,
            "kiosk_pin_enabled": False,
            "kiosk_pin": "1234",
        }
        response = await settings_client.post(
            "/api/settings/verify-pin", json={"pin": "1234"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True
        assert "token" in data

    async def test_admin_pin_empty_bypasses(self, settings_client, mock_settings_service):
        mock_settings_service.get_all.return_value = {
            "admin_pin_enabled": True,
            "kiosk_enabled": False,
            "kiosk_pin_enabled": False,
            "kiosk_pin": "",
        }
        response = await settings_client.post(
            "/api/settings/verify-pin", json={"pin": "anything"}
        )
        assert response.status_code == 200
        assert response.json() == {"valid": True}

    async def test_both_admin_and_kiosk_pin(self, settings_client, mock_settings_service):
        mock_settings_service.get_all.return_value = {
            "admin_pin_enabled": True,
            "kiosk_enabled": True,
            "kiosk_pin_enabled": True,
            "kiosk_pin": "5678",
        }
        response = await settings_client.post(
            "/api/settings/verify-pin", json={"pin": "5678"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True
        assert "token" in data


@pytest.mark.asyncio
class TestAdminAuth:
    """Tests for server-side admin token authentication."""

    @pytest.fixture(autouse=True)
    def clear_tokens(self):
        _admin_tokens.clear()
        yield
        _admin_tokens.clear()

    async def test_admin_route_no_token_returns_401(self, settings_client, mock_settings_service):
        mock_settings_service.get_all.return_value = {
            "admin_pin_enabled": True,
            "kiosk_enabled": False,
            "kiosk_pin_enabled": False,
        }
        response = await settings_client.get("/api/settings")
        assert response.status_code == 401

    async def test_admin_route_invalid_token_returns_401(self, settings_client, mock_settings_service):
        mock_settings_service.get_all.return_value = {
            "admin_pin_enabled": True,
            "kiosk_enabled": False,
            "kiosk_pin_enabled": False,
        }
        response = await settings_client.get(
            "/api/settings", headers={"X-Admin-Token": "bad-token"},
        )
        assert response.status_code == 401

    async def test_admin_route_valid_token_succeeds(self, settings_client, mock_settings_service):
        token = create_admin_token()
        mock_settings_service.get_all.return_value = {
            "admin_pin_enabled": True,
            "kiosk_pin": "1234",
            "theme": "cast-iron",
        }
        response = await settings_client.get(
            "/api/settings", headers={"X-Admin-Token": token},
        )
        assert response.status_code == 200

    async def test_pin_disabled_allows_without_token(self, settings_client, mock_settings_service):
        mock_settings_service.get_all.return_value = {
            "admin_pin_enabled": False,
            "kiosk_enabled": False,
            "kiosk_pin_enabled": False,
            "kiosk_pin": "",
            "theme": "cast-iron",
        }
        response = await settings_client.get("/api/settings")
        assert response.status_code == 200

    async def test_get_settings_masks_pin(self, settings_client, mock_settings_service):
        mock_settings_service.get_all.return_value = {
            "kiosk_pin": "secret123",
            "theme": "cast-iron",
        }
        response = await settings_client.get("/api/settings")
        data = response.json()
        assert "kiosk_pin" not in data
        assert data["has_pin"] is True

    async def test_get_settings_has_pin_false_when_empty(self, settings_client, mock_settings_service):
        mock_settings_service.get_all.return_value = {
            "kiosk_pin": "",
            "theme": "cast-iron",
        }
        response = await settings_client.get("/api/settings")
        data = response.json()
        assert data["has_pin"] is False

    async def test_update_settings_masks_pin(self, settings_client, mock_settings_service):
        mock_settings_service.get_all.return_value = {"kiosk_pin": "old"}
        mock_settings_service.update.return_value = {
            "kiosk_pin": "new-pin",
            "theme": "cast-iron",
        }
        response = await settings_client.put(
            "/api/settings", json={"theme": "cast-iron"},
        )
        data = response.json()
        assert "kiosk_pin" not in data
        assert data["has_pin"] is True

    async def test_pin_change_revokes_tokens(self, settings_client, mock_settings_service):
        token = create_admin_token()
        assert token in _admin_tokens
        mock_settings_service.get_all.return_value = {"kiosk_pin": "old-pin"}
        mock_settings_service.update.return_value = {"kiosk_pin": "new-pin"}
        await settings_client.put(
            "/api/settings", json={"kiosk_pin": "new-pin"},
        )
        assert token not in _admin_tokens

    async def test_same_pin_keeps_tokens(self, settings_client, mock_settings_service):
        token = create_admin_token()
        mock_settings_service.get_all.return_value = {"kiosk_pin": "1234"}
        mock_settings_service.update.return_value = {"kiosk_pin": "1234"}
        await settings_client.put(
            "/api/settings", json={"kiosk_pin": "1234"},
        )
        assert token in _admin_tokens

    async def test_verify_pin_token_works_for_admin_routes(self, settings_client, mock_settings_service):
        mock_settings_service.get_all.return_value = {
            "admin_pin_enabled": True,
            "kiosk_pin": "9999",
            "theme": "cast-iron",
        }
        # Get token via verify-pin
        pin_res = await settings_client.post(
            "/api/settings/verify-pin", json={"pin": "9999"}
        )
        token = pin_res.json()["token"]
        # Use token to access admin route
        response = await settings_client.get(
            "/api/settings", headers={"X-Admin-Token": token},
        )
        assert response.status_code == 200

    async def test_verify_pin_no_token_on_failure(self, settings_client, mock_settings_service):
        mock_settings_service.get_all.return_value = {
            "admin_pin_enabled": True,
            "kiosk_pin": "1234",
        }
        response = await settings_client.post(
            "/api/settings/verify-pin", json={"pin": "wrong"}
        )
        data = response.json()
        assert data["valid"] is False
        assert "token" not in data

    async def test_public_settings_unprotected(self, settings_client, mock_settings_service):
        mock_settings_service.get_all.return_value = {
            "admin_pin_enabled": True,
            "kiosk_enabled": True,
            "kiosk_pin_enabled": True,
        }
        mock_settings_service.get_public.return_value = {"theme": "cast-iron"}
        response = await settings_client.get("/api/settings/public")
        assert response.status_code == 200

    async def test_revoke_clears_all_tokens(self):
        t1 = create_admin_token()
        t2 = create_admin_token()
        assert t1 in _admin_tokens
        assert t2 in _admin_tokens
        revoke_admin_tokens()
        assert t1 not in _admin_tokens
        assert t2 not in _admin_tokens


@pytest.mark.asyncio
class TestNewSettings:
    """Tests for the 4 new admin settings (menu_poll_seconds, toast_seconds,
    max_discover_generations, max_previous_recipes)."""

    @pytest.fixture(autouse=True)
    def setup(self, settings_client, mock_settings_service):
        self.client = settings_client
        self.svc = mock_settings_service

    async def test_new_settings_in_public_endpoint(self):
        self.svc.get_all.return_value = {}
        self.svc.get_public.return_value = {
            "theme": "cast-iron",
            "menu_poll_seconds": 60,
            "toast_seconds": 2,
            "max_discover_generations": 10,
            "max_previous_recipes": 50,
        }
        response = await self.client.get("/api/settings/public")
        assert response.status_code == 200
        data = response.json()
        assert data["menu_poll_seconds"] == 60
        assert data["toast_seconds"] == 2
        assert data["max_discover_generations"] == 10
        assert data["max_previous_recipes"] == 50

    async def test_new_settings_persist(self):
        updated = {
            "menu_poll_seconds": 30,
            "toast_seconds": 5,
            "max_discover_generations": 20,
            "max_previous_recipes": 100,
        }
        self.svc.get_all.return_value = {}
        self.svc.update.return_value = updated
        response = await self.client.put(
            "/api/settings",
            json=updated,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["menu_poll_seconds"] == 30
        assert data["toast_seconds"] == 5
        assert data["max_discover_generations"] == 20
        assert data["max_previous_recipes"] == 100


@pytest.fixture
def mock_meal_plan_service():
    svc = MagicMock(spec=MealPlanService)
    svc.save_menu.return_value = {"created": 2, "errors": [], "total": 2}
    return svc


@pytest.fixture
def meal_plan_client(mock_settings, mock_gen_service, mock_config_service, mock_app_logger,
                     mock_settings_service, mock_meal_plan_service):
    mock_settings_service.get_all.return_value = {"meal_plan_enabled": True}
    app.dependency_overrides[get_settings] = lambda: mock_settings
    app.dependency_overrides[get_generation_service] = lambda: mock_gen_service
    app.dependency_overrides[get_config_service] = lambda: mock_config_service
    app.dependency_overrides[get_logger] = lambda: mock_app_logger
    app.dependency_overrides[get_credentials] = lambda: ("http://test.local", "test_token")
    app.dependency_overrides[get_settings_service] = lambda: mock_settings_service
    app.dependency_overrides[get_meal_plan_service] = lambda: mock_meal_plan_service
    yield AsyncClient(transport=ASGITransport(app=app), base_url="http://test")
    app.dependency_overrides.clear()


MEAL_PLAN_BODY = {"date": "2026-03-01", "meal_type_id": 1}


@pytest.mark.asyncio
class TestMealPlanSave:
    async def test_disabled_returns_403(self, meal_plan_client, mock_settings_service):
        mock_settings_service.get_all.return_value = {"meal_plan_enabled": False}
        response = await meal_plan_client.post("/api/meal-plan", json=MEAL_PLAN_BODY)
        assert response.status_code == 403

    async def test_explicit_recipes_sent_directly(self, meal_plan_client, mock_meal_plan_service, mock_gen_service):
        body = {**MEAL_PLAN_BODY, "recipes": [{"id": 1, "name": "Pasta"}, {"id": 2, "name": "Salad"}]}
        response = await meal_plan_client.post("/api/meal-plan", json=body)
        assert response.status_code == 200
        mock_meal_plan_service.save_menu.assert_called_once_with(
            meal_plan_type_id=1,
            recipes=[{"id": 1, "name": "Pasta"}, {"id": 2, "name": "Salad"}],
            date="2026-03-01",
            shared=[],
        )
        mock_gen_service.get_current_menu.assert_not_called()

    async def test_explicit_empty_recipes_returns_404(self, meal_plan_client):
        body = {**MEAL_PLAN_BODY, "recipes": []}
        response = await meal_plan_client.post("/api/meal-plan", json=body)
        assert response.status_code == 404
        assert "No recipes" in response.json()["detail"]

    async def test_fallback_to_current_menu(self, meal_plan_client, mock_gen_service, mock_meal_plan_service):
        mock_gen_service.get_current_menu.return_value = {
            "recipes": [{"id": 10, "name": "Soup"}],
        }
        response = await meal_plan_client.post("/api/meal-plan", json=MEAL_PLAN_BODY)
        assert response.status_code == 200
        mock_meal_plan_service.save_menu.assert_called_once_with(
            meal_plan_type_id=1,
            recipes=[{"id": 10, "name": "Soup"}],
            date="2026-03-01",
            shared=[],
        )

    async def test_no_current_menu_returns_404(self, meal_plan_client, mock_gen_service):
        mock_gen_service.get_current_menu.return_value = None
        response = await meal_plan_client.post("/api/meal-plan", json=MEAL_PLAN_BODY)
        assert response.status_code == 404
        assert "No current menu" in response.json()["detail"]

    async def test_partial_failure_returns_207(self, meal_plan_client, mock_gen_service, mock_meal_plan_service):
        mock_gen_service.get_current_menu.return_value = {"recipes": [{"id": 1, "name": "A"}]}
        mock_meal_plan_service.save_menu.return_value = {"created": 1, "errors": ["one failed"], "total": 2}
        response = await meal_plan_client.post("/api/meal-plan", json=MEAL_PLAN_BODY)
        assert response.status_code == 207

    async def test_total_failure_returns_400(self, meal_plan_client, mock_gen_service, mock_meal_plan_service):
        mock_gen_service.get_current_menu.return_value = {"recipes": [{"id": 1, "name": "A"}]}
        mock_meal_plan_service.save_menu.return_value = {"created": 0, "errors": ["all failed"], "total": 2}
        response = await meal_plan_client.post("/api/meal-plan", json=MEAL_PLAN_BODY)
        assert response.status_code == 400

    async def test_shared_users_forwarded(self, meal_plan_client, mock_meal_plan_service):
        body = {**MEAL_PLAN_BODY, "recipes": [{"id": 1, "name": "X"}], "shared": [5, 8]}
        response = await meal_plan_client.post("/api/meal-plan", json=body)
        assert response.status_code == 200
        assert mock_meal_plan_service.save_menu.call_args.kwargs["shared"] == [5, 8]
