from __future__ import annotations

import json
import os
from dataclasses import dataclass, field

from logger import log


def _default_path() -> str:
    home = os.path.expanduser("~")
    return os.path.join(home, ".jarvis_memory.json")


@dataclass
class MemoryState:
    # Preferencias del usuario (p.ej. "ia_preferida", "ciudad", etc.)
    prefs: dict[str, str] = field(default_factory=dict)
    # Macros: nombre -> lista de decisiones (acciones)
    macros: dict[str, list[dict]] = field(default_factory=dict)
    # Alias / comandos aprendidos: frase normalizada -> decision
    aliases: dict[str, dict] = field(default_factory=dict)


class MemoryStore:
    """
    Memoria real persistente (más allá de conversación):
    - preferencias
    - macros (ej: "modo trabajo")
    - alias creados por usuario
    """

    def __init__(self, path: str | None = None) -> None:
        self.path = path or _default_path()
        self.state = MemoryState()
        self.load()

    def load(self) -> None:
        if not os.path.exists(self.path):
            return
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                raw = json.load(f) or {}
            self.state = MemoryState(
                prefs=dict(raw.get("prefs", {}) or {}),
                macros=dict(raw.get("macros", {}) or {}),
                aliases=dict(raw.get("aliases", {}) or {}),
            )
        except Exception as e:
            log.warning("MemoryStore: no se pudo cargar memoria: %s", e)

    def save(self) -> None:
        try:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
        except Exception:
            pass
        try:
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "prefs": self.state.prefs,
                        "macros": self.state.macros,
                        "aliases": self.state.aliases,
                    },
                    f,
                    indent=2,
                    ensure_ascii=False,
                )
        except Exception as e:
            log.warning("MemoryStore: no se pudo guardar memoria: %s", e)

