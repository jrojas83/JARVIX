# ia_online.py — Jarvis v6
# ════════════════════════════════════════════════════════════════════
# RESPONSABILIDAD DE ESTE MÓDULO
# ────────────────────────────────────────────────────────────────────
# Gestiona TODAS las comunicaciones con IAs, tanto en la nube como
# locales (Ollama).  Otros módulos nunca llaman a ninguna API directamente;
# siempre pasan por aquí.
#
# ESTRUCTURA INTERNA
# ────────────────────────────────────────────────────────────────────
#  1. SQLite helpers  – registrar y consultar uso de tokens
#  2. Estado de IA    – qué IA está activa y cómo cambiarla
#  3. Clasificadores  – detectar si la orden es petición de código
#  4. Llamadores      – _llamar_groq / _gemini / _anthropic
#  5. Router          – preguntar_online() elige la IA correcta
#  6. Generador code  – generar_codigo() → portapapeles → VSCode
#
# MODELOS GROQ VIGENTES (abril 2025)
# ────────────────────────────────────────────────────────────────────
#  llama3-8b-8192        → DESCONTINUADO  ← causa del error original
#  llama-3.1-8b-instant  → rápido y gratuito  ✅  ← usamos este
#  llama-3.3-70b-versatile → más potente, mismo tier gratuito
#  mixtral-8x7b-32768    → bueno para español
#  gemma2-9b-it          → liviano, buen español
#
# MODELOS OLLAMA PARA EQUIPOS DE BAJOS RECURSOS (Intel N100 / 8 GB RAM)
# ────────────────────────────────────────────────────────────────────
#  phi3:mini             → 3.8B · ~2.3 GB  · Mejor calidad/tamaño del catálogo
#  phi3.5:mini           → 3.8B · ~2.4 GB  · Versión mejorada de phi3
#  qwen2.5:1.5b          → 1.5B · ~1 GB    · El más liviano viable
#  qwen2.5:3b            → 3B   · ~1.9 GB  · Balance recomendado ✅
#  deepseek-coder:1.3b   → 1.3B · ~0.8 GB  · Especializado en código
#  deepseek-coder:6.7b   → 6.7B · ~3.8 GB  · Código avanzado (requiere 6+ GB libre)
#  llama3.2:3b           → 3B   · ~2 GB    · Buen español
#  gemma2:2b             → 2B   · ~1.6 GB  · Liviano, razona bien
#  smollm2:1.7b          → 1.7B · ~1.1 GB  · Diseñado para hardware limitado
# ════════════════════════════════════════════════════════════════════

import requests
import subprocess
import os
import time
from datetime import datetime
from logger import log

# ── Importación defensiva de config ───────────────────────────
try:
    from config import (
        GROQ_API_KEY, GEMINI_API_KEY, ANTHROPIC_API_KEY,
        MODELO_ONLINE, IA_PREFERIDA
    )
except ImportError:
    GROQ_API_KEY = GEMINI_API_KEY = ANTHROPIC_API_KEY = ""
    MODELO_ONLINE = "claude-haiku-4-5-20251001"
    IA_PREFERIDA  = "auto"
    log.warning("config.py no encontrado — arrancando solo con Ollama")

# ════════════════════════════════════════════════════════════════════
# 1. SQLite — CONTADOR DE TOKENS
# ════════════════════════════════════════════════════════════════════
# Guardamos en ~/.jarvis.db cuántos tokens consume cada IA por día.
# Esto permite al usuario saber si está cerca del límite gratuito.

HOME    = os.path.expanduser("~")
DB_PATH = os.path.join(HOME, ".jarvis.db")


def _db():
    """
    Abre (o crea) la base de datos SQLite de Jarvis.
    La tabla tokens_uso registra cada llamada: qué IA, cuándo,
    cuántos tokens de entrada (prompt) y salida (respuesta).
    """
    import sqlite3
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS tokens_uso (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            ia         TEXT    NOT NULL,
            fecha      TEXT    NOT NULL,
            tokens_in  INTEGER DEFAULT 0,
            tokens_out INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    return conn


def registrar_uso(ia_nombre, tokens_entrada, tokens_salida):
    """
    Inserta una fila en tokens_uso.
    Se llama automáticamente después de cada respuesta de IA.
    Si falla (disco lleno, permisos), solo se loguea — no rompe nada.
    """
    hoy = datetime.now().strftime("%Y-%m-%d")
    try:
        conn = _db()
        conn.execute(
            "INSERT INTO tokens_uso (ia, fecha, tokens_in, tokens_out) VALUES (?,?,?,?)",
            (ia_nombre, hoy, tokens_entrada, tokens_salida)
        )
        conn.commit()
        conn.close()
    except Exception as e:
        log.warning("registrar_uso falló (no crítico): %s", e)


def reporte_tokens():
    """
    Genera un resumen legible del uso de tokens.
    Muestra: uso de hoy y uso total histórico, por IA.
    """
    hoy = datetime.now().strftime("%Y-%m-%d")
    try:
        conn      = _db()
        filas     = conn.execute(
            "SELECT ia, SUM(tokens_in), SUM(tokens_out) FROM tokens_uso GROUP BY ia"
        ).fetchall()
        hoy_filas = conn.execute(
            "SELECT ia, SUM(tokens_in), SUM(tokens_out) FROM tokens_uso WHERE fecha=? GROUP BY ia",
            (hoy,)
        ).fetchall()
        conn.close()
    except Exception as e:
        log.warning("reporte_tokens: %s", e)
        return "No hay registro de uso de tokens aún."

    if not filas:
        return "No hay registro de uso de tokens aún."

    hoy_dict = {r[0]: (r[1] or 0, r[2] or 0) for r in hoy_filas}
    lineas   = ["Uso de tokens por IA:"]
    for ia, total_in, total_out in filas:
        hi, ho = hoy_dict.get(ia, (0, 0))
        lineas.append(
            f"  {ia}: hoy {hi+ho:,} tokens (entrada {hi:,} / salida {ho:,}) | "
            f"total {(total_in or 0)+(total_out or 0):,}"
        )
    return "\n".join(lineas)


def _contar_tokens_aprox(texto):
    """
    Estimación rápida de tokens sin tokenizador externo.
    Regla empírica: 1 token ≈ 3.5 caracteres en español.
    """
    return max(1, len(texto) // 3)


# ════════════════════════════════════════════════════════════════════
# 2. ESTADO DE IA ACTIVA
# ════════════════════════════════════════════════════════════════════
# _ia_activa es un dict mutable en memoria.
# Se persiste solo en la sesión actual; al reiniciar Jarvis vuelve
# al valor de IA_PREFERIDA en .env.

_ia_activa = {"nombre": IA_PREFERIDA}


def set_ia(nombre):
    """
    Cambia la IA activa para esta sesión.
    "auto" = prueba Groq → Gemini → Anthropic en orden.
    """
    opciones = ["auto", "groq", "gemini", "anthropic", "ollama"]
    nombre   = nombre.lower().strip()
    if nombre not in opciones:
        return f"IA '{nombre}' no reconocida. Opciones: {', '.join(opciones)}"
    _ia_activa["nombre"] = nombre
    log.info("IA cambiada a: %s", nombre)
    return f"IA cambiada a: {nombre}"


def get_ia():
    return _ia_activa["nombre"]


def _ollama_activo():
    """
    Verifica si Ollama está corriendo en localhost:11434.
    Timeout corto (2s) para no bloquear el arranque.
    """
    try:
        r = requests.get("http://localhost:11434/", timeout=2)
        return r.status_code == 200
    except Exception:
        return False


def estado_ias():
    """
    Muestra el estado de todas las IAs.
    Útil para diagnosticar por qué una IA no responde.
    """
    groq_ok  = bool(GROQ_API_KEY)
    gem_ok   = bool(GEMINI_API_KEY)
    anth_ok  = bool(ANTHROPIC_API_KEY)
    oll_ok   = _ollama_activo()
    lineas   = [
        f"IA activa en esta sesión: {_ia_activa['nombre']}",
        f"  Groq:       {'activa' if groq_ok  else 'sin configurar — console.groq.com (gratis)'}",
        f"  Gemini:     {'activa' if gem_ok   else 'sin configurar — aistudio.google.com (gratis)'}",
        f"  Anthropic:  {'activa' if anth_ok  else 'sin configurar — console.anthropic.com (pago)'}",
        f"  Ollama:     {'corriendo' if oll_ok else 'no disponible — ejecuta: ollama serve'}",
    ]
    if not any([groq_ok, gem_ok, anth_ok, oll_ok]):
        lineas.append("Ninguna IA disponible. Configura al menos una en .env")
    return "\n".join(lineas)


def ia_disponible():
    """
    Devuelve (disponible: bool, nombre: str) de la primera IA online lista.
    Si modo == "ollama" devuelve False para forzar el path local.
    """
    modo = _ia_activa["nombre"]
    if modo == "ollama":
        return False, "ollama"

    if modo == "auto":
        checks = [
            ("groq",      GROQ_API_KEY),
            ("gemini",    GEMINI_API_KEY),
            ("anthropic", ANTHROPIC_API_KEY),
        ]
    else:
        key_map = {
            "groq":      GROQ_API_KEY,
            "gemini":    GEMINI_API_KEY,
            "anthropic": ANTHROPIC_API_KEY,
        }
        checks = [(modo, key_map.get(modo, ""))]

    for nombre, key in checks:
        if key:
            return True, nombre
    return False, "none"


# ════════════════════════════════════════════════════════════════════
# 3. CLASIFICADORES DE PETICIONES
# ════════════════════════════════════════════════════════════════════
# Listas simples en vez de NLP pesado.
# En un Intel N100 con 8 GB RAM cargar spaCy toma 2-5 segundos solo
# en el import. Las listas de strings son O(n) puro e instantáneas.

_PALABRAS_CODIGO = [
    "escribe", "genera", "crea", "hazme", "dame", "implementa",
    "construye", "desarrolla", "programa",
    "función", "funcion", "script", "código", "codigo",
    "clase", "componente", "archivo", "algoritmo",
    "query", "consulta sql", "api", "endpoint",
]

_LENGUAJES = [
    "python", "javascript", "js", "typescript", "ts",
    "react", "vue", "bash", "shell", "html", "css",
    "sql", "java", "c++", "rust", "go", "php",
    "ruby", "kotlin", "swift",
]


def es_peticion_de_codigo(texto):
    """
    Detecta si el texto es una petición de código.
    Se llama DESPUÉS de procesar_sin_ia() para evitar falsos positivos
    como "crea un recordatorio" que no es código.
    """
    t = texto.lower()
    return any(p in t for p in _PALABRAS_CODIGO)


def detectar_lenguaje(texto):
    """Detecta el lenguaje de programación mencionado. Devuelve None si no hay."""
    t = texto.lower()
    return next((l for l in _LENGUAJES if l in t), None)


# ════════════════════════════════════════════════════════════════════
# 4. LLAMADORES A CADA IA
# ════════════════════════════════════════════════════════════════════
# Cada función devuelve str (respuesta) o None (fallo).
# NUNCA lanza excepciones hacia arriba.
# Los errores se loguean con mensajes descriptivos.

# Modelos Groq vigentes — se prueban en orden ante descontinuaciones
_GROQ_MODELOS = [
    "llama-3.1-8b-instant",     # rápido, gratuito  ← preferido
    "gemma2-9b-it",             # fallback liviano
    "llama-3.3-70b-versatile",  # más potente (mismo tier gratuito)
]


def _llamar_groq(prompt, historial):
    """
    Llama a Groq.
    Prueba modelos en orden si alguno está descontinuado.
    El modelo llama3-8b-8192 fue descontinuado en marzo 2025;
    por eso ahora usamos llama-3.1-8b-instant como primario.
    """
    try:
        from groq import Groq
        cliente = Groq(api_key=GROQ_API_KEY)
        msgs    = [{"role": m["role"], "content": m["content"]} for m in historial[-6:]]
        msgs.append({"role": "user", "content": prompt})

        for modelo in _GROQ_MODELOS:
            try:
                resp  = cliente.chat.completions.create(
                    model      = modelo,
                    messages   = msgs,
                    max_tokens = 600,
                    temperature= 0.7,
                )
                texto = resp.choices[0].message.content.strip()
                registrar_uso("groq", resp.usage.prompt_tokens, resp.usage.completion_tokens)
                log.info("Groq respondió con %s (%d tokens)", modelo, resp.usage.total_tokens)
                return texto
            except Exception as e_inner:
                err = str(e_inner)
                if any(k in err for k in ["decommissioned", "deprecated", "not found", "model_not_found"]):
                    log.warning("Groq: modelo '%s' no disponible, probando siguiente", modelo)
                    continue
                raise  # error real → propagar al except externo

        log.error("Groq: todos los modelos fallaron. Revisa https://console.groq.com/docs/models")
        return None

    except Exception as e:
        err = str(e)
        if "401" in err or "authentication" in err.lower():
            log.error("Groq: API key inválida — revisa GROQ_API_KEY en .env")
        elif "429" in err or "rate_limit" in err.lower():
            log.warning("Groq: límite de velocidad — espera unos segundos")
        elif "connection" in err.lower() or "timeout" in err.lower():
            log.warning("Groq: problema de conexión a internet")
        else:
            log.warning("Groq falló: %s", e)
        return None


def _llamar_gemini(prompt, historial):
    """
    Llama a Gemini (Google).
    Soporta el SDK nuevo (google.genai) y el legacy (google.generativeai).
    El SDK legacy muestra un FutureWarning; es funcional pero será eliminado.
    Para silenciarlo: pip install google-genai
    """
    contexto = "\n".join(
        f"{'Usuario' if m['role']=='user' else 'Jarvis'}: {m['content']}"
        for m in historial[-6:]
    )
    prompt_completo = f"{contexto}\nUsuario: {prompt}" if contexto else prompt

    # Intento 1: SDK nuevo google.genai
    try:
        import google.genai as genai
        cliente = genai.Client(api_key=GEMINI_API_KEY)
        resp    = cliente.models.generate_content(
            model    = "gemini-2.0-flash",
            contents = prompt_completo,
        )
        texto  = resp.text.strip()
        tokens = _contar_tokens_aprox(prompt_completo + texto)
        registrar_uso("gemini", tokens // 2, tokens // 2)
        log.info("Gemini (google.genai) respondió (~%d tokens)", tokens)
        return texto
    except ImportError:
        pass  # SDK nuevo no instalado → probar legacy
    except Exception as e:
        err = str(e)
        if "API_KEY" in err or "401" in err:
            log.error("Gemini: API key inválida — revisa GEMINI_API_KEY en .env")
            return None
        elif "quota" in err.lower() or "429" in err:
            log.warning("Gemini: cuota agotada. Considera 'cambia a groq'")
            return None
        log.warning("Gemini (google.genai) falló: %s", e)
        return None

    # Intento 2: SDK legacy google.generativeai
    try:
        import google.generativeai as genai_legacy  # type: ignore
        genai_legacy.configure(api_key=GEMINI_API_KEY)
        modelo = genai_legacy.GenerativeModel("gemini-1.5-flash")
        resp   = modelo.generate_content(prompt_completo)
        texto  = resp.text.strip()
        tokens = _contar_tokens_aprox(prompt_completo + texto)
        registrar_uso("gemini", tokens // 2, tokens // 2)
        log.info("Gemini (legacy) respondió (~%d tokens)", tokens)
        return texto
    except Exception as e:
        log.warning("Gemini (legacy) falló: %s", e)
        return None


def _llamar_anthropic(prompt, historial):
    """
    Llama a Anthropic (Claude).
    Requiere saldo en la cuenta — no hay tier gratuito.
    """
    try:
        import anthropic
        cliente = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        msgs    = [{"role": m["role"], "content": m["content"]} for m in historial[-6:]]
        msgs.append({"role": "user", "content": prompt})
        resp    = cliente.messages.create(
            model     = MODELO_ONLINE,
            max_tokens= 600,
            messages  = msgs,
        )
        texto = resp.content[0].text.strip()
        registrar_uso("anthropic", resp.usage.input_tokens, resp.usage.output_tokens)
        log.info("Anthropic respondió (%d tokens)", resp.usage.input_tokens + resp.usage.output_tokens)
        return texto
    except Exception as e:
        err = str(e)
        if "authentication" in err.lower() or "401" in err:
            log.error("Anthropic: API key inválida — revisa ANTHROPIC_API_KEY en .env")
        elif "insufficient_quota" in err or "402" in err:
            log.error("Anthropic: sin créditos — recarga en console.anthropic.com")
        elif "529" in err or "overload" in err.lower():
            log.warning("Anthropic: servidores sobrecargados")
        else:
            log.warning("Anthropic falló: %s", e)
        return None


# ════════════════════════════════════════════════════════════════════
# 5. ROUTER — preguntar_online
# ════════════════════════════════════════════════════════════════════

def preguntar_online(prompt, historial=None):
    """
    Punto de entrada principal para consultas a IA online.
    Devuelve str (respuesta) o None si todo falla → jarvis.py cae a Ollama.

    Flujo en modo 'auto':
      1. Groq  (gratis, rápido, 14.400 req/día)
      2. Gemini (gratis, 1M tokens/mes)
      3. Anthropic (pago)
    """
    if historial is None:
        historial = []

    ok, ia = ia_disponible()
    if not ok:
        log.info("Sin IA online disponible — usando Ollama")
        return None

    llamadores = {
        "groq":      _llamar_groq,
        "gemini":    _llamar_gemini,
        "anthropic": _llamar_anthropic,
    }

    # Modo específico
    if ia in llamadores:
        resultado = llamadores[ia](prompt, historial)
        if resultado is None:
            log.warning(
                "IA '%s' no respondió. "
                "Escribe 'estado de las ia' para diagnosticar o "
                "'cambia a gemini' para cambiar de proveedor.", ia
            )
        return resultado

    # Modo auto: prueba en orden
    for nombre, fn in llamadores.items():
        key_map = {"groq": GROQ_API_KEY, "gemini": GEMINI_API_KEY, "anthropic": ANTHROPIC_API_KEY}
        if key_map.get(nombre):
            resultado = fn(prompt, historial)
            if resultado:
                log.info("Modo auto: respondió %s", nombre)
                return resultado

    log.warning(
        "Ninguna IA online respondió. "
        "Verifica: conexión a internet, API keys en .env, límites de uso. "
        "Usando Ollama como fallback."
    )
    return None


# ════════════════════════════════════════════════════════════════════
# 6. GENERADOR DE CÓDIGO
# ════════════════════════════════════════════════════════════════════
# Timeout para Ollama = 120s.
# Justificación: en Intel N100 (4 cores E-series, sin GPU),
# un modelo de 3B parámetros genera ~8-15 tokens/segundo.
# Para 100 líneas de código (~150 tokens) → ~10-18 segundos.
# Para código más complejo (300+ tokens) → hasta 40-60 segundos.
# 120s es el límite seguro para no falsar un timeout legítimo.

def generar_codigo(peticion, lenguaje=None, pegar_vscode=True):
    """
    Genera código con la IA disponible.
    1. Intenta IA online (más rápida en hardware lento)
    2. Fallback: Ollama local con timeout de 120s
    3. Copia al portapapeles
    4. Pega en VSCode si está abierto
    """
    lang_str = f" en {lenguaje}" if lenguaje else ""
    prompt   = (
        f"Escribe código{lang_str} para: {peticion}\n\n"
        "Responde SOLO con el código. Sin explicaciones, sin backticks."
    )

    ok, _ = ia_disponible()
    codigo = preguntar_online(prompt) if ok else None

    if not codigo:
        from config import MODELO, URL_OLLAMA
        log.info("Generando código con Ollama (%s) — puede tardar hasta 2 min", MODELO)
        try:
            r      = requests.post(URL_OLLAMA, json={"model": MODELO, "prompt": prompt, "stream": False}, timeout=120)
            codigo = r.json().get("response", "").strip()
        except requests.exceptions.Timeout:
            log.error("Ollama timeout en generación de código (>120s). Modelo: %s", MODELO)
            return "Ollama tardó demasiado. Prueba: 'cambia el modelo a qwen2.5:1.5b'"
        except requests.exceptions.ConnectionError:
            log.error("No se puede conectar a Ollama. Ejecuta: ollama serve")
            return "Ollama no está corriendo. Ejecuta 'ollama serve' en otra terminal."
        except Exception as e:
            log.error("generar_codigo Ollama: %s", e)
            return f"Error generando código: {e}"

    if not codigo:
        return "No pude generar el código. Revisa la conexión o que Ollama esté corriendo."

    _copiar_portapapeles(codigo)
    if pegar_vscode:
        _pegar_en_vscode()

    lineas  = codigo.split("\n")
    preview = "\n".join(lineas[:5])
    sufijo  = f"\n[...{len(lineas)-5} líneas más — ver portapapeles]" if len(lineas) > 5 else ""
    return f"Código generado{lang_str}:\n{preview}{sufijo}"


def _copiar_portapapeles(texto):
    """Copia texto al portapapeles. Intenta xclip, luego xsel."""
    for cmd in [["xclip", "-selection", "clipboard"], ["xsel", "--clipboard", "--input"]]:
        try:
            subprocess.run(cmd, input=texto.encode(), check=True, capture_output=True)
            log.info("Portapapeles: %d chars con %s", len(texto), cmd[0])
            return
        except FileNotFoundError:
            continue
        except Exception as e:
            log.warning("_copiar_portapapeles (%s): %s", cmd[0], e)
    log.warning("No se pudo copiar al portapapeles — instala: sudo apt install xclip")


def _pegar_en_vscode():
    """Pega el portapapeles en VSCode si está abierto."""
    try:
        if subprocess.run(["pgrep", "-x", "code"], capture_output=True).returncode != 0:
            return
        time.sleep(0.3)
        subprocess.run(["xdotool", "search", "--name", "Visual Studio Code", "windowfocus", "--sync"], capture_output=True)
        time.sleep(0.2)
        subprocess.run(["xdotool", "key", "ctrl+v"], capture_output=True)
        log.info("Código pegado en VSCode")
    except Exception as e:
        log.warning("_pegar_en_vscode: %s", e)
