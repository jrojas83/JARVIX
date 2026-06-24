from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass

from logger import log

from jarvis_core.ai.providers import call_ollama
from jarvis_core.ai.types import AiRequest, AiResponse
from jarvis_core.core.circuit_breaker import CircuitBreaker
from jarvis_core.core.retry import RetryPolicy, with_retry


@dataclass(frozen=True)
class OrchestratorConfig:
    # Timeouts por proveedor (segundos)
    ollama_timeout_s: float = 40.0

    # Resiliencia
    retry_policy: RetryPolicy = RetryPolicy(max_attempts=2, base_delay_s=0.25, max_delay_s=1.5, jitter_s=0.2)
    circuit_failure_threshold: int = 2
    circuit_cooldown_s: float = 20.0


class AiOrchestrator:
    """
    Orquestador async para IAs locales:
    - Solo soporta Ollama (IA local)
    - timeouts por proveedor
    - retries con backoff
    - circuit breaker por proveedor
    """

    def __init__(
        self,
        *,
        ollama_url: str = "http://localhost:11434/api/generate",
        ollama_model: str = "qwen2.5:3b",
        config: OrchestratorConfig = OrchestratorConfig(),
    ):
        self.ollama_url = ollama_url
        self.ollama_model = ollama_model
        self.cfg = config
        self.cb = CircuitBreaker(
            failure_threshold=self.cfg.circuit_failure_threshold,
            cooldown_s=self.cfg.circuit_cooldown_s,
        )

    def _provider_candidates(self, mode: str) -> list[str]:
        # Solo soporta ollama
        return ["ollama"]

    async def ask(self, prompt: str, history: list[dict] | None = None, *, mode: str = "auto") -> AiResponse | None:
        req = AiRequest(prompt=prompt, history=history or [])
        candidates = self._provider_candidates(mode)

        # Filtra por circuit breaker
        viable: list[str] = []
        for p in candidates:
            if not self.cb.allow(p):
                continue
            viable.append(p)

        if not viable:
            return None

        async def _call(provider: str) -> AiResponse | None:
            async def _attempt() -> AiResponse | None:
                if provider == "ollama":
                    return await call_ollama(
                        req,
                        url=self.ollama_url,
                        model=self.ollama_model,
                        timeout_s=self.cfg.ollama_timeout_s,
                    )
                return None

            def _retriable(e: Exception) -> bool:
                msg = str(e).lower()
                return any(k in msg for k in ["timeout", "tempor", "rate", "429", "overload", "connection"])

            t0 = time.monotonic()
            try:
                resp = await with_retry(_attempt, is_retriable=_retriable, policy=self.cfg.retry_policy, name=provider)
                if resp and resp.text:
                    self.cb.on_success(provider)
                    return resp
                # Si no hay texto, cuenta como fallo leve
                self.cb.on_failure(provider)
                return None
            except Exception as e:
                self.cb.on_failure(provider)
                ms = int((time.monotonic() - t0) * 1000)
                log.warning("Proveedor %s falló en %dms: %s", provider, ms, e)
                return None

        # First model wins: devolvemos el primer resultado no-None
        tasks = {asyncio.create_task(_call(p)): p for p in viable}
        try:
            while tasks:
                done, _pending = await asyncio.wait(tasks.keys(), return_when=asyncio.FIRST_COMPLETED)
                for t in done:
                    provider = tasks.pop(t, "unknown")
                    try:
                        res = t.result()
                    except Exception as e:
                        log.warning("Tarea %s explotó: %s", provider, e)
                        res = None
                    if res and res.text:
                        # Cancelar el resto
                        for other in list(tasks.keys()):
                            other.cancel()
                        return res
            return None
        finally:
            for t in tasks.keys():
                t.cancel()

