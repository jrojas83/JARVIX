from __future__ import annotations

import re
from datetime import datetime

from jarvis_core.intents.types import Intent
from intenciones import (
    PATRONES_HORA,
    PATRONES_FECHA,
    PATRONES_SISTEMA,
    PATRONES_SALIR,
    PATRONES_VOL_SUBIR,
    PATRONES_VOL_BAJAR,
    PATRONES_VOL_SILENCIO,
    PATRONES_VOL_MAXIMO,
    PATRONES_CLIMA,
    PATRONES_CLIMA_PRONOS,
    PATRONES_RECORDATORIO_LISTAR,
    PATRONES_RECORDATORIO_CANCELAR,
    PATRONES_NOTA_LEER,
    PATRONES_NOTA_BORRAR,
    PATRONES_IA_ESTADO,
    PATRONES_TOKENS,
    PATRONES_MODELOS_LIST,
    PATRONES_FUNCIONES_TODAS,
    PATRONES_FUNCIONES_GRUPOS,
)


def builtin_intents() -> list[Intent]:
    intents: list[Intent] = []

    intents.append(
        Intent(
            id="time.now",
            contains=tuple(PATRONES_HORA),
            handler=lambda _raw: {"accion": "hablar", "parametros": {"texto": f"Son las {datetime.now().strftime('%H:%M')}"}},
        )
    )
    intents.append(
        Intent(
            id="date.today",
            contains=tuple(PATRONES_FECHA),
            handler=lambda _raw: {"accion": "hablar", "parametros": {"texto": f"Hoy es {datetime.now().strftime('%A %d de %B de %Y')}"}},
        )
    )

    intents.append(Intent(id="system.info", contains=tuple(PATRONES_SISTEMA), handler=lambda _raw: {"accion": "sistema", "parametros": {}}))
    intents.append(Intent(id="app.exit", phrases=tuple(PATRONES_SALIR), handler=lambda _raw: {"accion": "salir", "parametros": {}}))

    intents.append(Intent(id="volume.up", contains=tuple(PATRONES_VOL_SUBIR), handler=lambda _raw: {"accion": "volumen", "parametros": {"accion": "subir"}}))
    intents.append(Intent(id="volume.down", contains=tuple(PATRONES_VOL_BAJAR), handler=lambda _raw: {"accion": "volumen", "parametros": {"accion": "bajar"}}))
    intents.append(Intent(id="volume.mute", contains=tuple(PATRONES_VOL_SILENCIO), handler=lambda _raw: {"accion": "volumen", "parametros": {"accion": "silenciar"}}))
    intents.append(Intent(id="volume.max", contains=tuple(PATRONES_VOL_MAXIMO), handler=lambda _raw: {"accion": "volumen", "parametros": {"accion": "maximo"}}))

    def _match_clima(text: str):
        if not any(p in text for p in PATRONES_CLIMA):
            return None
        operacion = "pronostico" if any(p in text for p in PATRONES_CLIMA_PRONOS) else "actual"
        ciudad = None
        for prefijo in ["clima en ", "tiempo en ", "temperatura en ", "cómo está el clima en ", "como esta el clima en "]:
            if prefijo in text:
                ciudad = text.split(prefijo, 1)[1].strip().rstrip("?¿.,")
                break
        return {"accion": "clima", "parametros": {"operacion": operacion, "ciudad": ciudad or ""}}

    intents.append(Intent(id="weather", match=_match_clima))

    intents.append(Intent(id="reminders.list", contains=tuple(PATRONES_RECORDATORIO_LISTAR), handler=lambda _raw: {"accion": "recordatorio", "parametros": {"operacion": "listar"}}))
    intents.append(Intent(id="reminders.cancel", contains=tuple(PATRONES_RECORDATORIO_CANCELAR), handler=lambda _raw: {"accion": "recordatorio", "parametros": {"operacion": "cancelar"}}))

    intents.append(Intent(id="notes.read", contains=tuple(PATRONES_NOTA_LEER), handler=lambda _raw: {"accion": "nota", "parametros": {"operacion": "leer"}}))
    intents.append(Intent(id="notes.delete_last", contains=tuple(PATRONES_NOTA_BORRAR), handler=lambda _raw: {"accion": "nota", "parametros": {"operacion": "borrar"}}))

    intents.append(Intent(id="ai.status", contains=tuple(PATRONES_IA_ESTADO), handler=lambda _raw: {"accion": "estado_ia", "parametros": {}}))
    intents.append(Intent(id="ai.tokens", contains=tuple(PATRONES_TOKENS), handler=lambda _raw: {"accion": "tokens", "parametros": {}}))
    intents.append(Intent(id="ollama.models", contains=tuple(PATRONES_MODELOS_LIST), handler=lambda _raw: {"accion": "modelo_ollama", "parametros": {"modelo": ""}}))

    intents.append(Intent(id="help.groups", contains=tuple(PATRONES_FUNCIONES_GRUPOS), handler=lambda _raw: {"accion": "funcionalidades", "parametros": {"tipo": "grupos"}}))
    intents.append(Intent(id="help.all", contains=tuple(PATRONES_FUNCIONES_TODAS), handler=lambda _raw: {"accion": "funcionalidades", "parametros": {"tipo": "total"}}))

    # Intent específico: "funcionalidades de X"
    def _match_help_group(text: str):
        m = re.search(r"(?:funcionalidades de|ingresar a|entrar a|qué hace|que hace)\s+([a-záéíóúñ\s]+)", text)
        if not m:
            return None
        return {"accion": "funcionalidades", "parametros": {"tipo": "grupo_especifico", "grupo": m.group(1).strip()}}

    intents.append(Intent(id="help.group", match=_match_help_group))

    # v8: comandos de memoria (macros y alias)
    def _match_macro_create(text: str):
        # "crea modo trabajo: abre firefox y abre codigo"
        if not (text.startswith("crea modo ") or text.startswith("crear modo ")):
            return None
        # delegamos la interpretación a Agent/IA o parser posterior; aquí solo señalamos intención
        return {"accion": "hablar", "parametros": {"texto": "Para crear modos/macro, usa: 'modo trabajo' (si ya existe) o edita tu memoria en ~/.jarvis_memory.json por ahora."}}

    intents.append(Intent(id="memory.macro.create", match=_match_macro_create))

    return intents

