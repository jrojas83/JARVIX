from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass

from logger import log

from jarvis_core.ai.types import AiRequest, AiResponse


@dataclass(frozen=True)
class ProviderConfig:
    name: str
    timeout_s: float


def _trim_history(history: list[dict], max_msgs: int = 6) -> list[dict]:
    return [{"role": m["role"], "content": m["content"]} for m in history[-max_msgs:]]


async def call_ollama(req: AiRequest, *, url: str, model: str, timeout_s: float) -> AiResponse | None:
    # Ollama: mantenemos requests (sync) pero lo envolvemos en thread con timeout
    def _run_sync() -> AiResponse | None:
        import requests

        t0 = time.monotonic()
        try:
            r = requests.post(
                url,
                json={"model": model, "prompt": req.prompt, "stream": False},
                timeout=timeout_s,
            )
            raw = (r.json() or {}).get("response", "")
            text = (raw or "").strip()
            ms = int((time.monotonic() - t0) * 1000)
            return AiResponse(provider="ollama", text=text, latency_ms=ms) if text else None
        except Exception as e:
            log.warning("Ollama falló: %s", e)
            return None

    try:
        return await asyncio.wait_for(asyncio.to_thread(_run_sync), timeout=timeout_s + 0.25)
    except Exception:
        return None

