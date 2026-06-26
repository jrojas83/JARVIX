from __future__ import annotations

import re
from datetime import datetime

from jarvis_core.intents.types import Intent
from jarvis_core.intents.patterns import (
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
    PATRONES_RECORDATORIO_CREAR,
    PATRONES_RECORDATORIO_LISTAR,
    PATRONES_RECORDATORIO_CANCELAR,
    PATRONES_NOTA_AGREGAR,
    PATRONES_NOTA_LEER,
    PATRONES_NOTA_BORRAR,
    PATRONES_NOTA_BUSCAR,
    PATRONES_WIFI,
    PATRONES_WIFI_ACTIVAR,
    PATRONES_WIFI_DESACT,
    PATRONES_WIFI_LISTAR,
    PATRONES_BLUETOOTH,
    PATRONES_BT_ACTIVAR,
    PATRONES_BT_DESACT,
    PATRONES_BT_ABRIR,
    PATRONES_SUSPENDER,
    PATRONES_APAGAR,
    PATRONES_REINICIAR,
    PATRONES_BUSCAR_GOOGLE,
    PATRONES_BUSCAR_YOUTUBE,
    PATRONES_BUSCAR_WIKI,
    PATRONES_IA_ESTADO,
    PATRONES_TOKENS,
    PATRONES_CAMBIAR_IA,
    PATRONES_MODELO_OLL,
    PATRONES_MODELOS_LIST,
    PATRONES_FUNCIONES_TODAS,
    PATRONES_FUNCIONES_GRUPOS,
    PATRONES_WA_ABRIR,
    PATRONES_WA_ESTADO,
    PATRONES_WA_CERRAR,
)


def builtin_intents() -> list[Intent]:
    intents: list[Intent] = []

    # ════════════════════════════════════════════════════════════════
    # HORA Y FECHA
    # ════════════════════════════════════════════════════════════════
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

    # ════════════════════════════════════════════════════════════════
    # SISTEMA Y CONTROL
    # ════════════════════════════════════════════════════════════════
    intents.append(Intent(id="system.info", contains=tuple(PATRONES_SISTEMA), handler=lambda _raw: {"accion": "sistema", "parametros": {}}))
    intents.append(Intent(id="app.exit", phrases=tuple(PATRONES_SALIR), handler=lambda _raw: {"accion": "salir", "parametros": {}}))

    # ════════════════════════════════════════════════════════════════
    # VOLUMEN
    # ════════════════════════════════════════════════════════════════
    intents.append(Intent(id="volume.up", contains=tuple(PATRONES_VOL_SUBIR), handler=lambda _raw: {"accion": "volumen", "parametros": {"accion": "subir"}}))
    intents.append(Intent(id="volume.down", contains=tuple(PATRONES_VOL_BAJAR), handler=lambda _raw: {"accion": "volumen", "parametros": {"accion": "bajar"}}))
    intents.append(Intent(id="volume.mute", contains=tuple(PATRONES_VOL_SILENCIO), handler=lambda _raw: {"accion": "volumen", "parametros": {"accion": "silenciar"}}))
    intents.append(Intent(id="volume.max", contains=tuple(PATRONES_VOL_MAXIMO), handler=lambda _raw: {"accion": "volumen", "parametros": {"accion": "maximo"}}))

    # ════════════════════════════════════════════════════════════════
    # CLIMA
    # ════════════════════════════════════════════════════════════════
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

    # ════════════════════════════════════════════════════════════════
    # WHATSAPP
    # ════════════════════════════════════════════════════════════════
    def _match_whatsapp_enviar(text: str):
        m = re.search(r"(?:manda|envía|envia|enviar|mándame|mandame)\s+(?:whatsapp|mensaje|wa)\s+a\s+([^:]+):\s*(.+)", text)
        if not m:
            return None
        return {
            "accion": "whatsapp",
            "parametros": {
                "operacion": "enviar",
                "contacto": m.group(1).strip().title(),
                "mensaje": m.group(2).strip(),
            },
        }

    intents.append(Intent(id="whatsapp.send", match=_match_whatsapp_enviar))

    def _match_whatsapp_leer(text: str):
        m = re.search(r"(?:lee|leer|muestra|ver)\s+(?:mis\s+)?mensajes\s+de\s+(.+)", text)
        if not m:
            return None
        return {"accion": "whatsapp", "parametros": {"operacion": "leer", "contacto": m.group(1).strip().title()}}

    intents.append(Intent(id="whatsapp.read", match=_match_whatsapp_leer))

    def _match_whatsapp_recordatorio(text: str):
        if "whatsapp" not in text or not any(p in text for p in ["recuérdame", "recuerdame", "recordatorio"]):
            return None
        m = re.search(r"en\s+([\d\w\s]+?)\s+(?:a|para)\s+([^\s:]+)(?::\s*(.+))?", text)
        if not m:
            return None
        return {
            "accion": "whatsapp",
            "parametros": {
                "operacion": "recordatorio",
                "contacto": m.group(2).strip().title(),
                "mensaje": (m.group(3) or "recordatorio de Jarvis").strip(),
                "tiempo": m.group(1).strip(),
            },
        }

    intents.append(Intent(id="whatsapp.reminder", match=_match_whatsapp_recordatorio))
    intents.append(Intent(id="whatsapp.status", contains=tuple(PATRONES_WA_ESTADO), handler=lambda _raw: {"accion": "whatsapp", "parametros": {"operacion": "estado"}}))
    intents.append(Intent(id="whatsapp.close", contains=tuple(PATRONES_WA_CERRAR), handler=lambda _raw: {"accion": "whatsapp", "parametros": {"operacion": "cerrar"}}))

    def _match_whatsapp_abrir(text: str):
        if "whatsapp" not in text or not any(p in text for p in ["abre ", "abrir ", "ejecuta "]):
            return None
        return {"accion": "whatsapp", "parametros": {"operacion": "abrir"}}

    intents.append(Intent(id="whatsapp.open", match=_match_whatsapp_abrir))

    # ════════════════════════════════════════════════════════════════
    # FUNCIONALIDADES / AYUDA
    # ════════════════════════════════════════════════════════════════
    intents.append(Intent(id="help.all", contains=tuple(PATRONES_FUNCIONES_TODAS), handler=lambda _raw: {"accion": "funcionalidades", "parametros": {"tipo": "total"}}))
    intents.append(Intent(id="help.groups", contains=tuple(PATRONES_FUNCIONES_GRUPOS), handler=lambda _raw: {"accion": "funcionalidades", "parametros": {"tipo": "grupos"}}))

    def _match_help_group(text: str):
        m = re.search(r"(?:funcionalidades de|ingresar a|entrar a|qué hace|que hace)\s+([a-záéíóúñ\s]+)", text)
        if not m:
            return None
        return {"accion": "funcionalidades", "parametros": {"tipo": "grupo_especifico", "grupo": m.group(1).strip()}}

    intents.append(Intent(id="help.group", match=_match_help_group))

    # ════════════════════════════════════════════════════════════════
    # RECORDATORIOS
    # ════════════════════════════════════════════════════════════════
    def _match_recordatorio_crear(text: str):
        if not any(p in text for p in PATRONES_RECORDATORIO_CREAR):
            return None
        patrones_tiempo = [
            r"en\s+(\d+\s*hora[s]?\s+y\s+\d+\s*minuto[s]?)",
            r"en\s+(\d+\s*hora[s]?)",
            r"en\s+(\d+\s*minuto[s]?)",
            r"en\s+(\d+\s*segundo[s]?)",
            r"en\s+(media\s*hora)",
            r"en\s+(cuarto\s*de\s*hora)",
        ]
        tiempo_enc = None
        mensaje_raw = ""
        for pat in patrones_tiempo:
            m = re.search(pat, text)
            if m:
                tiempo_enc = m.group(1)
                mensaje_raw = text[m.end():].strip()
                for pref in ["que", "de", "para", ":"]:
                    if mensaje_raw.startswith(pref):
                        mensaje_raw = mensaje_raw[len(pref):].strip()
                break
        if tiempo_enc and mensaje_raw:
            return {"accion": "recordatorio", "parametros": {"operacion": "crear", "mensaje": mensaje_raw, "tiempo": tiempo_enc}}
        return None

    intents.append(Intent(id="reminders.create", match=_match_recordatorio_crear))
    intents.append(Intent(id="reminders.list", contains=tuple(PATRONES_RECORDATORIO_LISTAR), handler=lambda _raw: {"accion": "recordatorio", "parametros": {"operacion": "listar"}}))
    intents.append(Intent(id="reminders.cancel", contains=tuple(PATRONES_RECORDATORIO_CANCELAR), handler=lambda _raw: {"accion": "recordatorio", "parametros": {"operacion": "cancelar"}}))

    # ════════════════════════════════════════════════════════════════
    # NOTAS
    # ════════════════════════════════════════════════════════════════
    def _match_nota_agregar(text: str):
        for prefijo in PATRONES_NOTA_AGREGAR:
            if prefijo in text:
                texto_nota = text.split(prefijo, 1)[1].strip()
                if texto_nota:
                    return {"accion": "nota", "parametros": {"operacion": "agregar", "texto": texto_nota}}
        return None

    intents.append(Intent(id="notes.add", match=_match_nota_agregar))
    intents.append(Intent(id="notes.read", contains=tuple(PATRONES_NOTA_LEER), handler=lambda _raw: {"accion": "nota", "parametros": {"operacion": "leer"}}))
    intents.append(Intent(id="notes.delete_last", contains=tuple(PATRONES_NOTA_BORRAR), handler=lambda _raw: {"accion": "nota", "parametros": {"operacion": "borrar"}}))

    def _match_nota_buscar(text: str):
        for pref in PATRONES_NOTA_BUSCAR:
            if pref in text:
                termino = text.replace(pref, "").strip()
                if termino:
                    return {"accion": "nota", "parametros": {"operacion": "buscar", "termino": termino}}
        return None

    intents.append(Intent(id="notes.search", match=_match_nota_buscar))

    # ════════════════════════════════════════════════════════════════
    # BÚSQUEDA WEB
    # ════════════════════════════════════════════════════════════════
    def _match_buscar_web(text: str):
        for patrones, motor in [
            (PATRONES_BUSCAR_GOOGLE, "google"),
            (PATRONES_BUSCAR_YOUTUBE, "youtube"),
            (PATRONES_BUSCAR_WIKI, "wikipedia"),
        ]:
            for p in patrones:
                if p in text:
                    consulta = text
                    for pat in patrones:
                        consulta = consulta.replace(pat, "").strip()
                    return {"accion": "buscar_web", "parametros": {"consulta": consulta, "motor": motor}}
        return None

    intents.append(Intent(id="web.search", match=_match_buscar_web))

    # ════════════════════════════════════════════════════════════════
    # IA Y MODELOS
    # ════════════════════════════════════════════════════════════════
    intents.append(Intent(id="ai.status", contains=tuple(PATRONES_IA_ESTADO), handler=lambda _raw: {"accion": "estado_ia", "parametros": {}}))
    intents.append(Intent(id="ai.tokens", contains=tuple(PATRONES_TOKENS), handler=lambda _raw: {"accion": "tokens", "parametros": {}}))

    def _match_cambiar_ia(text: str):
        for frase in PATRONES_CAMBIAR_IA:
            if frase in text:
                # Evitar falsos positivos con "activa " solo
                if frase.strip() == "activa":
                    continue
                ia_nombre = text.split(frase, 1)[1].strip().split()[0]
                return {"accion": "cambiar_ia", "parametros": {"ia": ia_nombre}}
        return None

    intents.append(Intent(id="ai.change", match=_match_cambiar_ia))

    def _match_modelo_oll(text: str):
        for frase in PATRONES_MODELO_OLL:
            if frase in text:
                modelo = text.split(frase, 1)[1].strip()
                return {"accion": "modelo_ollama", "parametros": {"modelo": modelo}}
        return None

    intents.append(Intent(id="ollama.model", match=_match_modelo_oll))
    intents.append(Intent(id="ollama.models", contains=tuple(PATRONES_MODELOS_LIST), handler=lambda _raw: {"accion": "modelo_ollama", "parametros": {"modelo": ""}}))

    # ════════════════════════════════════════════════════════════════
    # WIFI
    # ════════════════════════════════════════════════════════════════
    def _match_wifi(text: str):
        if not any(p in text for p in PATRONES_WIFI):
            return None
        if any(p in text for p in PATRONES_WIFI_ACTIVAR):
            return {"accion": "wifi", "parametros": {"accion": "activar"}}
        if any(p in text for p in PATRONES_WIFI_DESACT):
            return {"accion": "wifi", "parametros": {"accion": "desactivar"}}
        if any(p in text for p in PATRONES_WIFI_LISTAR):
            return {"accion": "wifi", "parametros": {"accion": "listar"}}
        m_wifi = re.search(r'conect(?:a|ame|arme)\s+(?:al?\s+wifi\s+)?(?:a\s+)?["\']?([^\s"\']+)["\']?', text)
        if m_wifi:
            return {"accion": "wifi", "parametros": {"accion": f"conectar:{m_wifi.group(1).strip()}"}}
        return {"accion": "wifi", "parametros": {"accion": "estado"}}

    intents.append(Intent(id="wifi", match=_match_wifi))

    # ════════════════════════════════════════════════════════════════
    # BLUETOOTH
    # ════════════════════════════════════════════════════════════════
    def _match_bluetooth(text: str):
        if not any(p in text for p in PATRONES_BLUETOOTH):
            return None
        if any(p in text for p in PATRONES_BT_ACTIVAR):
            return {"accion": "bluetooth", "parametros": {"accion": "activar"}}
        if any(p in text for p in PATRONES_BT_DESACT):
            return {"accion": "bluetooth", "parametros": {"accion": "desactivar"}}
        if any(p in text for p in PATRONES_BT_ABRIR):
            return {"accion": "bluetooth", "parametros": {"accion": "abrir"}}
        return {"accion": "bluetooth", "parametros": {"accion": "estado"}}

    intents.append(Intent(id="bluetooth", match=_match_bluetooth))

    # ════════════════════════════════════════════════════════════════
    # ENERGÍA
    # ════════════════════════════════════════════════════════════════
    intents.append(Intent(id="energy.suspend", contains=tuple(PATRONES_SUSPENDER), handler=lambda _raw: {"accion": "energia", "parametros": {"accion": "suspender"}}))
    intents.append(Intent(id="energy.off", contains=tuple(PATRONES_APAGAR), handler=lambda _raw: {"accion": "energia", "parametros": {"accion": "apagar"}}))
    intents.append(Intent(id="energy.restart", contains=tuple(PATRONES_REINICIAR), handler=lambda _raw: {"accion": "energia", "parametros": {"accion": "reiniciar"}}))

    # ════════════════════════════════════════════════════════════════
    # MEMORIA (MACROS Y ALIAS)
    # ════════════════════════════════════════════════════════════════
    def _match_macro_create(text: str):
        if not (text.startswith("crea modo ") or text.startswith("crear modo ")):
            return None
        return {"accion": "hablar", "parametros": {"texto": "Para crear modos/macro, usa: 'modo trabajo' (si ya existe) o edita tu memoria en ~/.jarvis_memory.json por ahora."}}

    intents.append(Intent(id="memory.macro.create", match=_match_macro_create))

    return intents

