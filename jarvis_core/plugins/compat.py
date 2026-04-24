from __future__ import annotations

from logger import log

from plugins import cargar_plugins, ejecutar_por_orden, resumen_plugins


class PluginCompat:
    """
    Compatibilidad con el sistema actual de plugins (carpeta `plugins/`).
    Esta capa permite que el core nuevo trate plugins como un "router" previo.
    """

    def __init__(self) -> None:
        self.loaded: list[str] = []

    def load(self) -> list[str]:
        self.loaded = cargar_plugins()
        return self.loaded

    def try_handle(self, raw_text: str) -> str | None:
        try:
            return ejecutar_por_orden(raw_text)
        except Exception as e:
            log.error("PluginCompat: error ejecutando plugins: %s", e, exc_info=True)
            return f"Error ejecutando plugins: {e}"

    def summary(self) -> str:
        return resumen_plugins()

