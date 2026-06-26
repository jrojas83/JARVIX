"""
JARVIX — Memoria de Personas
Gestiona información sobre familiares, amigos y personas importantes.
Tabla en ~/.jarvis.db junto a eventos y recordatorios.
"""

import sqlite3
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

DB_PATH = Path.home() / ".jarvis.db"


def _conn() -> sqlite3.Connection:
    return sqlite3.connect(DB_PATH)


def inicializar_tabla():
    """Crea la tabla personas si no existe. Seguro llamar múltiples veces."""
    with _conn() as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS personas (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre          TEXT    NOT NULL UNIQUE,
                relacion        TEXT,
                cumpleanos      TEXT,
                gustos          TEXT,
                notas           TEXT,
                actualizado     TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
            )
        """)
        con.execute("""
            CREATE INDEX IF NOT EXISTS idx_personas_nombre
            ON personas (nombre)
        """)


# ── Operaciones CRUD ──────────────────────────────────────────────────────────

def guardar_persona(
    nombre: str,
    relacion: str = "",
    cumpleanos: str = "",
    gustos: str = "",
    notas: str = ""
) -> bool:
    """
    Guarda o actualiza una persona. Retorna True si se guardó exitosamente.
    Si ya existe, actualiza los campos proporcionados.
    """
    nombre = nombre.strip().title()
    ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    with _conn() as con:
        # Verificar si existe
        existente = con.execute(
            "SELECT id FROM personas WHERE LOWER(nombre) = LOWER(?)", (nombre,)
        ).fetchone()
        
        if existente:
            # Actualizar solo los campos no vacíos
            campos = []
            valores = []
            if relacion:
                campos.append("relacion = ?")
                valores.append(relacion)
            if cumpleanos:
                campos.append("cumpleanos = ?")
                valores.append(cumpleanos)
            if gustos:
                campos.append("gustos = ?")
                valores.append(gustos)
            if notas:
                campos.append("notas = ?")
                valores.append(notas)
            
            if campos:
                valores.append(ahora)
                valores.append(nombre)
                query = f"UPDATE personas SET {', '.join(campos)}, actualizado = ? WHERE LOWER(nombre) = LOWER(?)"
                con.execute(query, valores)
            return True
        else:
            # Insertar nueva
            con.execute("""
                INSERT INTO personas (nombre, relacion, cumpleanos, gustos, notas, actualizado)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (nombre, relacion, cumpleanos, gustos, notas, ahora))
            return True


def obtener_persona(nombre: str) -> Optional[dict]:
    """Obtiene la información de una persona por nombre. Retorna None si no existe."""
    nombre = nombre.strip()
    with _conn() as con:
        fila = con.execute("""
            SELECT nombre, relacion, cumpleanos, gustos, notas, actualizado
            FROM personas
            WHERE LOWER(nombre) LIKE LOWER(?)
        """, (f"%{nombre}%",)).fetchone()
    
    if not fila:
        return None
    
    return {
        "nombre": fila[0],
        "relacion": fila[1] or "",
        "cumpleanos": fila[2] or "",
        "gustos": fila[3] or "",
        "notas": fila[4] or "",
        "actualizado": fila[5]
    }


def listar_personas() -> list[dict]:
    """Retorna lista de todas las personas guardadas."""
    with _conn() as con:
        filas = con.execute("""
            SELECT nombre, relacion, cumpleanos, gustos, notas
            FROM personas
            ORDER BY nombre
        """).fetchall()
    
    return [
        {
            "nombre": f[0],
            "relacion": f[1] or "",
            "cumpleanos": f[2] or "",
            "gustos": f[3] or "",
            "notas": f[4] or ""
        }
        for f in filas
    ]


def eliminar_persona(nombre: str) -> bool:
    """Elimina una persona por nombre. Retorna True si se eliminó."""
    nombre = nombre.strip()
    with _conn() as con:
        resultado = con.execute(
            "DELETE FROM personas WHERE LOWER(nombre) = LOWER(?)", (nombre,)
        )
        return resultado.rowcount > 0


# ── Detección de información en conversación ─────────────────────────────────

def detectar_info_persona(mensaje: str) -> Optional[dict]:
    """
    Detecta si un mensaje contiene información sobre una persona.
    Retorna dict con {nombre, relacion?, cumpleanos?, gustos?, notas?} o None.
    
    Patrones detectados:
    - "mi mamá se llama Rosa" → nombre + relación
    - "el cumpleaños de Pedro es el 15 de marzo" → nombre + cumpleaños
    - "a mi amigo Juan le gusta el fútbol" → nombre + relación + gusto
    - "mi hermana María nació en 1990" → nombre + relación
    """
    mensaje_lower = mensaje.lower()
    
    # Patrones para relaciones familiares
    relaciones_map = {
        r"mi\s+mamá|mi\s+madre": "mamá",
        r"mi\s+papá|mi\s+padre": "papá",
        r"mi\s+hermana": "hermana",
        r"mi\s+hermano": "hermano",
        r"mi\s+esposa|mi\s+mujer": "esposa",
        r"mi\s+esposo|mi\s+marido": "esposo",
        r"mi\s+hija": "hija",
        r"mi\s+hijo": "hijo",
        r"mi\s+amiga": "amiga",
        r"mi\s+amigo": "amigo",
        r"mi\s+novia": "novia",
        r"mi\s+novio": "novio",
        r"mi\s+jefe": "jefe",
        r"mi\s+jefa": "jefa",
        r"mi\s+compañero": "compañero",
        r"mi\s+compañera": "compañera",
    }
    
    relacion_detectada = None
    for patron, relacion in relaciones_map.items():
        if re.search(patron, mensaje_lower):
            relacion_detectada = relacion
            break
    
    # Patrón: "[relación] se llama [Nombre]"
    match_se_llama = re.search(r"(?:mi\s+\w+)\s+se\s+llama\s+(\w+)", mensaje_lower)
    if match_se_llama:
        nombre = match_se_llama.group(1).title()
        return {"nombre": nombre, "relacion": relacion_detectada or ""}
    
    # Patrón: "[relación] [Nombre]" (ej: "mi hermana María")
    match_relacion_nombre = re.search(r"(mi\s+\w+)\s+([A-Z][a-z]+)", mensaje)
    if match_relacion_nombre and not match_se_llama:
        relacion = relaciones_map.get(match_relacion_nombre.group(1).lower(), "")
        nombre = match_relacion_nombre.group(2).title()
        resultado = {"nombre": nombre, "relacion": relacion or relacion_detectada or ""}
        
        # Buscar cumpleaños en el mismo mensaje
        match_cumple = re.search(r"(?:cumpleaños|nació|nacio).*(\d{1,2})\s+(?:de|/)\s+(\w+)", mensaje_lower)
        if match_cumple:
            dia = match_cumple.group(1)
            mes = match_cumple.group(2)
            resultado["cumpleanos"] = f"{dia} de {mes}"
        
        # Buscar gustos
        match_gusta = re.search(r"le\s+gusta\s+(.+?)(?:\.|$|,)", mensaje_lower)
        if match_gusta:
            resultado["gustos"] = match_gusta.group(1).strip()
        
        return resultado
    
    # Patrón: "el cumpleaños de [Nombre] es [fecha]"
    match_cumple = re.search(r"el\s+cumpleaños\s+de\s+(\w+)\s+(?:es|era).*(\d{1,2})\s+(?:de|/)\s+(\w+)", mensaje_lower)
    if match_cumple:
        nombre = match_cumple.group(1).title()
        dia = match_cumple.group(2)
        mes = match_cumple.group(3)
        return {"nombre": nombre, "cumpleanos": f"{dia} de {mes}"}
    
    # Patrón: "a [Nombre] le gusta [algo]"
    match_gusta = re.search(r"a\s+(\w+)\s+le\s+gusta\s+(.+?)(?:\.|$)", mensaje_lower)
    if match_gusta:
        nombre = match_gusta.group(1).title()
        gusto = match_gusta.group(2).strip()
        return {"nombre": nombre, "gustos": gusto}
    
    return None


def generar_pregunta_confirmacion(info: dict) -> str:
    """Genera pregunta para confirmar antes de guardar."""
    nombre = info.get("nombre", "esta persona")
    partes = []
    
    if info.get("relacion"):
        partes.append(f"{info['relacion']} de Juan")
    if info.get("cumpleanos"):
        partes.append(f"cumple el {info['cumpleanos']}")
    if info.get("gustos"):
        partes.append(f"le gusta {info['gustos']}")
    
    if not partes:
        return f"¿Quieres que recuerde algo sobre {nombre}?"
    
    detalles = ", ".join(partes)
    return f"¿Quieres que recuerde que {nombre} ({detalles})?"


# ── Consultas útiles ──────────────────────────────────────────────────────────

def proximos_cumpleanos(dias: int = 3) -> list[dict]:
    """
    Retorna lista de personas que cumplen años en los próximos N días.
    Solo considera día y mes, ignora el año.
    """
    hoy = datetime.now()
    resultados = []
    
    with _conn() as con:
        filas = con.execute("""
            SELECT nombre, cumpleanos, relacion
            FROM personas
            WHERE cumpleanos != '' AND cumpleanos IS NOT NULL
        """).fetchall()
    
    for fila in filas:
        nombre, cumple_str, relacion = fila
        if not cumple_str:
            continue
        
        # Parsear "15 de marzo" o "15/03"
        try:
            if "de" in cumple_str:
                partes = cumple_str.split(" de ")
                dia = int(partes[0])
                mes_str = partes[1].lower()
                meses = {
                    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4,
                    "mayo": 5, "junio": 6, "julio": 7, "agosto": 8,
                    "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12
                }
                mes = meses.get(mes_str, 0)
            else:
                partes = cumple_str.replace("/", "-").split("-")
                dia = int(partes[0])
                mes = int(partes[1])
            
            if mes == 0:
                continue
            
            # Crear fecha de cumpleaños este año
            cumple_este_anio = datetime(hoy.year, mes, dia)
            
            # Si ya pasó este año, verificar el próximo año
            if cumple_este_anio.date() < hoy.date():
                cumple_este_anio = datetime(hoy.year + 1, mes, dia)
            
            diferencia = (cumple_este_anio - hoy).days
            
            if 0 <= diferencia <= dias:
                resultados.append({
                    "nombre": nombre,
                    "relacion": relacion or "",
                    "cumpleanos": cumple_str,
                    "dias_restantes": diferencia
                })
        except (ValueError, IndexError):
            continue
    
    return sorted(resultados, key=lambda x: x["dias_restantes"])


def buscar_por_relacion(relacion: str) -> list[dict]:
    """Busca personas por relación (ej: 'mamá', 'amigo')."""
    with _conn() as con:
        filas = con.execute("""
            SELECT nombre, relacion, cumpleanos, gustos, notas
            FROM personas
            WHERE LOWER(relacion) LIKE LOWER(?)
            ORDER BY nombre
        """, (f"%{relacion}%",)).fetchall()
    
    return [
        {
            "nombre": f[0],
            "relacion": f[1] or "",
            "cumpleanos": f[2] or "",
            "gustos": f[3] or "",
            "notas": f[4] or ""
        }
        for f in filas
    ]


def formatear_info_persona(persona: dict) -> str:
    """Formatea la información de una persona para mostrar."""
    lineas = [f"**{persona['nombre']}**"]
    
    if persona.get("relacion"):
        lineas.append(f"  Relación: {persona['relacion']}")
    if persona.get("cumpleanos"):
        lineas.append(f"  Cumpleaños: {persona['cumpleanos']}")
    if persona.get("gustos"):
        lineas.append(f"  Gustos: {persona['gustos']}")
    if persona.get("notas"):
        lineas.append(f"  Notas: {persona['notas']}")
    
    return "\n".join(lineas) if len(lineas) > 1 else lineas[0]


# ── Integración con conversación ─────────────────────────────────────────────

def extraer_nombres_mencionados(mensaje: str) -> list[str]:
    """Extrae posibles nombres propios mencionados en un mensaje."""
    # Buscar palabras capitalizadas que podrían ser nombres
    nombres = re.findall(r'\b[A-Z][a-z]+\b', mensaje)
    
    # Filtrar palabras comunes que no son nombres
    filtrar = {
        "Hola", "Buenos", "Buenas", "Qué", "Cómo", "Cuándo", "Dónde",
        "Por", "Para", "Juan", "Linux", "Python", "Jarvis", "Jarvix",
        "Mañana", "Tarde", "Noche", "Hoy", "Ayer", "Semana", "Mes",
        "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
        "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
    }
    
    return [n for n in nombres if n not in filtrar]


def obtener_contexto_personas(mensaje: str, max_personas: int = 3) -> str:
    """
    Obtiene contexto breve de personas mencionadas en el mensaje.
    Retorna string formateado para incluir en el prompt de la IA.
    """
    nombres_encontrados = extraer_nombres_mencionados(mensaje)
    
    if not nombres_encontrados:
        return ""
    
    personas_info = []
    for nombre in nombres_encontrados[:max_personas]:
        persona = obtener_persona(nombre)
        if persona:
            personas_info.append(persona)
    
    if not personas_info:
        return ""
    
    lineas = ["Información relevante sobre personas mencionadas:"]
    for p in personas_info:
        resumen = []
        if p.get("relacion"):
            resumen.append(p["relacion"])
        if p.get("gustos"):
            resumen.append(f"le gusta {p['gustos']}")
        
        if resumen:
            lineas.append(f"- {p['nombre']}: {', '.join(resumen)}")
        else:
            lineas.append(f"- {p['nombre']}")
    
    return "\n".join(lineas)


# ── Funciones para comandos directos ─────────────────────────────────────────

def comando_que_se_sobre(orden: str) -> str:
    """Maneja consultas como '¿qué sé sobre Pedro?'"""
    # Extraer nombre después de "sobre"
    match = re.search(r"sobre\s+(\w+)", orden.lower())
    if not match:
        return "No entendí de qué persona preguntas."
    
    nombre = match.group(1).title()
    persona = obtener_persona(nombre)
    
    if not persona:
        return f"No tengo información guardada sobre {nombre}."
    
    return formatear_info_persona(persona)


def comando_cuando_cumple(orden: str) -> str:
    """Maneja consultas como '¿cuándo cumple años mi mamá?'"""
    # Buscar relación o nombre
    match_relacion = re.search(r"(mi\s+\w+)", orden.lower())
    match_nombre = re.search(r"cumple.*?(\w+)", orden.lower())
    
    # Mapeo local de relaciones
    relaciones_map_local = {
        "mi mamá": "mamá", "mi madre": "mamá",
        "mi papá": "papá", "mi padre": "papá",
        "mi hermana": "hermana", "mi hermano": "hermano",
        "mi esposa": "esposa", "mi mujer": "esposa",
        "mi esposo": "esposo", "mi marido": "esposo",
        "mi hija": "hija", "mi hijo": "hijo",
        "mi amiga": "amiga", "mi amigo": "amigo",
        "mi novia": "novia", "mi novio": "novio",
    }
    
    if match_relacion:
        relacion = match_relacion.group(1)
        relacion_normalizada = relaciones_map_local.get(relacion, relacion)
        personas = buscar_por_relacion(relacion_normalizada)
        if personas:
            return f"{personas[0]['nombre']} ({personas[0]['relacion']}) cumple el {personas[0]['cumpleanos'] or 'fecha no registrada'}."
    
    if match_nombre:
        nombre = match_nombre.group(1).title()
        persona = obtener_persona(nombre)
        if persona:
            return f"{persona['nombre']} cumple el {persona['cumpleanos'] or 'fecha no registrada'}."
    
    return "No encontré esa persona o no tiene registrado el cumpleaños."


def comando_actualizar_persona(orden: str) -> str:
    """Maneja comandos como 'actualiza que a Rosa le gusta el café'"""
    info = detectar_info_persona(orden)
    
    if not info:
        return "No entendí qué información actualizar."
    
    nombre = info.get("nombre")
    if not obtener_persona(nombre):
        return f"No tengo registrada a {nombre}. Primero dime cómo se llama y qué relación tiene."
    
    # Actualizar campos detectados
    guardar_persona(
        nombre=nombre,
        relacion=info.get("relacion", ""),
        gustos=info.get("gustos", ""),
        notas=info.get("notas", "")
    )
    
    return f"Actualizada la información de {nombre}."
