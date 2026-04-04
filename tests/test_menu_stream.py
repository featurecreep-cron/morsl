"""Tests for the /api/menu/stream SSE endpoint.

Pub/sub delivery is tested in test_generation_sse.py (same-thread, fast).
These tests verify the HTTP endpoint wiring: content-type, subscriber lifecycle,
and event formatting through the SSE generator.
"""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from morsl.services.generation_service import GenerationService


@pytest.fixture
def gen_service(tmp_path):
    return GenerationService(data_dir=str(tmp_path))


class TestMenuStreamEventGenerator:
    """Test the SSE event generator directly — no HTTP layer, no cross-thread issues."""

    @pytest.mark.asyncio
    async def test_yields_connected_event_first(self, gen_service):
        """First yielded chunk is the connected event."""
        from morsl.app.api.routes.menu import menu_stream

        # Build a mock request to get the StreamingResponse
        mock_service = gen_service
        response = await menu_stream(gen_service=mock_service)

        assert response.media_type == "text/event-stream"
        assert response.headers.get("Cache-Control") == "no-cache"

        # Iterate the body generator
        body_gen = response.body_iterator
        first_chunk = await body_gen.__anext__()
        assert "event: connected" in first_chunk
        assert "data: {}" in first_chunk

        # Cleanup — cancel the generator
        await body_gen.aclose()

    @pytest.mark.asyncio
    async def test_delivers_event_from_queue(self, gen_service):
        """Events pushed to the subscriber queue appear in the SSE stream."""
        from morsl.app.api.routes.menu import menu_stream

        response = await menu_stream(gen_service=gen_service)
        body_gen = response.body_iterator

        # Consume connected event
        await body_gen.__anext__()

        # Push an event — since we're in the same event loop, put_nowait works
        gen_service._notify_subscribers({"type": "menu_updated", "clear_others": False})

        # Next chunk should be the menu_updated event
        chunk = await body_gen.__anext__()
        assert "event: menu_updated" in chunk
        assert "clear_others" in chunk

        await body_gen.aclose()

    @pytest.mark.asyncio
    async def test_keepalive_on_timeout(self, gen_service):
        """When queue is empty and timeout expires, yields keepalive comment."""
        from morsl.app.api.routes.menu import menu_stream

        with patch("morsl.app.api.routes.menu.SSE_QUEUE_TIMEOUT", 0.05):
            response = await menu_stream(gen_service=gen_service)
            body_gen = response.body_iterator

            # Consume connected event
            await body_gen.__anext__()

            # Wait for keepalive (timeout is 0.05s)
            chunk = await body_gen.__anext__()
            assert chunk == ": keepalive\n\n"

            await body_gen.aclose()

    @pytest.mark.asyncio
    async def test_unsubscribes_on_close(self, gen_service):
        """Closing the generator removes the subscriber queue."""
        from morsl.app.api.routes.menu import menu_stream

        response = await menu_stream(gen_service=gen_service)
        body_gen = response.body_iterator

        # After calling menu_stream, a subscriber should exist
        assert len(gen_service._subscribers) == 1

        await body_gen.__anext__()  # consume connected
        await body_gen.aclose()

        # After close, subscriber should be removed
        assert len(gen_service._subscribers) == 0

    @pytest.mark.asyncio
    async def test_formats_event_as_sse(self, gen_service):
        """Events are formatted with SSE event: and data: lines."""
        from morsl.app.api.routes.menu import menu_stream

        response = await menu_stream(gen_service=gen_service)
        body_gen = response.body_iterator
        await body_gen.__anext__()  # connected

        gen_service._notify_subscribers({"type": "menu_cleared"})
        chunk = await body_gen.__anext__()

        # Verify SSE format: event line, data line, blank line
        lines = chunk.strip().split("\n")
        assert lines[0] == "event: menu_cleared"
        assert lines[1].startswith("data: ")
        data = json.loads(lines[1][len("data: ") :])
        assert data["type"] == "menu_cleared"

        await body_gen.aclose()
