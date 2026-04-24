from __future__ import annotations

import asyncio
import random
from dataclasses import dataclass
from typing import Awaitable, Callable, TypeVar

T = TypeVar("T")


@dataclass(frozen=True)
class RetryPolicy:
    max_attempts: int = 2
    base_delay_s: float = 0.25
    max_delay_s: float = 2.0
    jitter_s: float = 0.15


async def with_retry(
    fn: Callable[[], Awaitable[T]],
    *,
    is_retriable: Callable[[Exception], bool] | None = None,
    policy: RetryPolicy = RetryPolicy(),
    name: str = "operation",
) -> T:
    last_exc: Exception | None = None
    for attempt in range(1, policy.max_attempts + 1):
        try:
            return await fn()
        except Exception as e:
            last_exc = e
            if attempt >= policy.max_attempts:
                break
            if is_retriable is not None and not is_retriable(e):
                break
            delay = min(policy.max_delay_s, policy.base_delay_s * (2 ** (attempt - 1)))
            delay += random.uniform(0.0, policy.jitter_s)
            await asyncio.sleep(delay)
    assert last_exc is not None
    raise last_exc

