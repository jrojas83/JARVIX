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


async def call_groq(req: AiRequest, *, api_key: str, timeout_s: float) -> AiResponse | None:
    if not api_key:
        return None

    def _run_sync() -> AiResponse | None:
        t0 = time.monotonic()
        try:
            from groq import Groq  # sync SDK

            client = Groq(api_key=api_key)
            msgs = _trim_history(req.history)
            msgs.append({"role": "user", "content": req.prompt})
            # Model list copied from existing logic
            models = ["llama-3.1-8b-instant", "gemma2-9b-it", "llama-3.3-70b-versatile"]
            for model in models:
                try:
                    resp = client.chat.completions.create(
                        model=model,
                        messages=msgs,
                        max_tokens=600,
                        temperature=0.7,
                    )
                    text = resp.choices[0].message.content.strip()
                    ms = int((time.monotonic() - t0) * 1000)
                    return AiResponse(provider="groq", text=text, latency_ms=ms)
                except Exception as e_inner:
                    err = str(e_inner).lower()
                    if any(k in err for k in ["decommissioned", "deprecated", "not found", "model_not_found"]):
                        log.warning("Groq: modelo '%s' no disponible, probando siguiente", model)
                        continue
                    raise
        except Exception as e:
            log.warning("Groq falló: %s", e)
            return None

    try:
        return await asyncio.wait_for(asyncio.to_thread(_run_sync), timeout=timeout_s)
    except Exception:
        return None


async def call_anthropic(req: AiRequest, *, api_key: str, model: str, timeout_s: float) -> AiResponse | None:
    if not api_key:
        return None

    def _run_sync() -> AiResponse | None:
        t0 = time.monotonic()
        try:
            import anthropic  # sync SDK

            client = anthropic.Anthropic(api_key=api_key)
            msgs = _trim_history(req.history)
            msgs.append({"role": "user", "content": req.prompt})
            resp = client.messages.create(model=model, max_tokens=600, messages=msgs)
            text = resp.content[0].text.strip()
            ms = int((time.monotonic() - t0) * 1000)
            return AiResponse(provider="anthropic", text=text, latency_ms=ms)
        except Exception as e:
            log.warning("Anthropic falló: %s", e)
            return None

    try:
        return await asyncio.wait_for(asyncio.to_thread(_run_sync), timeout=timeout_s)
    except Exception:
        return None


async def call_gemini(req: AiRequest, *, api_key: str, timeout_s: float) -> AiResponse | None:
    if not api_key:
        return None

    def _run_sync() -> AiResponse | None:
        t0 = time.monotonic()
        contexto = "\n".join(
            f"{'Usuario' if m['role']=='user' else 'Jarvis'}: {m['content']}"
            for m in req.history[-6:]
        )
        prompt = f"{contexto}\nUsuario: {req.prompt}" if contexto else req.prompt

        try:
            import google.genai as genai

            client = genai.Client(api_key=api_key)
            resp = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
            text = (resp.text or "").strip()
            ms = int((time.monotonic() - t0) * 1000)
            return AiResponse(provider="gemini", text=text, latency_ms=ms) if text else None
        except ImportError:
            pass
        except Exception as e:
            log.warning("Gemini (google.genai) falló: %s", e)
            return None

        try:
            import google.generativeai as genai_legacy  # type: ignore

            genai_legacy.configure(api_key=api_key)
            model = genai_legacy.GenerativeModel("gemini-1.5-flash")
            resp = model.generate_content(prompt)
            text = (resp.text or "").strip()
            ms = int((time.monotonic() - t0) * 1000)
            return AiResponse(provider="gemini", text=text, latency_ms=ms) if text else None
        except Exception as e:
            log.warning("Gemini (legacy) falló: %s", e)
            return None

    try:
        return await asyncio.wait_for(asyncio.to_thread(_run_sync), timeout=timeout_s)
    except Exception:
        return None


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

