from __future__ import annotations

from morsl.services.history_service import HistoryService


class TestHistoryService:
    def test_empty_on_init(self, tmp_path):
        svc = HistoryService(data_dir=str(tmp_path))
        entries, total = svc.list_entries()
        assert entries == []
        assert total == 0

    def test_add_and_list(self, tmp_path):
        svc = HistoryService(data_dir=str(tmp_path))
        svc.add_entry({"id": "a", "status": "ok", "profile": "test"})
        svc.add_entry({"id": "b", "status": "ok", "profile": "test"})
        entries, total = svc.list_entries()
        assert total == 2
        assert entries[0]["id"] == "b"  # newest first
        assert entries[1]["id"] == "a"

    def test_list_pagination(self, tmp_path):
        svc = HistoryService(data_dir=str(tmp_path))
        for i in range(10):
            svc.add_entry({"id": str(i), "profile": "test"})
        entries, total = svc.list_entries(limit=3, offset=2)
        assert total == 10
        assert len(entries) == 3
        # Newest first, so offset=2 skips the two newest
        assert entries[0]["id"] == "7"

    def test_get_entry_found(self, tmp_path):
        svc = HistoryService(data_dir=str(tmp_path))
        svc.add_entry({"id": "target", "profile": "test"})
        svc.add_entry({"id": "other", "profile": "other"})
        result = svc.get_entry("target")
        assert result is not None
        assert result["profile"] == "test"

    def test_get_entry_not_found(self, tmp_path):
        svc = HistoryService(data_dir=str(tmp_path))
        svc.add_entry({"id": "a", "profile": "test"})
        assert svc.get_entry("missing") is None

    def test_clear(self, tmp_path):
        svc = HistoryService(data_dir=str(tmp_path))
        svc.add_entry({"id": "a", "profile": "test"})
        svc.add_entry({"id": "b", "profile": "test"})
        svc.clear()
        entries, total = svc.list_entries()
        assert total == 0
        assert entries == []

    def test_persistence(self, tmp_path):
        svc1 = HistoryService(data_dir=str(tmp_path))
        svc1.add_entry({"id": "persisted", "status": "ok", "profile": "test"})

        svc2 = HistoryService(data_dir=str(tmp_path))
        entries, total = svc2.list_entries()
        assert total == 1
        assert entries[0]["id"] == "persisted"

    def test_max_entries_trimmed(self, tmp_path):
        svc = HistoryService(data_dir=str(tmp_path))
        for i in range(svc.MAX_ENTRIES + 10):
            svc.add_entry({"id": str(i), "profile": "test"})
        _, total = svc.list_entries(limit=9999)
        assert total == svc.MAX_ENTRIES

    def test_analytics_empty(self, tmp_path):
        svc = HistoryService(data_dir=str(tmp_path))
        analytics = svc.get_analytics()
        assert analytics["total_generations"] == 0
        assert analytics["avg_duration_ms"] == 0
        assert analytics["most_relaxed"] == []

    def test_analytics_basic(self, tmp_path):
        svc = HistoryService(data_dir=str(tmp_path))
        svc.add_entry(
            {
                "id": "1",
                "duration_ms": 1000,
                "recipe_count": 5,
                "status": "optimal",
                "profile": "default",
                "relaxed_constraints": [],
            }
        )
        svc.add_entry(
            {
                "id": "2",
                "duration_ms": 2000,
                "recipe_count": 3,
                "status": "optimal",
                "profile": "default",
                "relaxed_constraints": [],
            }
        )
        analytics = svc.get_analytics()
        assert analytics["total_generations"] == 2
        assert analytics["avg_duration_ms"] == 1500
        assert analytics["avg_recipes_per_generation"] == 4.0
        assert analytics["status_counts"]["optimal"] == 2
        assert analytics["profile_counts"]["default"] == 2

    def test_analytics_relaxed_constraints(self, tmp_path):
        svc = HistoryService(data_dir=str(tmp_path))
        svc.add_entry(
            {
                "id": "1",
                "duration_ms": 100,
                "recipe_count": 3,
                "status": "relaxed",
                "profile": "test",
                "relaxed_constraints": [
                    {"label": "Must have gin", "slack_value": 1.0},
                ],
            }
        )
        svc.add_entry(
            {
                "id": "2",
                "duration_ms": 200,
                "recipe_count": 3,
                "status": "relaxed",
                "profile": "test",
                "relaxed_constraints": [
                    {"label": "Must have gin", "slack_value": 2.0},
                    {"label": "High rated", "slack_value": 0.5},
                ],
            }
        )
        analytics = svc.get_analytics()
        relaxed = {r["label"]: r for r in analytics["most_relaxed"]}
        assert relaxed["Must have gin"]["times_relaxed"] == 2
        assert relaxed["Must have gin"]["avg_slack"] == 1.5
        assert relaxed["High rated"]["times_relaxed"] == 1
