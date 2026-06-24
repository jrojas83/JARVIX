from __future__ import annotations

import re
import sys
from datetime import datetime

from logger import log
from config import APPS_PERMITIDAS, CARPETAS, ARCHIVOS_CONOCIDOS, URLS_WEB
from acciones import (
    abrir_app,
    abrir_carpeta_conocida,
    abrir_archivo_conocido,
    buscar_archivo_en_carpeta,
    listar_archivos_carpeta,
    abrir_url,
    buscar_en_web,
    obtener_info_sistema,
    controlar_volumen,
    control_energia,
    accion_recordatorio,
    accion_nota,
    accion_clima,
    accion_whatsapp,
    accion_codigo,
    controlar_wifi,
    controlar_bluetooth,
    cambiar_modelo_ollama,
    accion_funcionalidades,
)
from ia_online import (
    es_peticion_de_codigo,
    detectar_lenguaje,
    set_ia,
    estado_ias,
    reporte_tokens,
)
from voz import hablar
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
)


def procesar_sin_ia(orden: str) -> dict | None:
    """
    Compatibilidad: port directo de jarvis.py para comandos frecuentes.
    Se mantendrá mientras migramos a intents + sinónimos.
    """
    o = orden.lower().strip()

    m_enviar = re.search(
        r"(?:manda|envía|envia|enviar|mándame|mandame)\s+(?:whatsapp|mensaje|wa)\s+a\s+([^:]+):\s*(.+)",
        o,
    )
    if m_enviar:
        return {
            "accion": "whatsapp",
            "parametros": {
                "operacion": "enviar",
                "contacto": m_enviar.group(1).strip().title(),
                "mensaje": m_enviar.group(2).strip(),
            },
        }

    m_leer = re.search(r"(?:lee|leer|muestra|ver)\s+(?:mis\s+)?mensajes\s+de\s+(.+)", o)
    if m_leer:
        return {"accion": "whatsapp", "parametros": {"operacion": "leer", "contacto": m_leer.group(1).strip().title()}}

    if "whatsapp" in o and any(p in o for p in ["recuérdame", "recuerdame", "recordatorio"]):
        m_wa = re.search(r"en\s+([\d\w\s]+?)\s+(?:a|para)\s+([^\s:]+)(?::\s*(.+))?", o)
        if m_wa:
            return {
                "accion": "whatsapp",
                "parametros": {
                    "operacion": "recordatorio",
                    "contacto": m_wa.group(2).strip().title(),
                    "mensaje": (m_wa.group(3) or "recordatorio de Jarvis").strip(),
                    "tiempo": m_wa.group(1).strip(),
                },
            }

    if any(p in o for p in ["estado whatsapp", "whatsapp conectado"]):
        return {"accion": "whatsapp", "parametros": {"operacion": "estado"}}
    if any(p in o for p in ["cierra whatsapp", "cerrar whatsapp"]):
        return {"accion": "whatsapp", "parametros": {"operacion": "cerrar"}}
    if "whatsapp" in o and any(p in o for p in ["abre ", "abrir ", "ejecuta "]):
        return {"accion": "whatsapp", "parametros": {"operacion": "abrir"}}

    if any(p in o for p in PATRONES_FUNCIONES_TODAS):
        return {"accion": "funcionalidades", "parametros": {"tipo": "total"}}
    if any(p in o for p in PATRONES_FUNCIONES_GRUPOS):
        return {"accion": "funcionalidades", "parametros": {"tipo": "grupos"}}
    m_grupo = re.search(r"(?:funcionalidades de|ingresar a|entrar a|qué hace|que hace)\s+([a-záéíóúñ\s]+)", o)
    if m_grupo:
        return {"accion": "funcionalidades", "parametros": {"tipo": "grupo_especifico", "grupo": m_grupo.group(1).strip()}}

    for app_key in APPS_PERMITIDAS:
        if app_key == "whatsapp":
            continue
        if app_key in o and any(p in o for p in ["abre", "abrir", "ejecuta"]):
            return {"accion": "abrir_app", "parametros": {"app": app_key}}

    for carpeta_key in CARPETAS:
        if carpeta_key in o and any(p in o for p in ["abre", "muestra", "carpeta", "abrir"]):
            return {"accion": "abrir_carpeta", "parametros": {"carpeta": carpeta_key}}

    if any(p in o for p in ["qué hay en", "lista", "mostrar archivos"]):
        for carpeta_key in CARPETAS:
            if carpeta_key in o:
                return {"accion": "listar_archivos", "parametros": {"carpeta": carpeta_key}}

    for patrones, motor in [
        (PATRONES_BUSCAR_GOOGLE, "google"),
        (PATRONES_BUSCAR_YOUTUBE, "youtube"),
        (PATRONES_BUSCAR_WIKI, "wikipedia"),
    ]:
        for p in patrones:
            if p in o:
                consulta = o
                for pat in patrones:
                    consulta = consulta.replace(pat, "").strip()
                return {"accion": "buscar_web", "parametros": {"consulta": consulta, "motor": motor}}

    if any(p in o for p in PATRONES_VOL_SUBIR):
        return {"accion": "volumen", "parametros": {"accion": "subir"}}
    if any(p in o for p in PATRONES_VOL_BAJAR):
        return {"accion": "volumen", "parametros": {"accion": "bajar"}}
    if any(p in o for p in PATRONES_VOL_SILENCIO):
        return {"accion": "volumen", "parametros": {"accion": "silenciar"}}
    if any(p in o for p in PATRONES_VOL_MAXIMO):
        return {"accion": "volumen", "parametros": {"accion": "maximo"}}

    if any(p in o for p in PATRONES_HORA):
        hora = datetime.now().strftime("%H:%M")
        return {"accion": "hablar", "parametros": {"texto": f"Son las {hora}"}}
    if any(p in o for p in PATRONES_FECHA):
        fecha = datetime.now().strftime("%A %d de %B de %Y")
        return {"accion": "hablar", "parametros": {"texto": f"Hoy es {fecha}"}}
    if any(p in o for p in PATRONES_SISTEMA):
        return {"accion": "sistema", "parametros": {}}
    if any(o == p for p in PATRONES_SALIR):
        return {"accion": "salir", "parametros": {}}

    if any(p in o for p in PATRONES_CLIMA):
        operacion = "pronostico" if any(p in o for p in PATRONES_CLIMA_PRONOS) else "actual"
        ciudad = None
        for prefijo in ["clima en ", "tiempo en ", "temperatura en ", "cómo está el clima en ", "como esta el clima en "]:
            if prefijo in o:
                ciudad = o.split(prefijo, 1)[1].strip().rstrip("?¿.,")
                break
        return {"accion": "clima", "parametros": {"operacion": operacion, "ciudad": ciudad or ""}}

    if es_peticion_de_codigo(o):
        lenguaje = detectar_lenguaje(o)
        return {"accion": "codigo", "parametros": {"peticion": orden, "lenguaje": lenguaje or ""}}

    if any(p in o for p in PATRONES_CAMBIAR_IA):
        for frase in PATRONES_CAMBIAR_IA:
            if frase in o:
                ia_nombre = o.split(frase, 1)[1].strip().split()[0]
                return {"accion": "cambiar_ia", "parametros": {"ia": ia_nombre}}

    if any(p in o for p in PATRONES_IA_ESTADO):
        return {"accion": "estado_ia", "parametros": {}}
    if any(p in o for p in PATRONES_TOKENS):
        return {"accion": "tokens", "parametros": {}}

    for frase in PATRONES_MODELO_OLL:
        if frase in o:
            modelo = o.split(frase, 1)[1].strip()
            return {"accion": "modelo_ollama", "parametros": {"modelo": modelo}}
    if any(p in o for p in PATRONES_MODELOS_LIST):
        return {"accion": "modelo_ollama", "parametros": {"modelo": ""}}

    if any(p in o for p in PATRONES_WIFI):
        if any(p in o for p in PATRONES_WIFI_ACTIVAR):
            return {"accion": "wifi", "parametros": {"accion": "activar"}}
        if any(p in o for p in PATRONES_WIFI_DESACT):
            return {"accion": "wifi", "parametros": {"accion": "desactivar"}}
        if any(p in o for p in PATRONES_WIFI_LISTAR):
            return {"accion": "wifi", "parametros": {"accion": "listar"}}
        m_wifi = re.search(r'conect(?:a|ame|arme)\s+(?:al?\s+wifi\s+)?(?:a\s+)?["\']?([^\s"\']+)["\']?', o)
        if m_wifi:
            return {"accion": "wifi", "parametros": {"accion": f"conectar:{m_wifi.group(1).strip()}"}}
        return {"accion": "wifi", "parametros": {"accion": "estado"}}

    if any(p in o for p in PATRONES_SUSPENDER):
        return {"accion": "energia", "parametros": {"accion": "suspender"}}
    if any(p in o for p in PATRONES_APAGAR):
        return {"accion": "energia", "parametros": {"accion": "apagar"}}
    if any(p in o for p in PATRONES_REINICIAR):
        return {"accion": "energia", "parametros": {"accion": "reiniciar"}}

    if any(p in o for p in PATRONES_BLUETOOTH):
        if any(p in o for p in PATRONES_BT_ACTIVAR):
            return {"accion": "bluetooth", "parametros": {"accion": "activar"}}
        if any(p in o for p in PATRONES_BT_DESACT):
            return {"accion": "bluetooth", "parametros": {"accion": "desactivar"}}
        if any(p in o for p in PATRONES_BT_ABRIR):
            return {"accion": "bluetooth", "parametros": {"accion": "abrir"}}
        return {"accion": "bluetooth", "parametros": {"accion": "estado"}}

    if any(p in o for p in PATRONES_RECORDATORIO_CREAR):
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
            m = re.search(pat, o)
            if m:
                tiempo_enc = m.group(1)
                mensaje_raw = o[m.end() :].strip()
                for pref in ["que", "de", "para", ":"]:
                    if mensaje_raw.startswith(pref):
                        mensaje_raw = mensaje_raw[len(pref) :].strip()
                break
        if tiempo_enc and mensaje_raw:
            return {"accion": "recordatorio", "parametros": {"operacion": "crear", "mensaje": mensaje_raw, "tiempo": tiempo_enc}}

    if any(p in o for p in PATRONES_RECORDATORIO_LISTAR):
        return {"accion": "recordatorio", "parametros": {"operacion": "listar"}}
    if any(p in o for p in PATRONES_RECORDATORIO_CANCELAR):
        return {"accion": "recordatorio", "parametros": {"operacion": "cancelar"}}

    if any(p in o for p in PATRONES_NOTA_AGREGAR):
        for prefijo in PATRONES_NOTA_AGREGAR:
            if prefijo in o:
                texto_nota = o.split(prefijo, 1)[1].strip()
                if texto_nota:
                    return {"accion": "nota", "parametros": {"operacion": "agregar", "texto": texto_nota}}
    if any(p in o for p in PATRONES_NOTA_LEER):
        return {"accion": "nota", "parametros": {"operacion": "leer"}}
    if any(p in o for p in PATRONES_NOTA_BORRAR):
        return {"accion": "nota", "parametros": {"operacion": "borrar"}}
    if any(p in o for p in PATRONES_NOTA_BUSCAR):
        for pref in PATRONES_NOTA_BUSCAR:
            if pref in o:
                termino = o.replace(pref, "").strip()
                if termino:
                    return {"accion": "nota", "parametros": {"operacion": "buscar", "termino": termino}}

    return None


def ejecutar(decision: dict) -> str:
    accion = decision.get("accion", "hablar")
    params = decision.get("parametros", {})

    if accion == "batch":
        acciones = params.get("acciones", []) or []
        respuestas: list[str] = []
        for d in acciones:
            if not isinstance(d, dict):
                continue
            try:
                r = ejecutar(d)
                if r:
                    respuestas.append(str(r))
            except Exception as e:
                log.warning("batch: fallo ejecutando sub-accion: %s", e)
        return "\n".join(respuestas).strip()

    if accion == "plugin":
        from plugins import ejecutar_plugin

        nombre = (params.get("nombre") or "").strip()
        orden = (params.get("orden") or "").strip()
        if not nombre:
            return "Plugin no especificado."
        res = ejecutar_plugin(nombre, orden or nombre, params or {})
        return res or ""

    dispatcher = {
        "abrir_app": lambda: abrir_app(params.get("app", "")),
        "abrir_carpeta": lambda: abrir_carpeta_conocida(params.get("carpeta", "")),
        "abrir_archivo": lambda: abrir_archivo_conocido(params.get("archivo", "")) or "No tengo ese archivo registrado",
        "buscar_archivo": lambda: buscar_archivo_en_carpeta(params.get("nombre", ""), params.get("carpeta", "documentos")),
        "listar_archivos": lambda: listar_archivos_carpeta(params.get("carpeta", "documentos"), params.get("extension")),
        "abrir_url": lambda: abrir_url(params.get("url", "")),
        "buscar_web": lambda: buscar_en_web(params.get("consulta", ""), params.get("motor", "google")),
        "sistema": lambda: obtener_info_sistema(),
        "volumen": lambda: controlar_volumen(params.get("accion", "subir")),
        "hablar": lambda: params.get("texto", ""),
        "recordatorio": lambda: accion_recordatorio(params.get("operacion", ""), params.get("mensaje", ""), params.get("tiempo", "")),
        "nota": lambda: accion_nota(params.get("operacion", ""), params.get("texto", ""), params.get("termino", "")),
        "clima": lambda: accion_clima(params.get("operacion", "actual"), params.get("ciudad") or None),
        "whatsapp": lambda: accion_whatsapp(params.get("operacion", ""), params.get("contacto", ""), params.get("mensaje", ""), params.get("tiempo", "")),
        "codigo": lambda: accion_codigo(params.get("peticion", ""), params.get("lenguaje") or None),
        "wifi": lambda: controlar_wifi(params.get("accion", "estado")),
        "bluetooth": lambda: controlar_bluetooth(params.get("accion", "estado")),
        "cambiar_ia": lambda: set_ia(params.get("ia", "auto")),
        "estado_ia": lambda: estado_ias(),
        "tokens": lambda: reporte_tokens(),
        "modelo_ollama": lambda: cambiar_modelo_ollama(params.get("modelo", "").strip() or None),
        "funcionalidades": lambda: accion_funcionalidades(params.get("tipo", "grupos"), params.get("grupo")),
    }

    if accion == "energia":
        return control_energia(params.get("accion", ""))

    if accion == "salir":
        hablar("Hasta luego")
        sys.exit(0)

    fn = dispatcher.get(accion)
    if fn:
        return fn()
    log.warning("Acción no reconocida: %s", accion)
    return "No sé cómo hacer eso aún"

