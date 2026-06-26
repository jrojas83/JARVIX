# jarvis_core/memory/episodic_memory.py — Memoria episódica de eventos
# ================================================================================
# Registra eventos de actividad del usuario para responder preguntas como:
#   - "¿qué hice hoy?"
#   - "¿qué hice ayer?"
#   - "¿cuándo usé VSCode por última vez?"
#   - "dame un resumen del día"
#
# Usa SQLite para almacenar eventos con timestamp, tipo, app y descripción.

import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from logger import log


def _default_db_path() -> str:
    """Ruta por defecto de la base de datos."""
    return str(Path.home() / ".jarvis.db")


def _get_connection() -> sqlite3.Connection:
    """Obtiene una conexión a la base de datos."""
    conn = sqlite3.connect(_default_db_path())
    conn.row_factory = sqlite3.Row
    return conn


def inicializar_tabla() -> bool:
    """Crea las tablas necesarias si no existen."""
    try:
        conn = _get_connection()
        cursor = conn.cursor()
        
        # Tabla de eventos
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS eventos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL DEFAULT (datetime('now','localtime')),
                tipo TEXT NOT NULL,
                app TEXT,
                descripcion TEXT,
                duracion_seg INTEGER
            )
        """)
        
        # Índices para consultas rápidas
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_eventos_timestamp ON eventos (timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_eventos_tipo ON eventos (tipo)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_eventos_app ON eventos (app)")
        
        conn.commit()
        conn.close()
        log.info("[MEMORIA EPISÓDICA] Tablas inicializadas correctamente")
        return True
    except Exception as e:
        log.warning("[MEMORIA EPISÓDICA] Error inicializando tablas: %s", e)
        return False


def registrar(tipo: str, descripcion: str, app: Optional[str] = None, duracion_seg: Optional[int] = None) -> bool:
    """
    Registra un evento en la memoria episódica.
    
    Args:
        tipo: Tipo de evento (ej: "orden_recibida", "app_abierta", "rutina_disparada")
        descripcion: Descripción del evento
        app: Aplicación relacionada (opcional)
        duracion_seg: Duración en segundos (opcional)
    
    Returns:
        True si se registró correctamente
    """
    try:
        conn = _get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO eventos (tipo, app, descripcion, duracion_seg)
            VALUES (?, ?, ?, ?)
        """, (tipo, app, descripcion, duracion_seg))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        log.warning("[MEMORIA EPISÓDICA] Error registrando evento: %s", e)
        return False


def que_hice_hoy() -> List[Dict[str, Any]]:
    """
    Obtiene todos los eventos de hoy.
    
    Returns:
        Lista de eventos ocurridos hoy
    """
    try:
        conn = _get_connection()
        cursor = conn.cursor()
        
        hoy = datetime.now().strftime("%Y-%m-%d")
        
        cursor.execute("""
            SELECT id, timestamp, tipo, app, descripcion, duracion_seg
            FROM eventos
            WHERE date(timestamp) = date(?)
            ORDER BY timestamp DESC
        """, (hoy,))
        
        eventos = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return eventos
    except Exception as e:
        log.warning("[MEMORIA EPISÓDICA] Error consultando eventos de hoy: %s", e)
        return []


def que_hice_ayer() -> List[Dict[str, Any]]:
    """
    Obtiene todos los eventos de ayer.
    
    Returns:
        Lista de eventos ocurridos ayer
    """
    try:
        conn = _get_connection()
        cursor = conn.cursor()
        
        ayer = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        
        cursor.execute("""
            SELECT id, timestamp, tipo, app, descripcion, duracion_seg
            FROM eventos
            WHERE date(timestamp) = date(?)
            ORDER BY timestamp DESC
        """, (ayer,))
        
        eventos = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return eventos
    except Exception as e:
        log.warning("[MEMORIA EPISÓDICA] Error consultando eventos de ayer: %s", e)
        return []


def resumen_del_dia(fecha: Optional[str] = None) -> str:
    """
    Genera un resumen en lenguaje natural de los eventos de un día.
    
    Args:
        fecha: Fecha en formato YYYY-MM-DD (por defecto, hoy)
    
    Returns:
        Resumen en texto plano
    """
    try:
        conn = _get_connection()
        cursor = conn.cursor()
        
        if fecha is None:
            fecha = datetime.now().strftime("%Y-%m-%d")
        
        cursor.execute("""
            SELECT tipo, app, COUNT(*) as cantidad
            FROM eventos
            WHERE date(timestamp) = date(?)
            GROUP BY tipo, app
            ORDER BY cantidad DESC
        """, (fecha,))
        
        resultados = cursor.fetchall()
        conn.close()
        
        if not resultados:
            return "No hay registros de actividad para ese día."
        
        lineas = []
        for row in resultados:
            tipo = row["tipo"]
            app = row["app"]
            cantidad = row["cantidad"]
            
            if app:
                lineas.append(f"{cantidad} {tipo}(s) relacionado(s) con {app}")
            else:
                lineas.append(f"{cantidad} {tipo}(s)")
        
        fecha_legible = datetime.strptime(fecha, "%Y-%m-%d").strftime("%d/%m/%Y")
        return f"Resumen del {fecha_legible}:\n" + "\n".join(lineas)
    
    except Exception as e:
        log.warning("[MEMORIA EPISÓDICA] Error generando resumen: %s", e)
        return "No pude generar el resumen del día."


def ultima_vez_que_use(app_o_tipo: str) -> Optional[Dict[str, Any]]:
    """
    Busca la última vez que se usó una app o tipo de evento.
    
    Args:
        app_o_tipo: Nombre de la app o tipo de evento
    
    Returns:
        El evento más reciente o None si no se encuentra
    """
    try:
        conn = _get_connection()
        cursor = conn.cursor()
        
        # Buscar primero por app
        cursor.execute("""
            SELECT id, timestamp, tipo, app, descripcion, duracion_seg
            FROM eventos
            WHERE app LIKE ? OR tipo LIKE ?
            ORDER BY timestamp DESC
            LIMIT 1
        """, (f"%{app_o_tipo}%", f"%{app_o_tipo}%"))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return dict(row)
        return None
    
    except Exception as e:
        log.warning("[MEMORIA EPISÓDICA] Error buscando última vez: %s", e)
        return None


def limpiar_antiguos(dias: int = 30) -> int:
    """
    Elimina eventos más antiguos que N días.
    
    Args:
        dias: Número de días a conservar
    
    Returns:
        Cantidad de eventos eliminados
    """
    try:
        conn = _get_connection()
        cursor = conn.cursor()
        
        fecha_limite = (datetime.now() - timedelta(days=dias)).strftime("%Y-%m-%d")
        
        cursor.execute("""
            DELETE FROM eventos
            WHERE date(timestamp) < date(?)
        """, (fecha_limite,))
        
        eliminados = cursor.rowcount
        conn.commit()
        conn.close()
        
        log.info("[MEMORIA EPISÓDICA] Se eliminaron %d eventos antiguos", eliminados)
        return eliminados
    
    except Exception as e:
        log.warning("[MEMORIA EPISÓDICA] Error limpiando eventos antiguos: %s", e)
        return 0


def obtener_actividad_reciente(minutos: int = 60) -> List[Dict[str, Any]]:
    """
    Obtiene eventos de los últimos N minutos.
    
    Args:
        minutos: Ventana de tiempo en minutos
    
    Returns:
        Lista de eventos recientes
    """
    try:
        conn = _get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, timestamp, tipo, app, descripcion, duracion_seg
            FROM eventos
            WHERE timestamp >= datetime('now', 'localtime', ? || ' minutes')
            ORDER BY timestamp DESC
        """, (-minutos,))
        
        eventos = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return eventos
    
    except Exception as e:
        log.warning("[MEMORIA EPISÓDICA] Error consultando actividad reciente: %s", e)
        return []


def hay_actividad_en_ventana(minutos: int = 30) -> bool:
    """
    Verifica si hubo actividad en los últimos N minutos.
    
    Args:
        minutos: Ventana de tiempo en minutos
    
    Returns:
        True si hubo actividad
    """
    eventos = obtener_actividad_reciente(minutos)
    return len(eventos) > 0
