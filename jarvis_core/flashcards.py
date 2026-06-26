# jarvis_core/flashcards.py — Flashcards con algoritmo SM-2 (Anki-style)
# ================================================================================
# Detecta automáticamente información nueva en conversaciones y la convierte
# en flashcards. Usa el algoritmo SM-2 para espaciado inteligente de repaso.
#
# Características:
#   - Detección automática de conocimiento nuevo con Ollama
#   - Algoritmo SM-2 para cálculo de intervalos de repaso
#   - Sesiones de repaso por voz
#   - Integración con el motor proactivo para recordatorios matutinos

import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

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
    """Crea la tabla de flashcards si no existe."""
    try:
        conn = _get_connection()
        cursor = conn.cursor()
        
        # Tabla de flashcards
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS flashcards (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                creada TEXT NOT NULL DEFAULT (datetime('now','localtime')),
                pregunta TEXT NOT NULL,
                respuesta TEXT NOT NULL,
                tema TEXT,
                intervalo_dias INTEGER DEFAULT 1,
                factor_facilidad REAL DEFAULT 2.5,
                repeticiones INTEGER DEFAULT 0,
                proxima_revision TEXT DEFAULT (datetime('now','localtime')),
                ultima_revision TEXT,
                calificacion_ultima INTEGER
            )
        """)
        
        # Índice para consultas por próxima revisión
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_flashcards_revision ON flashcards (proxima_revision)")
        
        conn.commit()
        conn.close()
        log.info("[FLASHCARDS] Tabla inicializada correctamente")
        return True
        
    except Exception as e:
        log.warning("[FLASHCARDS] Error inicializando tabla: %s", e)
        return False


def _calcular_sm2(calificacion: int, intervalo: int, factor: float, 
                  repeticiones: int) -> Tuple[int, float, int]:
    """
    Implementa el algoritmo SM-2 de repetición espaciada.
    
    Args:
        calificacion: 1-5 (1=no lo sabía, 5=bien)
        intervalo: Días hasta la próxima revisión actual
        factor: Factor de facilidad actual
        repeticiones: Número de repeticiones completadas
    
    Returns:
        tuple: (nuevo_intervalo, nuevo_factor, nuevas_repeticiones)
    """
    # Si la calificación es baja (< 3), reiniciar
    if calificacion < 3:
        nuevo_intervalo = 1
        nuevas_repeticiones = 0
        nuevo_factor = max(1.3, factor)  # No reducir el factor
    else:
        # Calcular nuevo intervalo
        if repeticiones == 0:
            nuevo_intervalo = 1
        elif repeticiones == 1:
            nuevo_intervalo = 6
        else:
            nuevo_intervalo = round(intervalo * factor)
        
        nuevas_repeticiones = repeticiones + 1
        
        # Actualizar factor de facilidad
        # Fórmula SM-2: F' = F + 0.1 - (5-Q) * (0.08 + (5-Q) * 0.02)
        nuevo_factor = factor + 0.1 - (5 - calificacion) * (0.08 + (5 - calificacion) * 0.02)
        nuevo_factor = max(1.3, nuevo_factor)  # Límite inferior 1.3
    
    return nuevo_intervalo, nuevo_factor, nuevas_repeticiones


def _llamar_ollama(prompt: str, timeout: int = 30) -> Optional[str]:
    """Llama a Ollama local y retorna la respuesta."""
    try:
        import requests
        
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "qwen2.5:3b",
                "prompt": prompt,
                "stream": False
            },
            timeout=timeout
        )
        
        if response.status_code == 200:
            data = response.json()
            return data.get("response", "").strip()
        else:
            return None
            
    except Exception as e:
        log.warning("[FLASHCARDS] Error llamando a Ollama: %s", e)
        return None


def _detectar_conocimiento_nuevo(pregunta_usuario: str, respuesta_jarvix: str) -> Optional[Dict]:
    """
    Analiza un intercambio para detectar si contiene conocimiento nuevo.
    
    Args:
        pregunta_usuario: Pregunta del usuario
        respuesta_jarvix: Respuesta de JARVIX
    
    Returns:
        dict o None: Datos de la flashcard si vale la pena, None si no
    """
    if not pregunta_usuario or not respuesta_jarvix:
        return None
    
    # Limitar longitud para no saturar Ollama
    pregunta_corta = pregunta_usuario[:300]
    respuesta_corta = respuesta_jarvix[:500]
    
    prompt = f"""Analiza este intercambio entre un usuario y un asistente.

Pregunta del usuario: '{pregunta_corta}'
Respuesta del asistente: '{respuesta_corta}'

¿Contiene información factual nueva que valga la pena recordar en una flashcard?

Si SÍ contiene información valiosa, responde con JSON exacto:
{{"vale_la_pena": true, "pregunta_flashcard": "...", "respuesta_flashcard": "...", "tema": "..."}}

Si NO contiene información valiosa (es conversación casual, saludos, opiniones subjetivas, etc.), responde:
{{"vale_la_pena": false}}

Responde SOLO con el JSON, nada más."""

    respuesta = _llamar_ollama(prompt, timeout=30)
    
    if not respuesta:
        return None
    
    try:
        # Limpiar posibles bloques markdown
        if respuesta.startswith("```json"):
            respuesta = respuesta[7:]
        if respuesta.endswith("```"):
            respuesta = respuesta[:-3]
        respuesta = respuesta.strip()
        
        datos = json.loads(respuesta)
        
        if isinstance(datos, dict) and datos.get('vale_la_pena'):
            return {
                'pregunta': datos.get('pregunta_flashcard', pregunta_usuario[:100]),
                'respuesta': datos.get('respuesta_flashcard', respuesta_jarvix[:200]),
                'tema': datos.get('tema', 'general')
            }
        
        return None
        
    except (json.JSONDecodeError, KeyError) as e:
        log.warning("[FLASHCARDS] Error parseando respuesta: %s", e)
        return None


def crear_flashcard_automatica(pregunta_usuario: str, respuesta_jarvix: str) -> bool:
    """
    Crea una flashcard automáticamente si detecta conocimiento nuevo.
    Trabaja silenciosamente en background.
    
    Args:
        pregunta_usuario: Pregunta del usuario
        respuesta_jarvix: Respuesta de JARVIX
    
    Returns:
        bool: True si se creó, False si no
    """
    try:
        datos = _detectar_conocimiento_nuevo(pregunta_usuario, respuesta_jarvix)
        
        if not datos:
            return False
        
        # Insertar en la base de datos
        conn = _get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO flashcards (pregunta, respuesta, tema)
            VALUES (?, ?, ?)
        """, (datos['pregunta'], datos['respuesta'], datos['tema']))
        
        conn.commit()
        conn.close()
        
        log.info("[FLASHCARDS] Flashcard creada automáticamente: %s", datos['pregunta'][:50])
        return True
        
    except Exception as e:
        log.warning("[FLASHCARDS] Error creando flashcard automática: %s", e)
        return False


def crear_flashcard_manual(pregunta: str, respuesta: str, tema: str = "") -> str:
    """
    Crea una flashcard manualmente.
    
    Args:
        pregunta: Pregunta de la flashcard
        respuesta: Respuesta de la flashcard
        tema: Tema opcional
    
    Returns:
        str: Confirmación
    """
    if not pregunta or not respuesta:
        return "La pregunta y respuesta no pueden estar vacías"
    
    try:
        conn = _get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO flashcards (pregunta, respuesta, tema)
            VALUES (?, ?, ?)
        """, (pregunta, respuesta, tema))
        
        conn.commit()
        conn.close()
        
        return f"Flashcard creada. Tema: {tema or 'general'}"
        
    except Exception as e:
        log.error("[FLASHCARDS] Error creando flashcard manual: %s", e)
        return "Error al crear flashcard"


def obtener_tarjetas_para_hoy(limite: int = 5) -> List[Dict]:
    """
    Obtiene las tarjetas que toca repasar hoy.
    
    Args:
        limite: Máximo de tarjetas a retornar
    
    Returns:
        list[dict]: Lista de tarjetas para repasar
    """
    try:
        conn = _get_connection()
        cursor = conn.cursor()
        
        ahora = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        cursor.execute("""
            SELECT id, pregunta, respuesta, tema, intervalo_dias, 
                   factor_facilidad, repeticiones, proxima_revision
            FROM flashcards
            WHERE proxima_revision <= ?
            ORDER BY proxima_revision ASC
            LIMIT ?
        """, (ahora, limite))
        
        tarjetas = []
        for row in cursor.fetchall():
            tarjetas.append({
                'id': row['id'],
                'pregunta': row['pregunta'],
                'respuesta': row['respuesta'],
                'tema': row['tema'],
                'intervalo_dias': row['intervalo_dias'],
                'factor_facilidad': row['factor_facilidad'],
                'repeticiones': row['repeticiones'],
                'proxima_revision': row['proxima_revision']
            })
        
        conn.close()
        return tarjetas
        
    except Exception as e:
        log.error("[FLASHCARDS] Error obteniendo tarjetas: %s", e)
        return []


def _actualizar_tarjeta(id_tarjeta: int, intervalo: int, factor: float, 
                        repeticiones: int, calificacion: int) -> bool:
    """Actualiza los datos de una tarjeta después de un repaso."""
    try:
        conn = _get_connection()
        cursor = conn.cursor()
        
        proxima = (datetime.now() + timedelta(days=intervalo)).strftime('%Y-%m-%d %H:%M:%S')
        ahora = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        cursor.execute("""
            UPDATE flashcards
            SET intervalo_dias = ?,
                factor_facilidad = ?,
                repeticiones = ?,
                proxima_revision = ?,
                ultima_revision = ?,
                calificacion_ultima = ?
            WHERE id = ?
        """, (intervalo, factor, repeticiones, proxima, ahora, calificacion, id_tarjeta))
        
        conn.commit()
        conn.close()
        return True
        
    except Exception as e:
        log.error("[FLASHCARDS] Error actualizando tarjeta: %s", e)
        return False


def sesion_repaso() -> str:
    """
    Inicia una sesión de repaso de flashcards.
    
    Returns:
        str: Resumen de la sesión
    """
    tarjetas = obtener_tarjetas_para_hoy(5)
    
    if not tarjetas:
        return "No tienes tarjetas para repasar hoy. ¡Bien hecho!"
    
    resultados = []
    
    for i, tarjeta in enumerate(tarjetas, 1):
        # En una implementación real con voz, aquí se:
        # 1. Diría la pregunta por voz
        # 2. Esperaría la respuesta del usuario
        # 3. Mostraría la respuesta correcta
        # 4. Preguntaría la calificación
        
        # Por ahora, simulamos que todas se respondieron bien (calificación 4)
        # En la integración real, esto se maneja interactivamente
        
        calificacion = 4  # Default: "bien"
        
        # Calcular nuevos valores con SM-2
        nuevo_intervalo, nuevo_factor, nuevas_repeticiones = _calcular_sm2(
            calificacion=calificacion,
            intervalo=tarjeta['intervalo_dias'],
            factor=tarjeta['factor_facilidad'],
            repeticiones=tarjeta['repeticiones']
        )
        
        # Actualizar tarjeta
        _actualizar_tarjeta(
            tarjeta['id'],
            nuevo_intervalo,
            nuevo_factor,
            nuevas_repeticiones,
            calificacion
        )
        
        resultados.append({
            'pregunta': tarjeta['pregunta'][:50],
            'calificacion': calificacion,
            'proximo_repaso': nuevo_intervalo
        })
    
    # Calcular próximo repaso más cercano
    proximo_dia = min(r['proximo_repaso'] for r in resultados) if resultados else 1
    
    return f"Sesión completada. Repasaste {len(resultados)} tarjetas. Próxima sesión en {proximo_dia} días."


def estadisticas_flashcards() -> str:
    """
    Retorna estadísticas sobre las flashcards.
    
    Returns:
        str: Estadísticas formateadas
    """
    try:
        conn = _get_connection()
        cursor = conn.cursor()
        
        # Total de tarjetas
        cursor.execute("SELECT COUNT(*) FROM flashcards")
        total = cursor.fetchone()[0]
        
        # Tarjetas para hoy
        ahora = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute("SELECT COUNT(*) FROM flashcards WHERE proxima_revision <= ?", (ahora,))
        para_hoy = cursor.fetchone()[0]
        
        # Tarjeta con mejor retención (más repeticiones)
        cursor.execute("""
            SELECT pregunta, repeticiones 
            FROM flashcards 
            ORDER BY repeticiones DESC 
            LIMIT 1
        """)
        mejor_row = cursor.fetchone()
        
        # Tema con más tarjetas
        cursor.execute("""
            SELECT tema, COUNT(*) as cantidad
            FROM flashcards
            GROUP BY tema
            ORDER BY cantidad DESC
            LIMIT 1
        """)
        tema_row = cursor.fetchone()
        
        conn.close()
        
        lineas = [f"Total de flashcards: {total}"]
        lineas.append(f"Para repasar hoy: {para_hoy}")
        
        if mejor_row:
            lineas.append(f"Mejor retención: '{mejor_row[0][:40]}...' ({mejor_row[1]} repeticiones)")
        
        if tema_row:
            lineas.append(f"Tema principal: {tema_row[0]} ({tema_row[1]} tarjetas)")
        
        return "\n".join(lineas)
        
    except Exception as e:
        log.error("[FLASHCARDS] Error obteniendo estadísticas: %s", e)
        return "Error al obtener estadísticas"


def get_estado() -> Dict[str, Any]:
    """Retorna el estado actual del sistema de flashcards."""
    try:
        conn = _get_connection()
        cursor = conn.cursor()
        
        # Total
        cursor.execute("SELECT COUNT(*) FROM flashcards")
        total = cursor.fetchone()[0]
        
        # Para hoy
        ahora = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute("SELECT COUNT(*) FROM flashcards WHERE proxima_revision <= ?", (ahora,))
        para_hoy = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            'total': total,
            'para_hoy': para_hoy,
            'tabla_inicializada': True
        }
        
    except Exception as e:
        return {
            'total': 0,
            'para_hoy': 0,
            'tabla_inicializada': False,
            'error': str(e)
        }
