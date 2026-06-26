"""
JARVIX — Memoria episódica
Registra eventos de actividad en ~/.jarvis.db y permite consultarlos
en lenguaje natural.
"""

import sqlite3
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

DB_PATH = Path.home() / ".jarvis.db"


def _conn() -> sqlite3.Connection:
    return sqlite3.connect(DB_PATH)


def inicializar_tabla():
    """Crea la tabla si no existe. Seguro llamar múltiples veces."""
    with _conn() as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS eventos (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp   TEXT    NOT NULL DEFAULT (datetime('now','localtime')),
                tipo        TEXT    NOT NULL,
                app         TEXT,
                descripcion TEXT,
                duracion_seg INTEGER
            )
        """)
        con.execute("""
            CREATE INDEX IF NOT EXISTS idx_eventos_timestamp
            ON eventos (timestamp)
        """)
        con.execute("""
            CREATE INDEX IF NOT EXISTS idx_eventos_tipo
            ON eventos (tipo)
        """)


def registrar(tipo: str, descripcion: str = "", app: str = "", duracion_seg: int = 0):
    """
    Guarda un evento. Llamar desde cualquier parte de JARVIX.

    Tipos recomendados:
        'orden_recibida'   — el usuario habló o escribió algo
        'app_abierta'      — se abrió una aplicación
        'rutina_disparada' — el motor de autonomía disparó una rutina
        'modo_activado'    — se activó un modo (trabajo, sueño, etc.)
        'recordatorio'     — se disparó un recordatorio
        'ocr_ejecutado'    — se leyó la pantalla
    """
    with _conn() as con:
        con.execute(
            "INSERT INTO eventos (tipo, app, descripcion, duracion_seg) VALUES (?,?,?,?)",
            (tipo, app, descripcion[:500], duracion_seg),
        )


# ── Consultas ─────────────────────────────────────────────────────────────────

def _filas_a_texto(filas: list, limite: int = 15) -> str:
    if not filas:
        return "No encontré registros para ese período."
    lineas = []
    for ts, tipo, app, desc in filas[:limite]:
        hora = ts[11:16]  # HH:MM
        partes = [hora, tipo]
        if app:
            partes.append(app)
        if desc:
            partes.append(desc[:60])
        lineas.append("  " + " | ".join(partes))
    if len(filas) > limite:
        lineas.append(f"  ... y {len(filas)-limite} eventos más.")
    return "\n".join(lineas)


def que_hice_hoy() -> str:
    with _conn() as con:
        filas = con.execute("""
            SELECT timestamp, tipo, app, descripcion
            FROM eventos
            WHERE date(timestamp) = date('now','localtime')
            ORDER BY timestamp
        """).fetchall()
    if not filas:
        return "No tengo registros de actividad de hoy todavía."
    return f"Actividad de hoy ({len(filas)} eventos):\n" + _filas_a_texto(filas)


def que_hice_ayer() -> str:
    with _conn() as con:
        filas = con.execute("""
            SELECT timestamp, tipo, app, descripcion
            FROM eventos
            WHERE date(timestamp) = date('now','localtime','-1 day')
            ORDER BY timestamp
        """).fetchall()
    if not filas:
        return "No tengo registros de ayer."
    return f"Actividad de ayer ({len(filas)} eventos):\n" + _filas_a_texto(filas)


def resumen_del_dia(fecha: Optional[str] = None) -> str:
    """
    Genera un resumen legible del día. fecha en formato 'YYYY-MM-DD'.
    Si no se pasa fecha, usa hoy.
    """
    if not fecha:
        fecha = datetime.now().strftime("%Y-%m-%d")

    with _conn() as con:
        # Conteo por tipo
        conteo = con.execute("""
            SELECT tipo, COUNT(*) as n
            FROM eventos
            WHERE date(timestamp) = ?
            GROUP BY tipo
            ORDER BY n DESC
        """, (fecha,)).fetchall()

        # Apps más usadas
        apps = con.execute("""
            SELECT app, COUNT(*) as n
            FROM eventos
            WHERE date(timestamp) = ? AND app != ''
            GROUP BY app
            ORDER BY n DESC
            LIMIT 5
        """, (fecha,)).fetchall()

    if not conteo:
        return f"Sin registros para el {fecha}."

    lineas = [f"Resumen del {fecha}:"]
    for tipo, n in conteo:
        lineas.append(f"  {tipo}: {n} veces")
    if apps:
        lineas.append("Apps más usadas:")
        for app, n in apps:
            lineas.append(f"  {app}: {n} veces")
    return "\n".join(lineas)


def ultima_vez_que_use(app_o_tipo: str) -> str:
    """¿Cuándo fue la última vez que abrí X?"""
    with _conn() as con:
        fila = con.execute("""
            SELECT timestamp, tipo, descripcion
            FROM eventos
            WHERE app LIKE ? OR descripcion LIKE ?
            ORDER BY timestamp DESC
            LIMIT 1
        """, (f"%{app_o_tipo}%", f"%{app_o_tipo}%")).fetchone()

    if not fila:
        return f"No encontré registros de '{app_o_tipo}'."
    ts, tipo, desc = fila
    return f"La última vez fue el {ts[:16]} ({tipo}): {desc[:80]}"


def limpiar_antiguos(dias: int = 30):
    """Elimina eventos más viejos que N días."""
    with _conn() as con:
        resultado = con.execute("""
            DELETE FROM eventos
            WHERE timestamp < datetime('now','localtime', ? || ' days')
        """, (f"-{dias}",))
        return f"Eliminados {resultado.rowcount} eventos de más de {dias} días."
