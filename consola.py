# consola.py — Jarvis v7
# Utilidades de consola: colores ANSI y métricas de tiempo.
# Sin dependencias externas (no necesita colorama).
#
# Uso:
#   from consola import imprimir_respuesta, imprimir_estado, cronometro
#
#   with cronometro("Groq") as c:
#       respuesta = preguntar_online(orden)
#   imprimir_respuesta(respuesta, fuente=c.fuente, ms=c.ms)

import time
from contextlib import contextmanager
from datetime import datetime

# ─── Colores ANSI ─────────────────────────────────────────────
RESET  = "\033[0m"
BOLD   = "\033[1m"
DIM    = "\033[2m"

# Texto
BLANCO  = "\033[97m"
GRIS    = "\033[90m"
VERDE   = "\033[92m"
AMBAR   = "\033[93m"
ROJO    = "\033[91m"
CYAN    = "\033[96m"
AZUL    = "\033[94m"
MAGENTA = "\033[95m"

# Colores por fuente de IA
_COLORES_FUENTE = {
    "groq":       CYAN,
    "gemini":     VERDE,
    "anthropic":  MAGENTA,
    "ollama":     AMBAR,
    "cache":      AZUL,
    "patron":     GRIS,   # respuesta por patrón directo (sin IA)
    "plugin":     VERDE,
    "conversacion": BLANCO,  # conversación proactiva
}


def _color_fuente(fuente: str) -> str:
    return _COLORES_FUENTE.get(fuente.lower(), BLANCO)


def _timestamp() -> str:
    return datetime.now().strftime("%H:%M:%S")


# ─── Cronómetro contextual ────────────────────────────────────

class _Cronometro:
    def __init__(self, fuente: str):
        self.fuente = fuente
        self.ms     = 0
        self._t0    = None

    def __enter__(self):
        self._t0 = time.monotonic()
        return self

    def __exit__(self, *_):
        self.ms = int((time.monotonic() - self._t0) * 1000)


def cronometro(fuente: str) -> _Cronometro:
    """Cronómetro de contexto. Uso: with cronometro('Groq') as c: ..."""
    return _Cronometro(fuente)


# ─── Impresoras de consola ────────────────────────────────────

def imprimir_orden(orden: str):
    """Imprime la orden del usuario con prefijo."""
    ts = _timestamp()
    print(f"\n{DIM}{ts}{RESET}  {BOLD}Tú ›{RESET} {orden}")


def imprimir_respuesta(texto: str, fuente: str = "jarvis", ms: int = 0):
    """
    Imprime la respuesta de Jarvis con color según fuente y tiempo.
    fuente: groq | gemini | anthropic | ollama | cache | patron | plugin
    """
    if not texto:
        return
    color = _color_fuente(fuente)
    ts    = _timestamp()

    # Badge de fuente + tiempo
    if ms > 0:
        badge = f"{color}[{fuente.upper()} {ms}ms]{RESET}"
    elif fuente == "cache":
        badge = f"{AZUL}[CACHÉ]{RESET}"
    elif fuente == "patron":
        badge = f"{GRIS}[PATRÓN]{RESET}"
    elif fuente == "plugin":
        badge = f"{VERDE}[PLUGIN]{RESET}"
    else:
        badge = f"{color}[{fuente.upper()}]{RESET}"

    print(f"{DIM}{ts}{RESET}  {BOLD}Jarvis ›{RESET} {badge} {texto}")


def imprimir_estado(mensaje: str, tipo: str = "info"):
    """
    Imprime mensajes de estado del sistema.
    tipo: info | ok | warn | error
    """
    iconos = {
        "info":  f"{CYAN}ℹ{RESET}",
        "ok":    f"{VERDE}✓{RESET}",
        "warn":  f"{AMBAR}⚠{RESET}",
        "error": f"{ROJO}✗{RESET}",
    }
    icono = iconos.get(tipo, "·")
    print(f"  {icono}  {DIM}{mensaje}{RESET}")


def imprimir_banner(version: str = "7", modo: str = "texto",
                    ia_local: bool = False, nombre_usuario: str = ""):
    """Banner de inicio personalizado."""
    saludo = f" — Hola, {nombre_usuario}" if nombre_usuario else ""
    print(f"\n{BOLD}{'═'*52}")
    print(f"  🤖 JARVIS v{version}{saludo}")
    print(f"{'═'*52}{RESET}")
    modo_str = {
        "texto":  "TEXTO  (usa --voz o --espera para voz)",
        "voz":    "VOZ CONTINUA",
        "espera": "ESPERA (di 'jarvis' para activar)",
    }.get(modo, modo.upper())
    print(f"  Modo: {modo_str}")
    ia_str = f"{VERDE}✅ activa{RESET}" if ia_local else f"{GRIS}⚪ no configurada{RESET}"
    print(f"  IA local (Ollama): {ia_str}")
    print(f"  {DIM}'test' para diagnóstico · 'ayuda' para comandos{RESET}\n")
