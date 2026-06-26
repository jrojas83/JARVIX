# jarvis_core/memory/people_memory.py — Memoria de personas
# ================================================================================
# Gestiona información sobre personas importantes para el usuario:
#   - Nombres, relaciones, cumpleaños
#   - Gustos y notas personales
#   - Consultas contextuales en conversación
#
# Usa SQLite para almacenar la información de forma persistente.

import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

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
    """Crea la tabla de personas si no existe."""
    try:
        conn = _get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS personas (
                nombre TEXT PRIMARY KEY,
                relacion TEXT,
                cumpleanos TEXT,
                gustos TEXT,
                notas TEXT,
                actualizado TEXT DEFAULT (datetime('now','localtime'))
            )
        """)
        
        conn.commit()
        conn.close()
        log.info("[MEMORIA PERSONAS] Tabla inicializada correctamente")
        return True
    except Exception as e:
        log.warning("[MEMORIA PERSONAS] Error inicializando tabla: %s", e)
        return False


def guardar_persona(
    nombre: str,
    relacion: Optional[str] = None,
    cumpleanos: Optional[str] = None,
    gustos: Optional[List[str]] = None,
    notas: Optional[str] = None
) -> Tuple[bool, str]:
    """
    Guarda o actualiza información de una persona.
    
    Args:
        nombre: Nombre de la persona
        relacion: Relación con el usuario (ej: "mamá", "amigo", "colega")
        cumpleanos: Fecha de cumpleaños (formato YYYY-MM-DD o MM-DD)
        gustos: Lista de gustos/preferencias
        notas: Notas adicionales
    
    Returns:
        (exitoso, mensaje)
    """
    try:
        conn = _get_connection()
        cursor = conn.cursor()
        
        # Verificar si ya existe
        cursor.execute("SELECT nombre FROM personas WHERE LOWER(nombre) = LOWER(?)", (nombre,))
        existente = cursor.fetchone()
        
        if existente:
            # Actualizar
            cursor.execute("""
                UPDATE personas SET
                    relacion = COALESCE(?, relacion),
                    cumpleanos = COALESCE(?, cumpleanos),
                    gustos = COALESCE(?, gustos),
                    notas = COALESCE(?, notas),
                    actualizado = datetime('now','localtime')
                WHERE LOWER(nombre) = LOWER(?)
            """, (relacion, cumpleanos, 
                  ",".join(gustos) if gustos else None, 
                  notas, nombre))
            msg = f"Actualicé los datos de {nombre}"
        else:
            # Insertar nuevo
            cursor.execute("""
                INSERT INTO personas (nombre, relacion, cumpleanos, gustos, notas)
                VALUES (?, ?, ?, ?, ?)
            """, (nombre, relacion, cumpleanos,
                  ",".join(gustos) if gustos else None,
                  notas))
            msg = f"Guardé que {nombre} es tu {relacion or 'contacto'}"
        
        conn.commit()
        conn.close()
        log.info("[MEMORIA PERSONAS] %s", msg)
        return True, msg
    
    except Exception as e:
        log.warning("[MEMORIA PERSONAS] Error guardando persona: %s", e)
        return False, f"Error guardando información: {e}"


def obtener_persona(nombre: str) -> Optional[Dict[str, Any]]:
    """
    Obtiene información de una persona por nombre.
    
    Args:
        nombre: Nombre de la persona
    
    Returns:
        Diccionario con la información o None si no existe
    """
    try:
        conn = _get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT nombre, relacion, cumpleanos, gustos, notas, actualizado
            FROM personas
            WHERE LOWER(nombre) = LOWER(?)
        """, (nombre,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            data = dict(row)
            # Parsear gustos de string a lista
            if data.get("gustos"):
                data["gustos"] = data["gustos"].split(",")
            return data
        return None
    
    except Exception as e:
        log.warning("[MEMORIA PERSONAS] Error obteniendo persona: %s", e)
        return None


def buscar_por_relacion(relacion: str) -> List[Dict[str, Any]]:
    """
    Busca personas por relación.
    
    Args:
        relacion: Tipo de relación (ej: "mamá", "amigo")
    
    Returns:
        Lista de personas con esa relación
    """
    try:
        conn = _get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT nombre, relacion, cumpleanos, gustos, notas
            FROM personas
            WHERE LOWER(relacion) LIKE LOWER(?)
        """, (f"%{relacion}%",))
        
        resultados = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        # Parsear gustos
        for p in resultados:
            if p.get("gustos"):
                p["gustos"] = p["gustos"].split(",")
        
        return resultados
    
    except Exception as e:
        log.warning("[MEMORIA PERSONAS] Error buscando por relación: %s", e)
        return []


def proximos_cumpleanos(dias: int = 3) -> List[Dict[str, Any]]:
    """
    Obtiene personas con cumpleaños en los próximos N días.
    
    Args:
        dias: Cantidad de días a mirar hacia adelante
    
    Returns:
        Lista de personas con cumpleaños próximo
    """
    try:
        conn = _get_connection()
        cursor = conn.cursor()
        
        hoy = datetime.now()
        fechas_busqueda = []
        
        for i in range(dias + 1):
            fecha = hoy + timedelta(days=i)
            fechas_busqueda.append(fecha.strftime("%m-%d"))
        
        placeholders = ",".join("?" * len(fechas_busqueda))
        
        cursor.execute(f"""
            SELECT nombre, relacion, cumpleanos, gustos, notas
            FROM personas
            WHERE strftime('%m-%d', cumpleanos) IN ({placeholders})
        """, fechas_busqueda)
        
        resultados = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        # Parsear gustos
        for p in resultados:
            if p.get("gustos"):
                p["gustos"] = p["gustos"].split(",")
        
        return resultados
    
    except Exception as e:
        log.warning("[MEMORIA PERSONAS] Error buscando cumpleaños: %s", e)
        return []


def obtener_contexto_personas(nombres_mencionados: List[str]) -> str:
    """
    Obtiene contexto compacto de personas mencionadas para incluir en el prompt.
    
    Args:
        nombres_mencionados: Lista de nombres detectados en la conversación
    
    Returns:
        Texto compacto con información relevante
    """
    if not nombres_mencionados:
        return ""
    
    contextos = []
    
    for nombre in nombres_mencionados[:3]:  # Máximo 3 personas
        info = obtener_persona(nombre)
        if info:
            partes = []
            
            if info.get("relacion"):
                partes.append(f"{info['relacion']} de Juan")
            
            if info.get("cumpleanos"):
                partes.append(f"cumpleaños: {info['cumpleanos']}")
            
            if info.get("gustos"):
                gustos_str = ", ".join(info["gustos"][:3])
                partes.append(f"le gusta: {gustos_str}")
            
            if partes:
                contextos.append(f"{nombre}: {'; '.join(partes)}")
    
    if contextos:
        return "Contexto de personas: " + " | ".join(contextos)
    return ""


def listar_todas() -> List[Dict[str, Any]]:
    """
    Lista todas las personas guardadas.
    
    Returns:
        Lista completa de personas
    """
    try:
        conn = _get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT nombre, relacion, cumpleanos, gustos, notas, actualizado
            FROM personas
            ORDER BY nombre
        """)
        
        resultados = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        # Parsear gustos
        for p in resultados:
            if p.get("gustos"):
                p["gustos"] = p["gustos"].split(",")
        
        return resultados
    
    except Exception as e:
        log.warning("[MEMORIA PERSONAS] Error listando personas: %s", e)
        return []


def eliminar_persona(nombre: str) -> Tuple[bool, str]:
    """
    Elimina una persona de la memoria.
    
    Args:
        nombre: Nombre de la persona a eliminar
    
    Returns:
        (exitoso, mensaje)
    """
    try:
        conn = _get_connection()
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM personas WHERE LOWER(nombre) = LOWER(?)", (nombre,))
        
        if cursor.rowcount > 0:
            conn.commit()
            conn.close()
            log.info("[MEMORIA PERSONAS] Eliminada: %s", nombre)
            return True, f"Eliminé a {nombre} de mi memoria"
        else:
            conn.close()
            return False, f"No encontré a {nombre} en mi memoria"
    
    except Exception as e:
        log.warning("[MEMORIA PERSONAS] Error eliminando persona: %s", e)
        return False, f"Error eliminando: {e}"


def detectar_patron_persona(texto: str) -> Optional[Dict[str, Any]]:
    """
    Detecta patrones de información sobre personas en el texto.
    
    Patrones soportados:
        - "mi mamá se llama X"
        - "el cumpleaños de X es el Y"
        - "a mi amigo X le gusta Z"
    
    Args:
        texto: Texto a analizar
    
    Returns:
        Diccionario con datos extraídos o None si no hay patrón
    """
    import re
    
    texto_lower = texto.lower()
    
    # Patrón: "mi [relación] se llama [nombre]"
    match_relacion = re.search(
        r"mi\s+(mamá|papa|papá|mama|hermano|hermana|amigo|amiga|novio|novia|esposo|esposa|colega|jefe|jefa)\s+se llama\s+([a-zA-ZÁÉÍÓÚÑáéíóúñ]+)",
        texto_lower
    )
    if match_relacion:
        relacion = match_relacion.group(1)
        nombre = match_relacion.group(2).title()
        return {
            "tipo": "relacion",
            "nombre": nombre,
            "relacion": relacion,
            "mensaje_confirmacion": f"¿Quieres que recuerde que {nombre} es tu {relacion}?"
        }
    
    # Patrón: "el cumpleaños de [nombre] es [fecha]"
    match_cumple = re.search(
        r"(?:el cumpleaños de|cumpleaños de)\s+([a-zA-ZÁÉÍÓÚÑáéíóúñ]+)\s+(?:es el|es)(?:\s+el)?\s*(\d{1,2})\s*(?:de)?\s*/?\s*(\d{1,2})",
        texto_lower
    )
    if not match_cumple:
        match_cumple = re.search(
            r"([a-zA-ZÁÉÍÓÚÑáéíóúñ]+)\s+cumple\s+años?\s+(?:el|es)\s+(\d{1,2})\s*/?\s*(\d{1,2})",
            texto_lower
        )
    
    if match_cumple:
        nombre = match_cumple.group(1).title()
        dia = match_cumple.group(2).zfill(2)
        mes = match_cumple.group(3).zfill(2)
        fecha = f"{mes}-{dia}"
        return {
            "tipo": "cumpleanos",
            "nombre": nombre,
            "cumpleanos": fecha,
            "mensaje_confirmacion": f"¿Quieres que recuerde que {nombre} cumple años el {dia}/{mes}?"
        }
    
    # Patrón: "a [nombre] le gusta [algo]"
    match_gusta = re.search(
        r"a\s+(?:mi\s+)?(?:amigo|amiga|hermano|hermana|colega|novio|novia|esposo|esposa)?\s*([a-zA-ZÁÉÍÓÚÑáéíóúñ]+)\s+le gusta(?:n)?\s+(.+?)(?:\.|$)",
        texto_lower
    )
    if match_gusta:
        nombre = match_gusta.group(1).title()
        gusto = match_gusta.group(2).strip().rstrip('.')
        return {
            "tipo": "gusto",
            "nombre": nombre,
            "gusto": gusto,
            "mensaje_confirmacion": f"¿Quieres que recuerde que a {nombre} le gusta {gusto}?"
        }
    
    return None
