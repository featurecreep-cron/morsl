"""Tests for GenerationService SSE pub/sub and clear_others flow."""

from __future__ import annotations

import asyncio
import json

import pytest

from morsl.services.generation_service import GenerationService


class TestSubscribePubSub:
    """subscribe / unsubscribe / _notify_subscribers mechanics."""

    def test_subscribe_returns_queue(self, tmp_path):
        svc = GenerationService(data_dir=str(tmp_path))
        q = svc.subscribe()
        assert isinstance(q, asyncio.Queue)
        assert q.maxsize == 64

    def test_subscribe_adds_to_list(self, tmp_path):
        svc = GenerationService(data_dir=str(tmp_path))
        q = svc.subscribe()
        assert q in svc._subscribers

    def test_unsubscribe_removes_queue(self, tmp_path):
        svc = GenerationService(data_dir=str(tmp_path))
        q = svc.subscribe()
        svc.unsubscribe(q)
        assert q not in svc._subscribers

    def test_unsubscribe_unknown_queue_no_error(self, tmp_path):
        svc = GenerationService(data_dir=str(tmp_path))
        q = asyncio.Queue()
        svc.unsubscribe(q)  # should not raise

    def test_notify_delivers_to_all_subscribers(self, tmp_path):
        svc = GenerationService(data_dir=str(tmp_path))
        q1 = svc.subscribe()
        q2 = svc.subscribe()
        event = {"type": "test_event"}
        svc._notify_subscribers(event)
        assert q1.get_nowait() == event
        assert q2.get_nowait() == event

    def test_notify_skips_full_queues(self, tmp_path):
        svc = GenerationService(data_dir=str(tmp_path))
        q = svc.subscribe()
        # Fill the queue to capacity
        for i in range(64):
            q.put_nowait({"type": "filler", "n": i})
        # This should not raise — full queue is silently skipped
        svc._notify_subscribers({"type": "overflow"})
        assert q.qsize() == 64  # still full, overflow was dropped

    def test_notify_with_no_subscribers(self, tmp_path):
        svc = GenerationService(data_dir=str(tmp_path))
        svc._notify_subscribers({"type": "lonely"})  # should not raise


class TestEventEmission:
    """Verify correct events are emitted on state transitions."""

    def test_clear_menu_emits_menu_cleared(self, tmp_path):
        menu = {"recipes": [{"id": 1, "name": "X"}]}
        (tmp_path / "current_menu.json").write_text(json.dumps(menu))
        svc = GenerationService(data_dir=str(tmp_path))

        q = svc.subscribe()
        svc.clear_menu()

        event = q.get_nowait()
        assert event["type"] == "menu_cleared"

    def test_clear_menu_no_event_when_nothing_to_clear(self, tmp_path):
        svc = GenerationService(data_dir=str(tmp_path))
        q = svc.subscribe()
        svc.clear_menu()
        assert q.empty()

    def test_save_menu_emits_menu_updated(self, tmp_path):
        svc = GenerationService(data_dir=str(tmp_path))
        q = svc.subscribe()
        svc._save_menu({"recipes": [], "generated_at": "2024-01-01"})

        event = q.get_nowait()
        assert event["type"] == "menu_updated"
        assert event["clear_others"] is False

    def test_save_menu_with_clear_others(self, tmp_path):
        svc = GenerationService(data_dir=str(tmp_path))
        q = svc.subscribe()
        svc._save_menu(
            {"recipes": [], "generated_at": "2024-01-01"},
            clear_others=True,
        )

        event = q.get_nowait()
        assert event["type"] == "menu_updated"
        assert event["clear_others"] is True

    def test_clear_others_not_persisted_in_json(self, tmp_path):
        """clear_others must NOT be in the saved JSON — it's SSE-only."""
        svc = GenerationService(data_dir=str(tmp_path))
        svc._save_menu(
            {"recipes": [], "generated_at": "2024-01-01"},
            clear_others=True,
        )
        saved = json.loads((tmp_path / "current_menu.json").read_text())
        assert "clear_others" not in saved

    @pytest.mark.asyncio
    async def test_start_generation_emits_generating(self, tmp_path, mock_logger):
        svc = GenerationService(data_dir=str(tmp_path))
        q = svc.subscribe()

        from unittest.mock import patch

        with patch.object(
            svc,
            "_sync_generate",
            return_value={
                "recipes": [{"id": 1, "name": "T", "description": "", "rating": 3.0}],
                "generated_at": "2024-01-01",
                "requested_count": 1,
                "constraint_count": 0,
                "status": "optimal",
                "warnings": [],
                "relaxed_constraints": [],
            },
        ):
            await svc.start_generation(
                config={"choices": 1, "cache": 0},
                url="http://localhost",
                token="test",
                logger=mock_logger,
            )
            if svc._current_task:
                await svc._current_task

        # Should have received: generating, then menu_updated
        events = []
        while not q.empty():
            events.append(q.get_nowait())
        types = [e["type"] for e in events]
        assert "generating" in types
        assert "menu_updated" in types
        assert types.index("generating") < types.index("menu_updated")
