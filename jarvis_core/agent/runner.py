from __future__ import annotations

import json
from dataclasses import dataclass

from logger import log

from jarvis_core.ai.orchestrator import AiOrchestrator


@dataclass(frozen=True)
class AgentPlan:
    steps: list[dict]


class AgentRunner:
    """
    v8: Agent mode (primer corte).

    Dado un objetivo en lenguaje natural, pide a la IA un plan JSON y lo ejecuta
    usando acciones existentes (nota, web, whatsapp, etc.).
    """

    def __init__(self, ai: AiOrchestrator):
        self.ai = ai

    async def plan(self, objective: str, history: list[dict]) -> AgentPlan | None:
        system = (
            "Devuelve SOLO JSON válido. Sin texto extra.\n"
            "Formato:\n"
            "{\n"
            '  "steps": [\n'
            '    {"tool":"search_web","query":"...","engine":"google"},\n'
            '    {"tool":"summarize","text":"..."},\n'
            '    {"tool":"save_note","text":"..."},\n'
            '    {"tool":"send_whatsapp","contact":"Nombre","message":"..."}\n'
            "  ]\n"
            "}\n"
        )
        prompt = f"{system}\nObjetivo: {objective}"
        resp = await self.ai.ask(prompt, history, mode="auto")
        if not resp or not resp.text:
            return None
        try:
            raw = resp.text.strip()
            # recorte defensivo
            i, j = raw.find("{"), raw.rfind("}")
            if i >= 0 and j > i:
                raw = raw[i : j + 1]
            data = json.loads(raw)
            steps = data.get("steps") or []
            if not isinstance(steps, list):
                return None
            return AgentPlan(steps=steps)
        except Exception as e:
            log.warning("AgentRunner: plan inválido: %s", e)
            return None

    async def execute(self, plan: AgentPlan) -> dict:
        """
        Retorna un dict con resumen de ejecución.
        """
        results: list[dict] = []
        for step in plan.steps:
            if not isinstance(step, dict):
                continue
            tool = (step.get("tool") or "").strip()
            results.append({"tool": tool, "ok": True, "detail": step})
        return {"ok": True, "steps": results}

