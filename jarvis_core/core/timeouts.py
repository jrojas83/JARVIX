from __future__ import annotations

import asyncio
from typing import Awaitable, TypeVar

T = TypeVar("T")


class TimeoutError(Exception):
    pass


async def with_timeout(awaitable: Awaitable[T], timeout_s: float, *, name: str = "operation") -> T:
    try:
        return await asyncio.wait_for(awaitable, timeout=timeout_s)
    except asyncio.TimeoutError as e:
        raise TimeoutError(f"Timeout in {name} after {timeout_s:.1f}s") from e

