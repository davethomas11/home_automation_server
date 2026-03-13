"""In-memory pub/sub for automation run events (SSE)."""

from __future__ import annotations

import asyncio
import time
from collections import defaultdict, deque
from typing import Any


class AutomationEventBroker:
    """Fan out automation events to all subscribers for a flow."""

    def __init__(self) -> None:
        self._subscribers: dict[int, set[asyncio.Queue[dict[str, Any]]]] = defaultdict(set)
        self._history: dict[int, deque[dict[str, Any]]] = defaultdict(lambda: deque(maxlen=512))
        self._lock = asyncio.Lock()

    async def subscribe(self, flow_id: int) -> asyncio.Queue[dict[str, Any]]:
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        async with self._lock:
            self._subscribers[flow_id].add(queue)
        return queue

    async def unsubscribe(self, flow_id: int, queue: asyncio.Queue[dict[str, Any]]) -> None:
        async with self._lock:
            subscribers = self._subscribers.get(flow_id)
            if not subscribers:
                return
            subscribers.discard(queue)
            if not subscribers:
                self._subscribers.pop(flow_id, None)

    async def publish(self, flow_id: int, event: dict[str, Any]) -> None:
        async with self._lock:
            targets = list(self._subscribers.get(flow_id, ()))
            self._history[flow_id].append(event)
        for queue in targets:
            await queue.put(event)

    async def get_history(self, flow_id: int, run_id: str | None = None) -> list[dict[str, Any]]:
        async with self._lock:
            events = list(self._history.get(flow_id, ()))
        if run_id is None:
            return events
        return [event for event in events if event.get("run_id") == run_id]


broker = AutomationEventBroker()


def make_event(event_type: str, *, flow_id: int, run_id: str, **data: Any) -> dict[str, Any]:
    """Build a normalized event payload for SSE clients."""
    return {
        "type": event_type,
        "flow_id": flow_id,
        "run_id": run_id,
        "ts": time.time(),
        **data,
    }

