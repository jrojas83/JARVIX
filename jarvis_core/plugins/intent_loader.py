from __future__ import annotations

import importlib
import os
from types import ModuleType

from logger import log

from jarvis_core.intents.registry import IntentRegistry
from jarvis_core.intents.types import Intent


class PluginIntentLoader:
    """
    v8: Plugins pueden declarar intents (sin tocar core).

    Formas soportadas dentro de `plugins/*.py`:
    - `INTENTS: list[Intent]`
    - `def register_intents(registry: IntentRegistry) -> None`
    """

    def __init__(self, plugins_dir: str | None = None) -> None:
        self.plugins_dir = plugins_dir or os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "plugins")

    def _iter_modules(self) -> list[ModuleType]:
        base_dir = os.path.abspath(os.path.join(self.plugins_dir))
        if not os.path.isdir(base_dir):
            return []

        modules: list[ModuleType] = []
        for filename in sorted(os.listdir(base_dir)):
            if not filename.endswith(".py"):
                continue
            if filename.startswith("_") or filename == "__init__.py":
                continue
            mod_name = filename[:-3]
            try:
                modules.append(importlib.import_module(f"plugins.{mod_name}"))
            except Exception as e:
                log.warning("PluginIntentLoader: no se pudo importar plugins.%s: %s", mod_name, e)
        return modules

    def register_into(self, registry: IntentRegistry) -> None:
        for m in self._iter_modules():
            try:
                if hasattr(m, "register_intents"):
                    m.register_intents(registry)  # type: ignore[attr-defined]
                if hasattr(m, "INTENTS"):
                    intents = getattr(m, "INTENTS")
                    if isinstance(intents, list):
                        for it in intents:
                            if isinstance(it, Intent):
                                registry.register(it)
            except Exception as e:
                log.warning("PluginIntentLoader: error registrando intents de %s: %s", getattr(m, "__name__", "?"), e)

