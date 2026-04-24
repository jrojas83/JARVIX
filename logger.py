# logger.py — Jarvis v5
# Logging centralizado. Importa `log` desde cualquier módulo.
#
# Uso:
#   from logger import log
#   log.info("Jarvis iniciado")
#   log.warning("Ollama no responde")
#   log.error("Fallo al abrir app: %s", error)
#
# Los logs se guardan en ~/.jarvis.log (no se suben a Git).

import logging
import os

HOME     = os.path.expanduser("~")
LOG_FILE = os.path.join(HOME, ".jarvis.log")

# ─── Configuración del logger ─────────────────────────────────
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)-8s] %(module)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    encoding="utf-8",
)

# También mostrar WARNING+ en consola (sin ensuciar la salida normal)
_console = logging.StreamHandler()
_console.setLevel(logging.WARNING)
_console.setFormatter(logging.Formatter("   ⚠️  %(message)s"))
logging.getLogger().addHandler(_console)

log = logging.getLogger("jarvis")
