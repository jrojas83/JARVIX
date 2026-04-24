from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Awaitable, Callable


@dataclass(frozen=True)
class Event:
    type: str
    payload: dict[str, Any]


Handler = Callable[[Event], Awaitable[None]]


class EventBus:
    """
    Bus de eventos async (event-driven):
    - Publica eventos a una cola
    - Uno o más workers consumen y ejecutan handlers
    """

    def __init__(self) -> None:
        self._queue: asyncio.Queue[Event] = asyncio.Queue()
        self._handlers: dict[str, list[Handler]] = {}
        self._tasks: list[asyncio.Task] = []
        self._running = False

    def on(self, event_type: str, handler: Handler) -> None:
        self._handlers.setdefault(event_type, []).append(handler)

    async def emit(self, event_type: str, payload: dict[str, Any] | None = None) -> None:
        await self._queue.put(Event(type=event_type, payload=payload or {}))

    async def start(self, *, workers: int = 2) -> None:
        if self._running:
            return
        self._running = True
        for _ in range(max(1, workers)):
            self._tasks.append(asyncio.create_task(self._worker()))

    async def stop(self) -> None:
        self._running = False
        for t in self._tasks:
            t.cancel()
        self._tasks.clear()

    async def _worker(self) -> None:
        while self._running:
            ev = await self._queue.get()
            handlers = self._handlers.get(ev.type, [])
            if handlers:
                await asyncio.gather(*(h(ev) for h in handlers), return_exceptions=True)
            self._queue.task_done()

