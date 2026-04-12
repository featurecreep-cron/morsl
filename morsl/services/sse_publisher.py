from __future__ import annotations

import asyncio
import contextlib
import threading
from typing import Any, Dict, List


class SSEPublisher:
    """Mixin for services that push events to SSE subscriber queues.

    Provides subscribe/unsubscribe/notify with automatic cleanup of
    dead subscribers (detected via QueueFull on put_nowait).
    """

    def _init_sse(self) -> None:
        """Call from __init__ to set up SSE state."""
        self._subscribers: List[asyncio.Queue[Dict[str, Any]]] = []
        self._sub_lock = threading.Lock()

    def subscribe(self) -> asyncio.Queue[Dict[str, Any]]:
        """Create a new SSE subscriber queue."""
        q: asyncio.Queue[Dict[str, Any]] = asyncio.Queue(maxsize=64)
        with self._sub_lock:
            self._subscribers.append(q)
        return q

    def unsubscribe(self, q: asyncio.Queue[Dict[str, Any]]) -> None:
        """Remove subscriber queue."""
        with self._sub_lock, contextlib.suppress(ValueError):
            self._subscribers.remove(q)

    def _notify_subscribers(self, event: Dict[str, Any]) -> None:
        """Push event to all SSE subscribers (non-blocking).

        Automatically removes subscribers whose queues are full (dead clients).
        """
        with self._sub_lock:
            subscribers = list(self._subscribers)
        dead: List[asyncio.Queue[Dict[str, Any]]] = []
        for q in subscribers:
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                dead.append(q)
        if dead:
            with self._sub_lock:
                for q in dead:
                    with contextlib.suppress(ValueError):
                        self._subscribers.remove(q)
