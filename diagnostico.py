# diagnostico.py — Jarvis v7
# Autodiagnóstico completo del sistema.
# Uso: python jarvis.py test
#
# Verifica:
#   1. Ollama → responde en localhost:11434
#   2. API keys → micro-petición real a cada IA configurada
#   3. OpenWeatherMap → un fetch de clima
#   4. espeak/pyttsx3 → síntesis de voz
#   5. Micrófono → reconocimiento de voz disponible
#   6. Plugins → todos cargan sin error
#   7. Base de datos → SQLite accesible
#   8. Caché → funciona correctamente
#
# Cada verificación muestra ✅ OK | ⚠️ advertencia | ❌ error + solución.

import os
import sys
import time
import subprocess

# ─── Colores ANSI (sin dependencias externas) ─────────────────
VERDE  = "\033[92m"
ROJO   = "\033[91m"
AMBAR  = "\033[93m"
CYAN   = "\033[96m"
GRIS   = "\033[90m"
RESET  = "\033[0m"
BOLD   = "\033[1m"

OK   = f"{VERDE}✅ OK{RESET}"
WARN = f"{AMBAR}⚠️  AVISO{RESET}"
FAIL = f"{ROJO}❌ FALLO{RESET}"


def _titulo(texto: str):
    print(f"\n{BOLD}{CYAN}{'─'*50}{RESET}")
    print(f"{BOLD}{CYAN}  {texto}{RESET}")
    print(f"{BOLD}{CYAN}{'─'*50}{RESET}")


def _linea(estado: str, descripcion: str, detalle: str = ""):
    print(f"  {estado}  {descripcion}")
    if detalle:
        print(f"        {GRIS}{detalle}{RESET}")


def _medir(fn):
    t0 = time.monotonic()
    try:
        resultado = fn()
        elapsed = time.monotonic() - t0
        return resultado, elapsed, None
    except Exception as e:
        elapsed = time.monotonic() - t0
        return None, elapsed, e


# ─── Checks individuales ──────────────────────────────────────

def check_ollama() -> tuple[bool, str]:
    import requests
    try:
        r = requests.get("http://localhost:11434/api/tags", timeout=5)
        modelos = [m["name"] for m in r.json().get("models", [])]
        return True, f"{len(modelos)} modelos instalados: {', '.join(modelos[:4])}"
    except requests.exceptions.ConnectionError:
        return False, "Ollama no responde. Ejecuta: ollama serve"
    except Exception as e:
        return False, str(e)


def check_groq() -> tuple[bool, str]:
    from config import GROQ_API_KEY
    if not GROQ_API_KEY:
        return None, "No configurada (GROQ_API_KEY vacía)"
    import requests
    try:
        r = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROQ_API_KEY}",
                     "Content-Type": "application/json"},
            json={"model": "llama-3.1-8b-instant",
                  "messages": [{"role": "user", "content": "di solo: ok"}],
                  "max_tokens": 5},
            timeout=10
        )
        if r.status_code == 200:
            return True, "API key válida"
        return False, f"Error HTTP {r.status_code}: {r.text[:100]}"
    except Exception as e:
        return False, str(e)


def check_gemini() -> tuple[bool, str]:
    from config import GEMINI_API_KEY
    if not GEMINI_API_KEY:
        return None, "No configurada (GEMINI_API_KEY vacía)"
    import requests
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"
        r = requests.post(url, json={"contents": [{"parts": [{"text": "di solo: ok"}]}]}, timeout=10)
        if r.status_code == 200:
            return True, "API key válida"
        return False, f"Error HTTP {r.status_code}: {r.text[:100]}"
    except Exception as e:
        return False, str(e)


def check_clima() -> tuple[bool, str]:
    from config import OPENWEATHER_API_KEY, CIUDAD_DEFAULT
    if not OPENWEATHER_API_KEY:
        return None, "No configurada (OPENWEATHER_API_KEY vacía)"
    import requests
    try:
        url = f"https://api.openweathermap.org/data/2.5/weather?q={CIUDAD_DEFAULT}&appid={OPENWEATHER_API_KEY}"
        r = requests.get(url, timeout=8)
        if r.status_code == 200:
            data = r.json()
            ciudad = data.get("name", CIUDAD_DEFAULT)
            temp = data["main"]["temp"] - 273.15
            return True, f"OK — {ciudad}: {temp:.1f}°C"
        return False, f"Error HTTP {r.status_code}"
    except Exception as e:
        return False, str(e)


def check_espeak() -> tuple[bool, str]:
    try:
        subprocess.run(
            ["espeak-ng", "-v", "es", "-s", "150", "test", "--stdout"],
            capture_output=True, timeout=5, check=True
        )
        return True, "espeak-ng disponible"
    except FileNotFoundError:
        try:
            subprocess.run(["espeak", "test", "--stdout"],
                           capture_output=True, timeout=5, check=True)
            return True, "espeak disponible (sin -ng)"
        except FileNotFoundError:
            return False, "espeak no encontrado. Instala: sudo apt install espeak-ng"
    except Exception as e:
        return False, str(e)


def check_microfono() -> tuple[bool, str]:
    try:
        # Verificar faster-whisper (nuevo sistema de voz offline)
        from faster_whisper import WhisperModel
        # Carga rápida para verificar disponibilidad
        model = WhisperModel("tiny", device="cpu", compute_type="int8")
        return True, "faster-whisper disponible (offline)"
    except ImportError:
        return False, "faster-whisper no instalado: pip install faster-whisper"
    except Exception as e:
        return False, str(e)


def check_plugins() -> tuple[bool, str]:
    try:
        from plugins import cargar_plugins
        cargados = cargar_plugins()
        if cargados:
            return True, f"{len(cargados)} plugin(s): {', '.join(cargados)}"
        return True, "Carpeta plugins/ vacía (sin plugins instalados)"
    except Exception as e:
        return False, str(e)


def check_db() -> tuple[bool, str]:
    import sqlite3, os
    home = os.path.expanduser("~")
    db_path = os.path.join(home, ".jarvis.db")
    try:
        conn = sqlite3.connect(db_path)
        conn.execute("SELECT 1")
        conn.close()
        size = os.path.getsize(db_path) if os.path.exists(db_path) else 0
        return True, f"SQLite OK — {db_path} ({size} bytes)"
    except Exception as e:
        return False, str(e)


def check_cache() -> tuple[bool, str]:
    try:
        from cache import cache
        cache.set("__test__", "ok", ttl=10)
        val = cache.get("__test__", ttl=10)
        cache.invalidar("__test__")
        if val == "ok":
            return True, "Caché funciona correctamente"
        return False, "Caché set/get no coincide"
    except Exception as e:
        return False, str(e)


def check_perfil() -> tuple[bool, str]:
    from config import NOMBRE_USUARIO, HORARIO_TRABAJO, CIUDAD_DEFAULT, saludo_contextual
    partes = []
    if NOMBRE_USUARIO:
        partes.append(f"nombre={NOMBRE_USUARIO}")
    else:
        partes.append("nombre=no configurado (añade NOMBRE_USUARIO en .env)")
    partes.append(f"horario={HORARIO_TRABAJO}")
    partes.append(f"ciudad={CIUDAD_DEFAULT}")
    saludo = saludo_contextual()
    print(f"        {GRIS}Saludo actual: «{saludo}»{RESET}")
    return True, " · ".join(partes)


# ─── Runner principal ─────────────────────────────────────────

def ejecutar_diagnostico():
    print(f"\n{BOLD}{'='*52}")
    print(f"  🔬 JARVIS v7 — Autodiagnóstico")
    print(f"{'='*52}{RESET}")

    checks = [
        ("Ollama (IA local)",      check_ollama),
        ("Groq (IA online)",       check_groq),
        ("Gemini (IA online)",     check_gemini),
        ("OpenWeatherMap (clima)", check_clima),
        ("espeak (síntesis voz)", check_espeak),
        ("Micrófono",              check_microfono),
        ("Plugins",                check_plugins),
        ("Base de datos SQLite",   check_db),
        ("Caché",                  check_cache),
        ("Perfil de usuario",      check_perfil),
    ]

    fallos = 0
    avisos = 0

    _titulo("Verificando componentes...")

    for nombre, fn in checks:
        t0 = time.monotonic()
        try:
            resultado = fn()
        except Exception as e:
            resultado = (False, str(e))
        elapsed = time.monotonic() - t0

        ok, detalle = resultado

        if ok is True:
            estado = OK
        elif ok is None:
            estado = WARN
            avisos += 1
        else:
            estado = FAIL
            fallos += 1

        tiempo_str = f"{GRIS}[{elapsed*1000:.0f}ms]{RESET}"
        print(f"  {estado}  {nombre} {tiempo_str}")
        if detalle:
            print(f"        {GRIS}{detalle}{RESET}")

    # Resumen
    _titulo("Resumen")
    total = len(checks)
    oks = total - fallos - avisos
    print(f"  {VERDE}{oks} OK{RESET}  ·  {AMBAR}{avisos} avisos{RESET}  ·  {ROJO}{fallos} fallos{RESET}")

    if fallos == 0 and avisos == 0:
        print(f"\n  {VERDE}{BOLD}✅ Todo en orden — Jarvis listo para usar{RESET}\n")
    elif fallos == 0:
        print(f"\n  {AMBAR}⚠️  Jarvis funcional, pero revisa los avisos{RESET}\n")
    else:
        print(f"\n  {ROJO}❌ {fallos} componente(s) fallaron — revisa los mensajes arriba{RESET}\n")

    return fallos == 0
