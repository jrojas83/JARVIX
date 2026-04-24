# plugins/agua.py — Plugin de ejemplo para Jarvis v7
# Recordatorio proactivo de hidratación durante el trabajo.
# Usa threading para no bloquear el bucle principal de Jarvis.
#
# Comandos:
#   "activa recordatorio de agua"  → cada 90 minutos te recuerda beber agua
#   "desactiva recordatorio de agua"
#   "estado recordatorio de agua"

import threading
import time
import subprocess
from logger import log

NOMBRE      = "agua"
DESCRIPCION = "Recordatorio proactivo de hidratación cada N minutos"
ACCION      = "agua"

PATRONES = [
    "recordatorio de agua",
    "recordarme beber agua",
    "recuérdame beber agua",
    "recuerdame beber agua",
    "hidratación",
    "hidratacion",
]

_INTERVALO_MINUTOS = 90
_timer_activo: threading.Event | None = None
_hilo: threading.Thread | None = None


def _bucle_recordatorio(stop_event: threading.Event, intervalo_min: int):
    log.info("Plugin agua: recordatorio activo cada %d minutos", intervalo_min)
    while not stop_event.wait(timeout=intervalo_min * 60):
        subprocess.run(
            ["notify-send", "💧 Hidratación", f"Llevas {intervalo_min} min trabajando. ¡Bebe agua!",
             "--urgency=normal", "--expire-time=8000"],
            capture_output=True
        )
        # También intentar hablar si espeak está disponible
        try:
            subprocess.Popen(["espeak", "-v", "es+m3", "-s", "140",
                              "Recuerda beber agua"],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except FileNotFoundError:
            pass
        log.info("Plugin agua: recordatorio enviado")


def ejecutar(orden: str, params: dict) -> str:
    global _timer_activo, _hilo
    o = orden.lower()

    if any(p in o for p in ["desactiva", "para", "detén", "deten", "apaga"]):
        if _timer_activo and not _timer_activo.is_set():
            _timer_activo.set()
            return "Recordatorio de hidratación desactivado"
        return "El recordatorio de agua no estaba activo"

    if any(p in o for p in ["estado", "activo", "está activo", "esta activo"]):
        if _timer_activo and not _timer_activo.is_set():
            return f"Recordatorio de agua activo (cada {_INTERVALO_MINUTOS} minutos)"
        return "Recordatorio de agua inactivo"

    # Activar
    if _timer_activo and not _timer_activo.is_set():
        return f"El recordatorio de agua ya está activo (cada {_INTERVALO_MINUTOS} minutos)"

    _timer_activo = threading.Event()
    _hilo = threading.Thread(
        target=_bucle_recordatorio,
        args=(_timer_activo, _INTERVALO_MINUTOS),
        daemon=True,
        name="agua-reminder"
    )
    _hilo.start()
    return f"Recordatorio de hidratación activado: cada {_INTERVALO_MINUTOS} minutos te aviso"
