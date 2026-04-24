# recordatorios.py — Jarvis v5
# Recordatorios con SQLite (persisten entre sesiones) + notas rápidas.
# Los timers activos se restauran al iniciar si quedan pendientes.

import threading
import subprocess
import sqlite3
import os
import re
from datetime import datetime, timedelta
from logger import log

HOME    = os.path.expanduser("~")
DB_PATH = os.path.join(HOME, ".jarvis.db")

# ─── Inicialización de la base de datos ───────────────────────

def _db():
    """Devuelve una conexión con row_factory para obtener dicts."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Crea las tablas si no existen. Llamar al inicio de Jarvis."""
    with _db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS recordatorios (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                mensaje     TEXT    NOT NULL,
                hora_disparo TEXT   NOT NULL,   -- ISO 8601
                desc_tiempo TEXT    NOT NULL,
                completado  INTEGER DEFAULT 0,
                creado      TEXT    NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS notas (
                id      INTEGER PRIMARY KEY AUTOINCREMENT,
                texto   TEXT NOT NULL,
                fecha   TEXT NOT NULL
            )
        """)
    log.info("Base de datos inicializada: %s", DB_PATH)


# ─── Notificación de escritorio ───────────────────────────────

def notificar(titulo, mensaje, urgencia="normal", icono="dialog-information", duracion=5000):
    """Muestra una notificación en el escritorio con notify-send."""
    try:
        subprocess.Popen(
            ["notify-send",
             "--urgency", urgencia,
             "--icon",    icono,
             "--expire-time", str(duracion),
             titulo, mensaje],
            start_new_session=True
        )
    except FileNotFoundError:
        pass   # notify-send no instalado — la voz ya avisa
    except Exception as e:
        log.warning("notificar: %s", e)


# ─── Parser de tiempo natural ─────────────────────────────────

def _parsear_tiempo(texto):
    """
    Convierte texto natural a segundos.
    Ejemplos: '5 minutos', '1 hora', '2 horas y 30 minutos', 'media hora'
    Devuelve (segundos: int, descripcion: str) o (None, None).
    """
    texto = texto.lower().strip()
    patrones = [
        (r'(\d+)\s*hora[s]?\s*y?\s*(\d+)\s*minuto[s]?', lambda m: int(m.group(1))*3600 + int(m.group(2))*60),
        (r'(\d+)\s*hora[s]?',                             lambda m: int(m.group(1))*3600),
        (r'(\d+)\s*minuto[s]?',                           lambda m: int(m.group(1))*60),
        (r'(\d+)\s*segundo[s]?',                          lambda m: int(m.group(1))),
        (r'media\s*hora',                                 lambda m: 1800),
        (r'cuarto\s*de\s*hora',                           lambda m: 900),
    ]
    for patron, calc in patrones:
        m = re.search(patron, texto)
        if m:
            segundos = calc(m)
            partes = []
            if segundos >= 3600:
                h = segundos // 3600
                partes.append(f"{h} hora{'s' if h>1 else ''}")
            if (segundos % 3600) >= 60:
                mn = (segundos % 3600) // 60
                partes.append(f"{mn} minuto{'s' if mn>1 else ''}")
            if segundos < 60:
                partes.append(f"{segundos} segundo{'s' if segundos>1 else ''}")
            return segundos, " y ".join(partes)
    return None, None


# ─── Gestión de timers en memoria ────────────────────────────
# {id_db: threading.Timer}
_timers_activos: dict = {}


def _disparar(rid, mensaje):
    """Callback del timer: avisa por voz y notificación, marca como completado."""
    from voz import hablar
    log.info("Recordatorio #%d disparado: %s", rid, mensaje)
    hablar(f"Recordatorio: {mensaje}")
    notificar(
        "⏰ Recordatorio Jarvis",
        mensaje,
        urgencia="critical",
        icono="appointment-soon",
        duracion=0
    )
    _timers_activos.pop(rid, None)
    with _db() as conn:
        conn.execute("UPDATE recordatorios SET completado=1 WHERE id=?", (rid,))


def _armar_timer(rid, mensaje, segundos):
    """Crea y arranca un threading.Timer para el recordatorio."""
    t = threading.Timer(segundos, _disparar, args=(rid, mensaje))
    t.daemon = True
    t.start()
    _timers_activos[rid] = t
    return t


# ─── API pública: Recordatorios ───────────────────────────────

def crear_recordatorio(mensaje, tiempo_texto):
    """
    Crea un recordatorio que persiste en SQLite y dispara timer en memoria.
    Si Jarvis se reinicia antes de que dispare, restaurar_recordatorios_pendientes()
    lo recupera al inicio.
    """
    segundos, desc = _parsear_tiempo(tiempo_texto)
    if segundos is None:
        return f"No entendí el tiempo '{tiempo_texto}'. Di algo como '10 minutos' o '1 hora'."
    if segundos <= 0:
        return "El tiempo debe ser mayor que cero."
    if segundos > 86400:
        return "El tiempo máximo es 24 horas."

    hora_disparo = (datetime.now() + timedelta(seconds=segundos)).isoformat()
    creado       = datetime.now().isoformat()

    with _db() as conn:
        cur = conn.execute(
            "INSERT INTO recordatorios (mensaje, hora_disparo, desc_tiempo, creado) VALUES (?,?,?,?)",
            (mensaje, hora_disparo, desc, creado)
        )
        rid = cur.lastrowid

    _armar_timer(rid, mensaje, segundos)
    log.info("Recordatorio creado #%d: '%s' en %s", rid, mensaje, desc)
    return f"Recordatorio creado: '{mensaje}' en {desc}."


def listar_recordatorios():
    """Devuelve los recordatorios activos (no completados)."""
    with _db() as conn:
        rows = conn.execute(
            "SELECT id, mensaje, desc_tiempo FROM recordatorios WHERE completado=0 ORDER BY id"
        ).fetchall()
    if not rows:
        return "No tienes recordatorios activos."
    lineas = [f"Tienes {len(rows)} recordatorio(s) activo(s):"]
    for r in rows:
        activo = "⏱" if r["id"] in _timers_activos else "💾"
        lineas.append(f"  {activo} #{r['id']} — '{r['mensaje']}' (en {r['desc_tiempo']})")
    return "\n".join(lineas)


def cancelar_recordatorio(rid=None):
    """Cancela el recordatorio con id `rid`, o el más reciente si rid=None."""
    with _db() as conn:
        if rid is None:
            row = conn.execute(
                "SELECT id, mensaje FROM recordatorios WHERE completado=0 ORDER BY id DESC LIMIT 1"
            ).fetchone()
        else:
            row = conn.execute(
                "SELECT id, mensaje FROM recordatorios WHERE id=? AND completado=0", (rid,)
            ).fetchone()

    if not row:
        return "No hay recordatorios activos para cancelar."

    rid = row["id"]
    if rid in _timers_activos:
        _timers_activos[rid].cancel()
        del _timers_activos[rid]

    with _db() as conn:
        conn.execute("UPDATE recordatorios SET completado=1 WHERE id=?", (rid,))

    log.info("Recordatorio #%d cancelado: '%s'", rid, row["mensaje"])
    return f"Recordatorio '{row['mensaje']}' cancelado."


def restaurar_recordatorios_pendientes():
    """
    Al arrancar Jarvis: relanza timers para recordatorios que no se dispararon
    en la sesión anterior (hora_disparo en el futuro y completado=0).
    """
    ahora = datetime.now()
    with _db() as conn:
        rows = conn.execute(
            "SELECT id, mensaje, hora_disparo FROM recordatorios WHERE completado=0"
        ).fetchall()

    restaurados = 0
    for r in rows:
        try:
            hora = datetime.fromisoformat(r["hora_disparo"])
            segundos_restantes = (hora - ahora).total_seconds()
            if segundos_restantes > 0:
                _armar_timer(r["id"], r["mensaje"], segundos_restantes)
                restaurados += 1
                log.info("Recordatorio #%d restaurado (dispara en %.0fs)", r["id"], segundos_restantes)
            else:
                # Ya debería haber disparado — marcarlo como completado
                with _db() as conn:
                    conn.execute("UPDATE recordatorios SET completado=1 WHERE id=?", (r["id"],))
                log.info("Recordatorio #%d marcado completado (hora pasada)", r["id"])
        except Exception as e:
            log.warning("No se pudo restaurar recordatorio #%d: %s", r["id"], e)

    if restaurados:
        log.info("%d recordatorio(s) restaurados al arrancar", restaurados)
    return restaurados


# ─── API pública: Notas ───────────────────────────────────────

def agregar_nota(texto):
    """Guarda una nota rápida en SQLite."""
    fecha = datetime.now().strftime("%Y-%m-%d %H:%M")
    with _db() as conn:
        conn.execute("INSERT INTO notas (texto, fecha) VALUES (?,?)", (texto.strip(), fecha))
    notificar("📝 Nota guardada — Jarvis", texto, urgencia="low",
              icono="accessories-text-editor", duracion=4000)
    log.info("Nota guardada: '%s'", texto[:60])
    return f"Nota guardada: '{texto}'"


def leer_notas(cantidad=5):
    """Devuelve las últimas N notas."""
    with _db() as conn:
        total = conn.execute("SELECT COUNT(*) FROM notas").fetchone()[0]
        rows  = conn.execute(
            "SELECT texto, fecha FROM notas ORDER BY id DESC LIMIT ?", (cantidad,)
        ).fetchall()
    if not rows:
        return "No tienes notas guardadas."
    lineas = [f"Tienes {total} nota(s). Las últimas {len(rows)}:"]
    for r in rows:
        lineas.append(f"  [{r['fecha']}] {r['texto']}")
    return "\n".join(lineas)


def borrar_nota(nid=None):
    """Borra la nota con id `nid`, o la más reciente si nid=None."""
    with _db() as conn:
        if nid is None:
            row = conn.execute("SELECT id, texto FROM notas ORDER BY id DESC LIMIT 1").fetchone()
        else:
            row = conn.execute("SELECT id, texto FROM notas WHERE id=?", (nid,)).fetchone()
        if not row:
            return "No hay notas para borrar."
        conn.execute("DELETE FROM notas WHERE id=?", (row["id"],))
    log.info("Nota #%d eliminada: '%s'", row["id"], row["texto"][:60])
    return f"Nota eliminada: '{row['texto']}'"


def buscar_en_notas(termino):
    """Busca notas que contengan el término (insensible a mayúsculas)."""
    with _db() as conn:
        rows = conn.execute(
            "SELECT texto, fecha FROM notas WHERE LOWER(texto) LIKE ? ORDER BY id DESC LIMIT 5",
            (f"%{termino.lower()}%",)
        ).fetchall()
    if not rows:
        return f"No encontré notas con '{termino}'."
    lineas = [f"Encontré {len(rows)} nota(s) con '{termino}':"]
    for r in rows:
        lineas.append(f"  [{r['fecha']}] {r['texto']}")
    return "\n".join(lineas)
