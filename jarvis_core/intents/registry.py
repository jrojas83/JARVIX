from __future__ import annotations

from dataclasses import dataclass

from jarvis_core.intents.normalize import normalize_text
from jarvis_core.intents.types import Decision, Intent


@dataclass
class MatchResult:
    decision: Decision
    intent_id: str
    score: int


class IntentRegistry:
    def __init__(self) -> None:
        self._intents: list[Intent] = []

    def register(self, intent: Intent) -> None:
        self._intents.append(intent)

    def register_many(self, intents: list[Intent]) -> None:
        self._intents.extend(intents)

    def match(self, raw_text: str) -> MatchResult | None:
        text = normalize_text(raw_text)
        best: MatchResult | None = None

        for it in self._intents:
            # Custom matcher tiene prioridad
            if it.match is not None:
                decision = it.match(text)
                if decision is not None:
                    return MatchResult(decision=decision, intent_id=it.id, score=1000)

            score = 0
            if it.phrases:
                for p in it.phrases:
                    if text == normalize_text(p):
                        score = max(score, 900)
            if it.contains:
                for c in it.contains:
                    if normalize_text(c) in text:
                        score = max(score, 600)

            if score and it.handler is not None:
                decision = it.handler(raw_text)
                candidate = MatchResult(decision=decision, intent_id=it.id, score=score)
                if best is None or candidate.score > best.score:
                    best = candidate

        return best

