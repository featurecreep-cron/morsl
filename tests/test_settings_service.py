from __future__ import annotations

import json

from morsl.services.settings_service import DEFAULTS, PUBLIC_KEYS, SettingsService


class TestSettingsService:
    def test_defaults_on_init(self, tmp_path):
        svc = SettingsService(data_dir=str(tmp_path))
        settings = svc.get_all()
        assert settings["ratings_enabled"] is True
        assert settings["orders_enabled"] is False
        assert settings["theme"] == "cast-iron"

    def test_update_valid_key(self, tmp_path):
        svc = SettingsService(data_dir=str(tmp_path))
        result = svc.update({"theme": "dark-roast"})
        assert result["theme"] == "dark-roast"
        # Verify persisted
        svc2 = SettingsService(data_dir=str(tmp_path))
        assert svc2.get_all()["theme"] == "dark-roast"

    def test_update_ignores_unknown_keys(self, tmp_path):
        svc = SettingsService(data_dir=str(tmp_path))
        result = svc.update({"unknown_key": "value", "theme": "test"})
        assert "unknown_key" not in result
        assert result["theme"] == "test"

    def test_update_clamps_bounded_values(self, tmp_path):
        svc = SettingsService(data_dir=str(tmp_path))
        result = svc.update({"menu_poll_seconds": 5})  # min is 10
        assert result["menu_poll_seconds"] == 10
        result = svc.update({"menu_poll_seconds": 999})  # max is 300
        assert result["menu_poll_seconds"] == 300

    def test_update_invalid_bounded_value_uses_default(self, tmp_path):
        svc = SettingsService(data_dir=str(tmp_path))
        result = svc.update({"menu_poll_seconds": "not a number"})
        assert result["menu_poll_seconds"] == DEFAULTS["menu_poll_seconds"]

    def test_timezone_readonly(self, tmp_path, monkeypatch):
        monkeypatch.setenv("TZ", "America/Chicago")
        svc = SettingsService(data_dir=str(tmp_path))
        # Timezone comes from env, not settings
        assert svc.get_all()["timezone"] == "America/Chicago"
        # Can't override via update
        svc.update({"timezone": "Europe/London"})
        assert svc.get_all()["timezone"] == "America/Chicago"

    def test_get_public_filters_keys(self, tmp_path):
        svc = SettingsService(data_dir=str(tmp_path))
        public = svc.get_public()
        for key in public:
            assert key in PUBLIC_KEYS
        # Private keys should not be in public
        assert "pin" not in public
        assert "tandoor_token_b64" not in public
        assert "api_cache_minutes" not in public

    def test_get_timezone(self, tmp_path, monkeypatch):
        monkeypatch.setenv("TZ", "US/Eastern")
        svc = SettingsService(data_dir=str(tmp_path))
        tz = svc.get_timezone()
        assert str(tz) == "US/Eastern"

    def test_get_timezone_invalid_fallback(self, tmp_path, monkeypatch):
        monkeypatch.setenv("TZ", "Not/A/Timezone")
        svc = SettingsService(data_dir=str(tmp_path))
        tz = svc.get_timezone()
        assert str(tz) == "UTC"

    def test_persistence_across_instances(self, tmp_path):
        svc1 = SettingsService(data_dir=str(tmp_path))
        svc1.update({"app_name": "TestBar"})

        svc2 = SettingsService(data_dir=str(tmp_path))
        assert svc2.get_all()["app_name"] == "TestBar"

    def test_load_with_migrated_kiosk_pin(self, tmp_path):
        """Old kiosk_pin key should migrate to pin."""
        (tmp_path / "settings.json").write_text(json.dumps({"kiosk_pin": "1234", "theme": "dark"}))
        svc = SettingsService(data_dir=str(tmp_path))
        settings = svc.get_all()
        assert settings["pin"] == "1234"
        assert settings["theme"] == "dark"

    def test_new_defaults_on_upgrade(self, tmp_path):
        """Settings file from older version missing new keys gets defaults."""
        (tmp_path / "settings.json").write_text(
            json.dumps({"theme": "custom", "ratings_enabled": False})
        )
        svc = SettingsService(data_dir=str(tmp_path))
        settings = svc.get_all()
        assert settings["theme"] == "custom"
        assert settings["ratings_enabled"] is False
        # New keys get their defaults
        assert settings["qr_show_on_menu"] is False

    def test_migrate_default_profile(self, tmp_path):
        (tmp_path / "settings.json").write_text(json.dumps({"default_profile": "cocktails"}))
        svc = SettingsService(data_dir=str(tmp_path))

        class FakeConfigService:
            def __init__(self):
                self.default_set = None

            def set_default_profile(self, name):
                self.default_set = name

        config_svc = FakeConfigService()
        svc.migrate_default_profile(config_svc)
        assert config_svc.default_set == "cocktails"
        # Key should be removed from settings
        assert "default_profile" not in svc.get_all()
