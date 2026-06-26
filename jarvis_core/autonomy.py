"""
jarvis_core/autonomy.py  — Motor de autonomía proactiva para JARVIX
====================================================================
100% OFFLINE. Sin APIs externas. Sin anthropic. Sin internet.

Cómo funciona:
  - Corre en un hilo daemon (no bloquea el bucle principal de jarvis.py)
  - Se comunica con jarvis.py mediante una cola thread-safe (queue.Queue)
  - jarvis.py saca mensajes de esa cola en su bucle y los habla con hablar()

Integración — 3 cambios en jarvis.py (ver INTEGRACION.md):
  from jarvis_core.autonomy import AutonomyEngine, cola_autonomia
"""

import json
import logging
import queue
import subprocess
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path

log = logging.getLogger("jarvis.autonomy")

# ─────────────────────────────────────────────────────────────
# Cola compartida con jarvis.py
# jarvis.py lee de esta cola en su bucle principal con:
#   while not cola_autonomia.empty():
#       msg = cola_autonomia.get_nowait()
#       hablar(msg)
# ─────────────────────────────────────────────────────────────
cola_autonomia: queue.Queue = queue.Queue()

MEMORIA_FILE = Path.home() / ".jarvis_memory.json"

_DIAS_ES = {
    "monday": "lunes", "tuesday": "martes", "wednesday": "miércoles",
    "thursday": "jueves", "friday": "viernes",
    "saturday": "sábado", "sunday": "domingo",
}

RUTINAS_DEFAULT = [
    {
        "id": "buenos_dias",
        "desc": "Saludo matutino",
        "hora": "08:00",
        "dias": ["lunes", "martes", "miércoles", "jueves", "viernes"],
        "mensaje": "Buenos días. ¿Listo para empezar el día? Dime qué necesitas.",
        "activa": True,
    },
    {
        "id": "check_tarde",
        "desc": "Check-in de tarde",
        "hora": "15:00",
        "dias": ["lunes", "martes", "miércoles", "jueves", "viernes"],
        "mensaje": "¿Cómo va el día? ¿Necesitas ayuda con algo?",
        "activa": False,
    },
    {
        "id": "cierre_dia",
        "desc": "Cierre del día",
        "hora": "20:00",
        "dias": ["lunes", "martes", "miércoles", "jueves", "viernes"],
        "mensaje": "Hora de cerrar el día. ¿Lograste lo que tenías planeado?",
        "activa": False,
    },
]


class AutonomyEngine:
    """
    Motor de autonomía proactiva. Se lanza con .start() y corre en background.

    Parámetros
    ----------
    inactividad_min : minutos sin interacción para alertar (0 = desactivado)
    check_seg       : frecuencia de revisión en segundos (default 60)
    notif_desktop   : usar notify-send además de voz (requiere libnotify)
    """

    def __init__(self, inactividad_min: int = 60, check_seg: int = 60,
                 notif_desktop: bool = True):
        self.inactividad_min = inactividad_min
        self.check_seg = check_seg
        self.notif_desktop = notif_desktop

        self._ultimo_usuario: float = time.time()
        self._disparadas: set = set()
        self._alerta_inac: bool = False
        self._activo: bool = False

    def start(self):
        """Inicia el motor en un hilo daemon."""
        self._activo = True
        t = threading.Thread(target=self._loop, name="jarvis-autonomy", daemon=True)
        t.start()
        log.info("[AUTONOMY] Motor iniciado — inactividad=%dmin check=%ds",
                 self.inactividad_min, self.check_seg)

    def stop(self):
        self._activo = False

    def registrar_interaccion(self):
        """Llamar cada vez que el usuario envía un mensaje."""
        self._ultimo_usuario = time.time()
        self._alerta_inac = False

    # ── Gestión de rutinas ───────────────────────────────────

    def listar_rutinas(self) -> str:
        rutinas = self._leer_rutinas()
        lineas = ["Rutinas configuradas:"]
        for r in rutinas:
            est = "✅" if r.get("activa") else "⬜"
            lineas.append(f"  {est} [{r['id']}] {r['hora']} — {r['desc']}")
        return "\n".join(lineas)

    def activar_rutina(self, rid: str) -> str:
        return self._toggle(rid, True)

    def desactivar_rutina(self, rid: str) -> str:
        return self._toggle(rid, False)

    def agregar_rutina(self, id: str, desc: str, hora: str,
                       dias: list, mensaje: str) -> str:
        rutinas = self._leer_rutinas()
        rutinas = [r for r in rutinas if r["id"] != id]
        rutinas.append({"id": id, "desc": desc, "hora": hora,
                        "dias": dias, "mensaje": mensaje, "activa": True})
        self._guardar_rutinas(rutinas)
        return f"Rutina '{desc}' agregada para las {hora}."

    # ── Bucle interno ────────────────────────────────────────

    def _loop(self):
        while self._activo:
            try:
                self._check_rutinas()
                self._check_inactividad()
            except Exception as e:
                log.error("[AUTONOMY] Error: %s", e, exc_info=True)
            time.sleep(self.check_seg)

    def _check_rutinas(self):
        now = datetime.now()
        hora = now.strftime("%H:%M")
        dia = _DIAS_ES.get(now.strftime("%A").lower(), "")

        for r in self._leer_rutinas():
            if not r.get("activa"):
                continue
            if hora != r.get("hora", ""):
                continue
            if dia not in r.get("dias", []):
                continue

            clave = f"{r['id']}_{now.strftime('%Y%m%d%H%M')}"
            if clave in self._disparadas:
                continue

            self._disparadas.add(clave)
            ayer = (now - timedelta(days=2)).strftime("%Y%m%d")
            self._disparadas = {k for k in self._disparadas if k[-12:-4] >= ayer}

            log.info("[AUTONOMY] Rutina disparada: %s", r["id"])
            
            # Registrar evento en memoria episódica
            from jarvis_core import episodic_memory as em
            em.registrar("rutina_disparada", descripcion=r.get('id', ''))
            
            self._emitir(r.get("mensaje", r["desc"]))

    def _check_inactividad(self):
        if self.inactividad_min <= 0:
            return
        mins = int((time.time() - self._ultimo_usuario) / 60)
        if mins >= self.inactividad_min and not self._alerta_inac:
            self._alerta_inac = True
            self._emitir(f"Llevas {mins} minutos sin actividad. ¿Todo bien?")
            log.info("[AUTONOMY] Inactividad: %d min", mins)

    def _emitir(self, msg: str):
        cola_autonomia.put(msg)
        if self.notif_desktop:
            try:
                subprocess.Popen(
                    ["notify-send", "JARVIX", msg,
                     "--icon=dialog-information", "--expire-time=8000"],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )
            except FileNotFoundError:
                pass

    # ── Persistencia ─────────────────────────────────────────

    def _leer_rutinas(self) -> list:
        try:
            if MEMORIA_FILE.exists():
                with open(MEMORIA_FILE, "r") as f:
                    data = json.load(f)
                mem = data.get("rutinas", [])
                ids = {r["id"] for r in mem}
                for r in RUTINAS_DEFAULT:
                    if r["id"] not in ids:
                        mem.append(r)
                return mem
        except Exception as e:
            log.warning("[AUTONOMY] Error leyendo memoria: %s", e)
        return list(RUTINAS_DEFAULT)

    def _guardar_rutinas(self, rutinas: list):
        try:
            data = {}
            if MEMORIA_FILE.exists():
                with open(MEMORIA_FILE, "r") as f:
                    data = json.load(f)
            data["rutinas"] = rutinas
            with open(MEMORIA_FILE, "w") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            log.warning("[AUTONOMY] Error guardando: %s", e)

    def _toggle(self, rid: str, estado: bool) -> str:
        rutinas = self._leer_rutinas()
        for r in rutinas:
            if r["id"] == rid:
                r["activa"] = estado
                self._guardar_rutinas(rutinas)
                return f"Rutina '{r['desc']}' {'activada' if estado else 'desactivada'}."
        return f"No encontré la rutina '{rid}'."
