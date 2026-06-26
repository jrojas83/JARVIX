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

    # =========================================================================
    # MÓDULO 1: WORK MODE - Detector de modo trabajo
    # =========================================================================
    def _match_activar_modo_trabajo(text: str):
        patrones = ['activa modo trabajo', 'voy a programar', 'prepara el entorno', 
                    'modo dev', 'abre todo para trabajar', 'modo desarrollo']
        if any(p in text for p in patrones):
            from jarvis_core.work_mode import activar_modo_trabajo
            return {"accion": "hablar", "parametros": {"texto": activar_modo_trabajo()}}
        return None

    def _match_desactivar_modo_trabajo(text: str):
        patrones = ['desactiva modo trabajo', 'cierra el entorno', 'salir modo trabajo']
        if any(p in text for p in patrones):
            from jarvis_core.work_mode import desactivar_modo_trabajo
            return {"accion": "hablar", "parametros": {"texto": desactivar_modo_trabajo()}}
        return None

    def _match_estado_modo_trabajo(text: str):
        patrones = ['estado del modo trabajo', 'está activo el modo trabajo', 'modo trabajo estado']
        if any(p in text for p in patrones):
            from jarvis_core.work_mode import estado_modo
            return {"accion": "hablar", "parametros": {"texto": estado_modo()}}
        return None

    intents.append(Intent(id="work_mode.activar", match=_match_activar_modo_trabajo))
    intents.append(Intent(id="work_mode.desactivar", match=_match_desactivar_modo_trabajo))
    intents.append(Intent(id="work_mode.estado", match=_match_estado_modo_trabajo))

    # =========================================================================
    # MÓDULO 2: DICTATION - Dictado continuo
    # =========================================================================
    def _match_iniciar_dictado(text: str):
        patrones = ['modo dictado', 'iniciar dictado', 'activa dictado', 
                    'quiero dictarle', 'escribe lo que digo', 'empieza dictado']
        if any(p in text for p in patrones):
            from jarvis_core.dictation import iniciar_dictado
            return {"accion": "hablar", "parametros": {"texto": iniciar_dictado()}}
        return None

    def _match_detener_dictado(text: str):
        patrones = ['detener dictado', 'parar dictado', 'fin dictado', 
                    'deja de escribir', 'termina dictado']
        if any(p in text for p in patrones):
            from jarvis_core.dictation import detener_dictado
            return {"accion": "hablar", "parametros": {"texto": detener_dictado()}}
        return None

    def _match_estado_dictado(text: str):
        patrones = ['estado dictado', 'dictado activo', 'cómo está el dictado']
        if any(p in text for p in patrones):
            from jarvis_core.dictation import estado_dictado
            return {"accion": "hablar", "parametros": {"texto": estado_dictado()}}
        return None

    intents.append(Intent(id="dictation.iniciar", match=_match_iniciar_dictado))
    intents.append(Intent(id="dictation.detener", match=_match_detener_dictado))
    intents.append(Intent(id="dictation.estado", match=_match_estado_dictado))

    # =========================================================================
    # MÓDULO 3: VOICE NOTES - Notas por voz con etiquetas semánticas
    # =========================================================================
    def _match_buscar_notas(text: str):
        patrones = ['busca en mis notas', 'qué notas tengo de', 'busca notas de', 
                    'notas sobre ', 'buscar nota']
        if any(p in text for p in patrones):
            # Extraer término de búsqueda
            termino = text
            for p in patrones:
                if p in text:
                    termino = text.split(p, 1)[-1].strip() if p in text else termino
                    break
            from jarvis_core.voice_notes import buscar_notas
            return {"accion": "hablar", "parametros": {"texto": buscar_notas(termino)}}
        return None

    def _match_listar_notas(text: str):
        patrones = ['mis notas recientes', 'últimas notas', 'qué anoté hoy', 
                    'lista mis notas', 'ver notas']
        if any(p in text for p in patrones):
            from jarvis_core.voice_notes import listar_notas_recientes
            return {"accion": "hablar", "parametros": {"texto": listar_notas_recientes()}}
        return None

    intents.append(Intent(id="voice_notes.buscar", match=_match_buscar_notas))
    intents.append(Intent(id="voice_notes.listar", match=_match_listar_notas))

    # =========================================================================
    # MÓDULO 4: HABIT MONITOR - Monitor de hábitos
    # =========================================================================
    def _match_registrar_agua(text: str):
        patrones = ['tomé agua', 'bebí agua', 'ya tomé agua', 'registré agua']
        if any(p in text for p in patrones):
            from jarvis_core.habit_monitor import registrar_habito
            exito = registrar_habito('agua')
            return {"accion": "hablar", "parametros": {"texto": "Agua registrada" if exito else "Error al registrar"}}
        return None

    def _match_registrar_descanso(text: str):
        patrones = ['hice pausa', 'me levanté', 'hice descanso', 'tomé un descanso']
        if any(p in text for p in patrones):
            from jarvis_core.habit_monitor import registrar_habito
            exito = registrar_habito('descanso')
            return {"accion": "hablar", "parametros": {"texto": "Descanso registrado" if exito else "Error al registrar"}}
        return None

    def _match_listar_habitos(text: str):
        patrones = ['mis hábitos', 'cómo van mis hábitos', 'estado de hábitos', 'ver hábitos']
        if any(p in text for p in patrones):
            from jarvis_core.habit_monitor import listar_reglas
            return {"accion": "hablar", "parametros": {"texto": listar_reglas()}}
        return None

    intents.append(Intent(id="habit.agua", match=_match_registrar_agua))
    intents.append(Intent(id="habit.descanso", match=_match_registrar_descanso))
    intents.append(Intent(id="habit.listar", match=_match_listar_habitos))

    # =========================================================================
    # MÓDULO 5: FILE AGENT - Organizador de archivos agente
    # =========================================================================
    def _match_organizar_archivos(text: str):
        patrones = ['organiza mis descargas', 'organiza la carpeta', 'ordena mis archivos', 
                    'limpia la carpeta', 'organiza las fotos', 'organiza documentos']
        if any(p in text for p in patrones):
            from jarvis_core.file_agent import organizar
            return {"accion": "hablar", "parametros": {"texto": organizar(text)}}
        return None

    intents.append(Intent(id="file_agent.organizar", match=_match_organizar_archivos))

    # =========================================================================
    # MÓDULO 6: FLASHCARDS - Flashcards con algoritmo SM-2
    # =========================================================================
    def _match_sesion_repaso(text: str):
        patrones = ['repasar flashcards', 'sesión de repaso', 'repasar lo que aprendí', 
                    'mis flashcards de hoy', 'repaso tarjetas']
        if any(p in text for p in patrones):
            from jarvis_core.flashcards import sesion_repaso
            return {"accion": "hablar", "parametros": {"texto": sesion_repaso()}}
        return None

    def _match_estadisticas_flashcards(text: str):
        patrones = ['cuántas flashcards tengo', 'estadísticas de flashcards', 
                    'estado flashcards', 'ver flashcards']
        if any(p in text for p in patrones):
            from jarvis_core.flashcards import estadisticas_flashcards
            return {"accion": "hablar", "parametros": {"texto": estadisticas_flashcards()}}
        return None

    intents.append(Intent(id="flashcards.repaso", match=_match_sesion_repaso))
    intents.append(Intent(id="flashcards.estadisticas", match=_match_estadisticas_flashcards))

    return intents

