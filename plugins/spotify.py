"""
Plugin v8 (ejemplo): intents + ejecución.

Este archivo es un "módulo comando" que:
- expone intents (sin tocar el core)
- puede seguir exponiendo PATRONES/ejecutar() para compat v7
"""

from __future__ import annotations

from jarvis_core.intents.types import Intent


NOMBRE = "spotify"
DESCRIPCION = "Abre el reproductor/música"

# Compat v7: activación por contains (simple)
PATRONES = [
    "abre spotify",
    "spotify",
    "pon musica",
    "quiero escuchar algo",
    "abre mi reproductor",
]


def ejecutar(orden: str, params: dict) -> str:
    # En Linux real, esto debería abrir Spotify (si existe) o el navegador.
    # Por compat, devolvemos texto; el usuario puede reemplazar con su lógica.
    return "Abriendo tu reproductor de música."


def register_intents(registry) -> None:
    # Intent principal de "música" (sin comandos rígidos)
    registry.register(
        Intent(
            id="music.open_player",
            contains=(
                "pon musica",
                "quiero escuchar algo",
                "abre mi reproductor",
                "poner musica",
                "musica",
                "spotify",
            ),
            handler=lambda _raw: {"accion": "plugin", "parametros": {"nombre": "spotify"}},
        )
    )


# Alternativa declarativa: lista INTENTS
INTENTS = [
    Intent(
        id="music.open_spotify",
        contains=("abre spotify", "abrir spotify"),
        handler=lambda _raw: {"accion": "plugin", "parametros": {"nombre": "spotify"}},
    )
]

