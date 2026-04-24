from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AiRequest:
    prompt: str
    # Historial estilo OpenAI: [{"role": "user"|"assistant", "content": "..."}]
    history: list[dict]


@dataclass(frozen=True)
class AiResponse:
    provider: str
    text: str
    latency_ms: int

