#!/usr/bin/env python3
# jarvis.py — Jarvis v5
#
# Uso:
#   python jarvis.py              → modo texto
#   python jarvis.py --voz        → modo voz continua
#   python jarvis.py --espera     → modo espera (di "jarvis" para activar)
#
# Primero: cp .env.example .env  y rellena tus API keys

import json
import os
import re
import sys
from datetime import datetime

from logger import log
from config import (
    MODELO, URL_OLLAMA, APPS_PERMITIDAS, CARPETAS,
    ARCHIVOS_CONOCIDOS, URLS_WEB,
    NOMBRE_USUARIO, saludo_contextual,
)
from cache import cache, TTL_CLIMA, TTL_SISTEMA, TTL_IA
from consola import (
    cronometro, imprimir_orden, imprimir_respuesta,
    imprimir_estado, imprimir_banner,
)

# Lazy loading: requests solo se importa cuando se usa
_requests_module = None

def _get_requests():
    """Importa requests bajo demanda (lazy loading)."""
    global _requests_module
    if _requests_module is None:
        import requests
        _requests_module = requests
    return _requests_module

from acciones import (
    abrir_app, abrir_carpeta_conocida, abrir_archivo_conocido,
    buscar_archivo_en_carpeta, listar_archivos_carpeta,
    abrir_url, abrir_url_conocida, buscar_en_web,
    abrir_whatsapp, obtener_info_sistema, controlar_volumen,
    control_energia, accion_recordatorio, accion_nota,
    accion_clima, accion_whatsapp, accion_codigo,
    controlar_wifi, controlar_bluetooth,
    cambiar_modelo_ollama, notificar, accion_funcionalidades,
)
from ia_online import (
    es_peticion_de_codigo, detectar_lenguaje,
    ia_disponible, preguntar_online,
    set_ia, get_ia, estado_ias, reporte_tokens,
)
from recordatorios import init_db, restaurar_recordatorios_pendientes
from voz import escuchar, escuchar_con_activacion, hablar
from plugins import cargar_plugins, ejecutar_por_orden, resumen_plugins
from jarvis_core.intents.patterns import (
    PATRONES_HORA, PATRONES_FECHA, PATRONES_SISTEMA, PATRONES_SALIR,
    PATRONES_VOL_SUBIR, PATRONES_VOL_BAJAR, PATRONES_VOL_SILENCIO, PATRONES_VOL_MAXIMO,
    PATRONES_CLIMA, PATRONES_CLIMA_PRONOS,
    PATRONES_RECORDATORIO_CREAR, PATRONES_RECORDATORIO_LISTAR, PATRONES_RECORDATORIO_CANCELAR,
    PATRONES_NOTA_AGREGAR, PATRONES_NOTA_LEER, PATRONES_NOTA_BORRAR, PATRONES_NOTA_BUSCAR,
    PATRONES_WIFI, PATRONES_WIFI_ACTIVAR, PATRONES_WIFI_DESACT, PATRONES_WIFI_LISTAR,
    PATRONES_BLUETOOTH, PATRONES_BT_ACTIVAR, PATRONES_BT_DESACT, PATRONES_BT_ABRIR,
    PATRONES_SUSPENDER, PATRONES_APAGAR, PATRONES_REINICIAR,
    PATRONES_BUSCAR_GOOGLE, PATRONES_BUSCAR_YOUTUBE, PATRONES_BUSCAR_WIKI,
    PATRONES_IA_ESTADO, PATRONES_TOKENS, PATRONES_CAMBIAR_IA, PATRONES_MODELO_OLL, PATRONES_MODELOS_LIST,
    PATRONES_FUNCIONES_TODAS, PATRONES_FUNCIONES_GRUPOS,
    GRUPOS_FUNCIONALIDADES,
)

MEMORIA_FILE = "memoria.json"


# ─── Memoria de conversación ──────────────────────────────────

def cargar_memoria():
    if os.path.exists(MEMORIA_FILE):
        try:
            with open(MEMORIA_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            log.warning("No se pudo cargar memoria: %s", e)
    return []

def guardar_memoria(historial):
    try:
        with open(MEMORIA_FILE, "w") as f:
            json.dump(historial[-40:], f, indent=2, ensure_ascii=False)
    except Exception as e:
        log.warning("No se pudo guardar memoria: %s", e)


# ─── Consulta a Ollama (fallback local) ───────────────────────

def preguntar_ia_local(orden, historial):
    """Consulta a Ollama. Devuelve dict de decisión o respuesta de texto."""
    # ── Caché ──────────────────────────────────────────────────
    cached = cache.get(orden, ttl=TTL_IA)
    if cached is not None:
        imprimir_estado(f"Respuesta desde caché", "info")
        return cached
    apps_lista     = list(APPS_PERMITIDAS.keys())
    carpetas_lista = list(CARPETAS.keys())
    archivos_lista = list(ARCHIVOS_CONOCIDOS.keys())
    urls_lista     = list(URLS_WEB.keys())

    sistema = f"""Eres Jarvis, un asistente de escritorio en Linux Ubuntu.
Analiza la orden y responde ÚNICAMENTE con JSON válido, sin texto extra, sin ```json.

Acciones disponibles:
{{
  "accion": "abrir_app"|"abrir_carpeta"|"abrir_archivo"|"buscar_archivo"|
            "listar_archivos"|"abrir_url"|"buscar_web"|"abrir_whatsapp"|
            "sistema"|"volumen"|"energia"|"hablar"|"salir"|
            "recordatorio"|"nota"|"clima"|"whatsapp"|"codigo",
  "parametros": {{}}
}}

Parámetros por acción:
- abrir_app:       {{"app": "nombre"}}
- abrir_carpeta:   {{"carpeta": "nombre"}}
- abrir_archivo:   {{"archivo": "apodo"}}
- buscar_archivo:  {{"nombre": "texto", "carpeta": "nombre"}}
- listar_archivos: {{"carpeta": "nombre", "extension": "pdf"}}
- abrir_url:       {{"url": "https://..."}}
- buscar_web:      {{"consulta": "texto", "motor": "google|youtube|wikipedia"}}
- volumen:         {{"accion": "subir"|"bajar"|"silenciar"|"maximo"}}
- energia:         {{"accion": "apagar"|"reiniciar"|"suspender"}}
- hablar:          {{"texto": "respuesta"}}
- recordatorio:    {{"operacion": "crear"|"listar"|"cancelar", "mensaje": "texto", "tiempo": "10 minutos"}}
- nota:            {{"operacion": "agregar"|"leer"|"borrar"|"buscar", "texto": "...", "termino": "..."}}
- clima:           {{"operacion": "actual"|"pronostico", "ciudad": "Cali"}}
- whatsapp:        {{"operacion": "abrir"|"enviar"|"leer"|"recordatorio"|"estado"|"cerrar",
                    "contacto": "Nombre", "mensaje": "texto", "tiempo": "10 minutos"}}
- codigo:          {{"peticion": "descripción", "lenguaje": "python|javascript|..."}}

Apps registradas: {apps_lista[:10]}
Carpetas: {carpetas_lista}
"""
    contexto = ""
    for msg in historial[-6:]:
        rol = "Usuario" if msg["role"] == "user" else "Jarvis"
        contexto += f"{rol}: {msg['content']}\n"

    payload = {
        "model": MODELO,
        "prompt": sistema + f"\nContexto:\n{contexto}\nOrden: {orden}\nRespuesta JSON:",
        "stream": False
    }
    try:
        t0 = __import__("time").monotonic()
        r = requests.post(URL_OLLAMA, json=payload, timeout=120)
        ms = int((__import__("time").monotonic() - t0) * 1000)
        raw = r.json().get("response", "").strip()
        inicio = raw.find("{")
        fin    = raw.rfind("}") + 1
        if inicio == -1:
            raise ValueError("Sin JSON")
        resultado = json.loads(raw[inicio:fin])
        imprimir_estado(f"Ollama respondió en {ms}ms", "ok")
        cache.set(orden, resultado, ttl=TTL_IA)
        return resultado
    except json.JSONDecodeError as e:
        log.warning("preguntar_ia_local: Ollama respondió pero no con JSON válido: %s", e)
        return {"accion": "hablar", "parametros": {"texto": "No entendí bien la respuesta de la IA, ¿puedes repetir?"}}
    except requests.exceptions.Timeout:
        log.error(
            "preguntar_ia_local: Ollama tardó más de 120 segundos. "
            "En Intel N100 esto puede pasar con modelos de 7B+. "
            "Considera: 'cambia el modelo a qwen2.5:1.5b' para respuestas más rápidas."
        )
        return {"accion": "hablar", "parametros": {"texto": "La IA local tardó demasiado. Prueba cambiar a un modelo más liviano."}}
    except requests.exceptions.ConnectionError:
        log.error(
            "preguntar_ia_local: No se pudo conectar a Ollama en localhost:11434. "
            "Solución: ejecuta 'ollama serve' en otra terminal."
        )
        return {"accion": "hablar", "parametros": {"texto": "Ollama no está corriendo. Ejecuta 'ollama serve' en otra terminal."}}
    except Exception as e:
        log.error("preguntar_ia_local error inesperado: %s", e, exc_info=True)
        return {"accion": "hablar", "parametros": {"texto": f"Error en la IA local: {e}"}}


# ─── Procesamiento sin IA (modo rápido con patrones) ──────────

# Optimización: precompilar tuplas de búsqueda para operaciones frecuentes
_PATRONES_WHATSAPP_ESTADO = ("estado whatsapp", "whatsapp conectado")
_PATRONES_WHATSAPP_CERRAR = ("cierra whatsapp", "cerrar whatsapp")
_PATRONES_WHATSAPP_ABRIR = ("abre ", "abrir ", "ejecuta ")
_PATRONES_LISTAR = ("qué hay en", "lista", "mostrar archivos")
_PATRONES_APP_ACCION = ("abre", "abrir", "ejecuta")
_PATRONES_CARPETA_ACCION = ("abre", "muestra", "carpeta", "abrir")


def procesar_sin_ia(orden):
    """
    Detecta intenciones comunes directamente con patrones.
    Más rápido que pasar por Ollama para comandos frecuentes.
    Los patrones están centralizados en intenciones.py.
    Devuelve dict de decisión o None si no detecta nada.
    """
    o = orden.lower().strip()

    # ── WhatsApp (va primero para no ser capturado por el loop de apps) ──
    m_enviar = re.search(
        r'(?:manda|envía|envia|enviar|mándame|mandame)\s+(?:whatsapp|mensaje|wa)\s+a\s+([^:]+):\s*(.+)',
        o
    )
    if m_enviar:
        return {"accion": "whatsapp", "parametros": {
            "operacion": "enviar",
            "contacto":  m_enviar.group(1).strip().title(),
            "mensaje":   m_enviar.group(2).strip()
        }}

    m_leer = re.search(r'(?:lee|leer|muestra|ver)\s+(?:mis\s+)?mensajes\s+de\s+(.+)', o)
    if m_leer:
        return {"accion": "whatsapp", "parametros": {
            "operacion": "leer",
            "contacto":  m_leer.group(1).strip().title()
        }}

    if "whatsapp" in o and any(p in o for p in ("recuérdame", "recuerdame", "recordatorio")):
        m_wa = re.search(r'en\s+([\d\w\s]+?)\s+(?:a|para)\s+([^\s:]+)(?::\s*(.+))?', o)
        if m_wa:
            return {"accion": "whatsapp", "parametros": {
                "operacion": "recordatorio",
                "contacto":  m_wa.group(2).strip().title(),
                "mensaje":   (m_wa.group(3) or "recordatorio de Jarvis").strip(),
                "tiempo":    m_wa.group(1).strip(),
            }}

    if any(p in o for p in _PATRONES_WHATSAPP_ESTADO):
        return {"accion": "whatsapp", "parametros": {"operacion": "estado"}}
    if any(p in o for p in _PATRONES_WHATSAPP_CERRAR):
        return {"accion": "whatsapp", "parametros": {"operacion": "cerrar"}}
    if "whatsapp" in o and any(p in o for p in _PATRONES_WHATSAPP_ABRIR):
        return {"accion": "whatsapp", "parametros": {"operacion": "abrir"}}

    # ── Funcionalidades por voz ────────────────────────────────
    if any(p in o for p in PATRONES_FUNCIONES_TODAS):
        return {"accion": "funcionalidades", "parametros": {"tipo": "total"}}

    if any(p in o for p in PATRONES_FUNCIONES_GRUPOS):
        return {"accion": "funcionalidades", "parametros": {"tipo": "grupos"}}

    # "funcionalidades de [grupo]" o "ingresar a [grupo]"
    m_grupo = re.search(r'(?:funcionalidades de|ingresar a|entrar a|qué hace|que hace)\s+([a-záéíóúñ\s]+)', o)
    if m_grupo:
        nombre_grupo = m_grupo.group(1).strip()
        return {"accion": "funcionalidades", "parametros": {"tipo": "grupo_especifico", "grupo": nombre_grupo}}

    # ── Apps (excluye whatsapp ya manejado) ───────────────────
    for app_key in APPS_PERMITIDAS:
        if app_key == "whatsapp":
            continue
        if app_key in o and any(p in o for p in ["abre", "abrir", "ejecuta"]):
            return {"accion": "abrir_app", "parametros": {"app": app_key}}

    # ── Carpetas ──────────────────────────────────────────────
    for carpeta_key in CARPETAS:
        if carpeta_key in o and any(p in o for p in ["abre", "muestra", "carpeta", "abrir"]):
            return {"accion": "abrir_carpeta", "parametros": {"carpeta": carpeta_key}}

    # ── Listar contenido ──────────────────────────────────────
    if any(p in o for p in ["qué hay en", "lista", "mostrar archivos"]):
        for carpeta_key in CARPETAS:
            if carpeta_key in o:
                return {"accion": "listar_archivos", "parametros": {"carpeta": carpeta_key}}

    # ── Búsqueda web ──────────────────────────────────────────
    for patrones, motor in [
        (PATRONES_BUSCAR_GOOGLE,  "google"),
        (PATRONES_BUSCAR_YOUTUBE, "youtube"),
        (PATRONES_BUSCAR_WIKI,    "wikipedia"),
    ]:
        for p in patrones:
            if p in o:
                consulta = o
                for pat in patrones:
                    consulta = consulta.replace(pat, "").strip()
                return {"accion": "buscar_web", "parametros": {"consulta": consulta, "motor": motor}}

    # ── Volumen ───────────────────────────────────────────────
    if any(p in o for p in PATRONES_VOL_SUBIR):
        return {"accion": "volumen", "parametros": {"accion": "subir"}}
    if any(p in o for p in PATRONES_VOL_BAJAR):
        return {"accion": "volumen", "parametros": {"accion": "bajar"}}
    if any(p in o for p in PATRONES_VOL_SILENCIO):
        return {"accion": "volumen", "parametros": {"accion": "silenciar"}}
    if any(p in o for p in PATRONES_VOL_MAXIMO):
        return {"accion": "volumen", "parametros": {"accion": "maximo"}}

    # ── Hora y fecha ──────────────────────────────────────────
    if any(p in o for p in PATRONES_HORA):
        hora = datetime.now().strftime("%H:%M")
        return {"accion": "hablar", "parametros": {"texto": f"Son las {hora}"}}

    if any(p in o for p in PATRONES_FECHA):
        fecha = datetime.now().strftime("%A %d de %B de %Y")
        return {"accion": "hablar", "parametros": {"texto": f"Hoy es {fecha}"}}

    # ── Sistema ───────────────────────────────────────────────
    if any(p in o for p in PATRONES_SISTEMA):
        return {"accion": "sistema", "parametros": {}}

    # ── Salir ─────────────────────────────────────────────────
    if any(o == p for p in PATRONES_SALIR):
        return {"accion": "salir", "parametros": {}}

    # ── Clima ─────────────────────────────────────────────────
    if any(p in o for p in PATRONES_CLIMA):
        operacion = "pronostico" if any(p in o for p in PATRONES_CLIMA_PRONOS) else "actual"
        ciudad = None
        for prefijo in ["clima en ", "tiempo en ", "temperatura en ",
                         "cómo está el clima en ", "como esta el clima en "]:
            if prefijo in o:
                ciudad = o.split(prefijo, 1)[1].strip().rstrip("?¿.,")
                break
        return {"accion": "clima", "parametros": {"operacion": operacion, "ciudad": ciudad or ""}}

    # ── Código / IA en línea ──────────────────────────────────
    if es_peticion_de_codigo(o):
        lenguaje = detectar_lenguaje(o)
        return {"accion": "codigo", "parametros": {"peticion": orden, "lenguaje": lenguaje or ""}}

    # ── Cambio de IA ──────────────────────────────────────────
    if any(p in o for p in PATRONES_CAMBIAR_IA):
        for frase in PATRONES_CAMBIAR_IA:
            if frase in o:
                ia_nombre = o.split(frase, 1)[1].strip().split()[0]
                return {"accion": "cambiar_ia", "parametros": {"ia": ia_nombre}}

    if any(p in o for p in PATRONES_IA_ESTADO):
        return {"accion": "estado_ia", "parametros": {}}

    if any(p in o for p in PATRONES_TOKENS):
        return {"accion": "tokens", "parametros": {}}

    # ── Cambio de modelo Ollama ───────────────────────────────
    for frase in PATRONES_MODELO_OLL:
        if frase in o:
            modelo = o.split(frase, 1)[1].strip()
            return {"accion": "modelo_ollama", "parametros": {"modelo": modelo}}

    if any(p in o for p in PATRONES_MODELOS_LIST):
        return {"accion": "modelo_ollama", "parametros": {"modelo": ""}}

    # ── WiFi ──────────────────────────────────────────────────
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

    # ── Energía ───────────────────────────────────────────────
    if any(p in o for p in PATRONES_SUSPENDER):
        return {"accion": "energia", "parametros": {"accion": "suspender"}}
    if any(p in o for p in PATRONES_APAGAR):
        return {"accion": "energia", "parametros": {"accion": "apagar"}}
    if any(p in o for p in PATRONES_REINICIAR):
        return {"accion": "energia", "parametros": {"accion": "reiniciar"}}

    # ── Bluetooth ─────────────────────────────────────────────
    if any(p in o for p in PATRONES_BLUETOOTH):
        if any(p in o for p in PATRONES_BT_ACTIVAR):
            return {"accion": "bluetooth", "parametros": {"accion": "activar"}}
        if any(p in o for p in PATRONES_BT_DESACT):
            return {"accion": "bluetooth", "parametros": {"accion": "desactivar"}}
        if any(p in o for p in PATRONES_BT_ABRIR):
            return {"accion": "bluetooth", "parametros": {"accion": "abrir"}}
        return {"accion": "bluetooth", "parametros": {"accion": "estado"}}

    # ── Recordatorios ─────────────────────────────────────────
    if any(p in o for p in PATRONES_RECORDATORIO_CREAR):
        patrones_tiempo = [
            r'en\s+(\d+\s*hora[s]?\s+y\s+\d+\s*minuto[s]?)',
            r'en\s+(\d+\s*hora[s]?)',
            r'en\s+(\d+\s*minuto[s]?)',
            r'en\s+(\d+\s*segundo[s]?)',
            r'en\s+(media\s*hora)',
            r'en\s+(cuarto\s*de\s*hora)',
        ]
        tiempo_enc = None
        mensaje_raw = ""
        for pat in patrones_tiempo:
            m = re.search(pat, o)
            if m:
                tiempo_enc  = m.group(1)
                mensaje_raw = o[m.end():].strip()
                for pref in ["que", "de", "para", ":"]:
                    if mensaje_raw.startswith(pref):
                        mensaje_raw = mensaje_raw[len(pref):].strip()
                break
        if tiempo_enc and mensaje_raw:
            return {"accion": "recordatorio", "parametros": {
                "operacion": "crear",
                "mensaje":   mensaje_raw,
                "tiempo":    tiempo_enc,
            }}

    if any(p in o for p in PATRONES_RECORDATORIO_LISTAR):
        return {"accion": "recordatorio", "parametros": {"operacion": "listar"}}

    if any(p in o for p in PATRONES_RECORDATORIO_CANCELAR):
        return {"accion": "recordatorio", "parametros": {"operacion": "cancelar"}}

    # ── Notas ─────────────────────────────────────────────────
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

    return None   # No detectado → usar IA


# ─── Ejecutar decisión ────────────────────────────────────────

def ejecutar(decision):
    accion = decision.get("accion", "hablar")
    params = decision.get("parametros", {})

    dispatcher = {
        "abrir_app":      lambda: abrir_app(params.get("app", "")),
        "abrir_carpeta":  lambda: abrir_carpeta_conocida(params.get("carpeta", "")),
        "abrir_archivo":  lambda: abrir_archivo_conocido(params.get("archivo", "")) or "No tengo ese archivo registrado",
        "buscar_archivo": lambda: buscar_archivo_en_carpeta(params.get("nombre", ""), params.get("carpeta", "documentos")),
        "listar_archivos":lambda: listar_archivos_carpeta(params.get("carpeta", "documentos"), params.get("extension")),
        "abrir_url":      lambda: abrir_url(params.get("url", "")),
        "buscar_web":     lambda: buscar_en_web(params.get("consulta", ""), params.get("motor", "google")),
        "abrir_whatsapp": lambda: abrir_whatsapp(),
        "sistema":        lambda: obtener_info_sistema(),
        "volumen":        lambda: controlar_volumen(params.get("accion", "subir")),
        "hablar":         lambda: params.get("texto", ""),
        "recordatorio":   lambda: accion_recordatorio(params.get("operacion", ""), params.get("mensaje", ""), params.get("tiempo", "")),
        "nota":           lambda: accion_nota(params.get("operacion", ""), params.get("texto", ""), params.get("termino", "")),
        "clima":          lambda: accion_clima(params.get("operacion", "actual"), params.get("ciudad") or None),
        "whatsapp":       lambda: accion_whatsapp(params.get("operacion", ""), params.get("contacto", ""), params.get("mensaje", ""), params.get("tiempo", "")),
        "codigo":         lambda: accion_codigo(params.get("peticion", ""), params.get("lenguaje") or None),
        "wifi":           lambda: controlar_wifi(params.get("accion", "estado")),
        "bluetooth":      lambda: controlar_bluetooth(params.get("accion", "estado")),
        "cambiar_ia":     lambda: set_ia(params.get("ia", "auto")),
        "estado_ia":      lambda: estado_ias(),
        "tokens":         lambda: reporte_tokens(),
        "modelo_ollama":  lambda: cambiar_modelo_ollama(params.get("modelo", "").strip() or None),
        "funcionalidades":lambda: accion_funcionalidades(params.get("tipo", "grupos"), params.get("grupo")),
    }

    if accion == "energia":
        accion_en = params.get("accion", "")
        if accion_en == "apagar":
            resp = input("⚠️  ¿Seguro que quieres APAGAR? (si/no): ").strip().lower()
            if resp != "si":
                return "Apagado cancelado"
        return control_energia(accion_en)

    if accion == "salir":
        hablar("Hasta luego")
        sys.exit(0)

    fn = dispatcher.get(accion)
    if fn:
        return fn()
    log.warning("Acción no reconocida: %s", accion)
    return "No sé cómo hacer eso aún"


# ─── Main ─────────────────────────────────────────────────────

def main():
    # ── Modo diagnóstico ───────────────────────────────────────
    if "test" in sys.argv or "diagnostico" in sys.argv:
        from diagnostico import ejecutar_diagnostico
        ok = ejecutar_diagnostico()
        sys.exit(0 if ok else 1)

    # Inicializar base de datos y restaurar recordatorios pendientes
    init_db()
    pendientes = restaurar_recordatorios_pendientes()

    # Cargar plugins
    plugins_cargados = cargar_plugins()

    historial = cargar_memoria()

    modo_voz    = "--voz"    in sys.argv
    modo_espera = "--espera" in sys.argv
    modo = "voz" if modo_voz else "espera" if modo_espera else "texto"

    log.info("Jarvis v7 iniciado — modo: %s", modo)

    online_ok, _ = ia_disponible()
    imprimir_banner(
        version="7",
        modo=modo,
        ia_online=online_ok,
        nombre_usuario=NOMBRE_USUARIO,
    )

    if pendientes:
        imprimir_estado(f"{pendientes} recordatorio(s) restaurados de la sesión anterior", "warn")
    if plugins_cargados:
        imprimir_estado(f"Plugins: {', '.join(plugins_cargados)}", "ok")

    # Saludo personalizado
    saludo = saludo_contextual()
    hablar(saludo)
    notificar("🤖 Jarvis activo", saludo,
              urgencia="low", icono="dialog-information", duracion=3000)

    while True:
        try:
            # ── Capturar orden ────────────────────────────────
            if modo_espera:
                orden = escuchar_con_activacion()
            elif modo_voz:
                orden = escuchar()
                if not orden:
                    continue
            else:
                try:
                    orden = input("\nJarvis › ").strip()
                except EOFError:
                    break
                if not orden:
                    continue

            # ── Comandos especiales de consola ────────────────
            if orden.lower() in ("ayuda", "help"):
                from jarvis_core.intents.patterns import ayuda_grupos
                print(ayuda_grupos())
                print("\n  Escribe 'funcionalidades totales' para ver todos los comandos.")
                continue

            if orden.lower() in ("test", "diagnóstico", "diagnostico"):
                from diagnostico import ejecutar_diagnostico
                ejecutar_diagnostico()
                continue

            if orden.lower() in ("caché", "cache", "estadísticas cache"):
                print(f"  {cache.stats()}")
                continue

            if orden.lower() in ("plugins", "qué plugins tienes", "que plugins tienes"):
                print(resumen_plugins())
                continue

            imprimir_orden(orden)
            log.info("Orden recibida: %s", orden[:100])
            historial.append({"role": "user", "content": orden})

            # ── Flujo: plugins → rápido → IA online → Ollama ──
            # 1. Plugins (primero — pueden sobreescribir comportamiento)
            respuesta_plugin = ejecutar_por_orden(orden)
            if respuesta_plugin is not None:
                imprimir_respuesta(respuesta_plugin, fuente="plugin")
                hablar(respuesta_plugin)
                historial.append({"role": "assistant", "content": respuesta_plugin})
                guardar_memoria(historial)
                continue

            # 2. Patrones rápidos (sin IA)
            decision = procesar_sin_ia(orden)

            if decision is None:
                if es_peticion_de_codigo(orden):
                    lenguaje = detectar_lenguaje(orden)
                    decision = {"accion": "codigo", "parametros": {
                        "peticion": orden, "lenguaje": lenguaje or ""
                    }}
                else:
                    # 3. IA online
                    online_ok, _ = ia_disponible()
                    if online_ok:
                        with cronometro("online") as c:
                            respuesta_online = preguntar_online(orden, historial)
                        if respuesta_online:
                            imprimir_respuesta(respuesta_online, fuente=get_ia(), ms=c.ms)
                            hablar(respuesta_online)
                            historial.append({"role": "assistant", "content": respuesta_online})
                            guardar_memoria(historial)
                            continue
                    # 4. Ollama local
                    imprimir_estado("Consultando IA local (Ollama)...", "info")
                    decision = preguntar_ia_local(orden, historial)

            respuesta = ejecutar(decision)

            if respuesta:
                fuente = "cache" if cache.get(orden, ttl=TTL_IA) == decision else "patron"
                imprimir_respuesta(respuesta, fuente=fuente)
                hablar(respuesta)
                historial.append({"role": "assistant", "content": respuesta})
                guardar_memoria(historial)

        except KeyboardInterrupt:
            print()
            hablar("Hasta luego")
            log.info("Jarvis cerrado por el usuario")
            break
        except Exception as e:
            log.error("Error en bucle principal: %s", e, exc_info=True)
            imprimir_estado(f"Error: {e}", "error")


if __name__ == "__main__":
    # Nueva arquitectura (v7+): bucle principal asíncrono con
    # resiliencia de IA (timeouts/retries/circuit breaker) y
    # estrategia "first model wins".
    #
    # Conservamos este archivo como entrypoint por compatibilidad,
    # pero delegamos al core.
    from jarvis_core.app import main as core_main

    raise SystemExit(core_main(sys.argv))
