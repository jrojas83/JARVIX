# jarvis_core/voice_notes.py — Notas por voz con etiquetas semánticas
# ================================================================================
# Permite capturar ideas diciendo "nota: ..." y JARVIX las guarda, clasifica
# automáticamente por tema usando embeddings, y permite buscarlas después
# por significado, no por palabras exactas.
#
# Características:
#   - Detección automática del prefijo "nota:", "apunta:", "anota:", etc.
#   - Generación de etiquetas con Ollama local
#   - Búsqueda semántica usando embeddings compartidos con semantic_cache.py
#   - Almacenamiento en SQLite con vector serializado

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

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
    """Crea la tabla de notas si no existe."""
    try:
        conn = _get_connection()
        cursor = conn.cursor()
        
        # Tabla de notas de voz
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS notas_voz (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL DEFAULT (datetime('now','localtime')),
                contenido TEXT NOT NULL,
                etiquetas TEXT,
                embedding BLOB,
                contexto_app TEXT
            )
        """)
        
        # Índice para consultas por timestamp
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_notas_timestamp ON notas_voz (timestamp)")
        
        conn.commit()
        conn.close()
        log.info("[VOICE_NOTES] Tabla inicializada correctamente")
        return True
        
    except Exception as e:
        log.warning("[VOICE_NOTES] Error inicializando tabla: %s", e)
        return False


def _get_embedding_function():
    """
    Obtiene la función de embedding desde semantic_cache.py.
    Evita cargar el modelo dos veces.
    """
    try:
        from jarvis_core.semantic_cache import _embedding
        return _embedding
    except ImportError as e:
        log.warning("[VOICE_NOTES] No se pudo importar _embedding: %s", e)
        return None


def _generar_etiquetas(texto: str) -> List[str]:
    """
    Genera etiquetas para una nota usando Ollama local.
    
    Args:
        texto: Contenido de la nota
    
    Returns:
        Lista de etiquetas (2-4 palabras clave)
    """
    if not texto or len(texto) < 5:
        return []
    
    prompt = f"""Dado este texto: '{texto[:200]}'. 
Responde ÚNICAMENTE con una lista JSON de 2 a 4 etiquetas de una sola palabra que describan el tema. 
Ejemplo: ['trabajo', 'python', 'error']. 
Solo el JSON, nada más."""

    try:
        import requests
        
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "qwen2.5:3b",
                "prompt": prompt,
                "stream": False
            },
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            respuesta = data.get("response", "").strip()
            
            # Intentar parsear JSON
            try:
                # Limpiar posibles caracteres extra
                if respuesta.startswith("```json"):
                    respuesta = respuesta[7:]
                if respuesta.endswith("```"):
                    respuesta = respuesta[:-3]
                respuesta = respuesta.strip()
                
                etiquetas = json.loads(respuesta)
                if isinstance(etiquetas, list):
                    return [str(t).lower().strip() for t in etiquetas if t]
            except json.JSONDecodeError:
                log.warning("[VOICE_NOTES] No se pudo parsear JSON de etiquetas: %s", respuesta)
        
    except requests.RequestException as e:
        log.warning("[VOICE_NOTES] Error llamando a Ollama: %s", e)
    except Exception as e:
        log.warning("[VOICE_NOTES] Error generando etiquetas: %s", e)
    
    return []


def guardar_nota(contenido: str, contexto_app: str = "") -> str:
    """
    Guarda una nota con etiquetas generadas automáticamente.
    
    Args:
        contenido: Contenido de la nota
        contexto_app: Aplicación donde se creó la nota
    
    Returns:
        str: Confirmación con etiquetas
    """
    if not contenido or len(contenido) < 3:
        return "El contenido de la nota es muy corto"
    
    try:
        # 1. Generar etiquetas
        etiquetas = _generar_etiquetas(contenido)
        etiquetas_json = json.dumps(etiquetas, ensure_ascii=False)
        
        # 2. Generar embedding
        embedding_func = _get_embedding_function()
        embedding_bytes = None
        
        if embedding_func:
            try:
                import numpy as np
                embedding = embedding_func(contenido)
                embedding_bytes = embedding.tobytes()
            except Exception as e:
                log.warning("[VOICE_NOTES] Error generando embedding: %s", e)
        
        # 3. Insertar en base de datos
        conn = _get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO notas_voz (contenido, etiquetas, embedding, contexto_app)
            VALUES (?, ?, ?, ?)
        """, (contenido, etiquetas_json, embedding_bytes, contexto_app))
        
        conn.commit()
        conn.close()
        
        # 4. Registrar en memoria episódica
        try:
            from jarvis_core.memory.episodic_memory import registrar
            registrar('nota_guardada', descripcion=contenido[:100])
        except Exception:
            pass
        
        # 5. Retornar confirmación
        if etiquetas:
            return f"Nota guardada. Etiquetas: {', '.join(etiquetas)}"
        else:
            return "Nota guardada"
            
    except Exception as e:
        log.error("[VOICE_NOTES] Error guardando nota: %s", e)
        return "Error al guardar la nota"


def _obtener_numpy():
    """Obtiene el módulo numpy."""
    try:
        import numpy as np
        return np
    except ImportError:
        return None


def _similitud_coseno(vec1, vec2) -> float:
    """Calcula similitud coseno entre dos vectores."""
    np = _obtener_numpy()
    if np is None:
        return 0.0
    
    dot_product = np.dot(vec1, vec2)
    norm1 = np.linalg.norm(vec1)
    norm2 = np.linalg.norm(vec2)
    
    if norm1 == 0 or norm2 == 0:
        return 0.0
    
    return float(dot_product / (norm1 * norm2))


def buscar_notas(consulta: str, limite: int = 5) -> str:
    """
    Busca notas por similitud semántica.
    
    Args:
        consulta: Texto de búsqueda
        limite: Máximo de resultados
    
    Returns:
        str: Resultados formateados
    """
    embedding_func = _get_embedding_function()
    
    if not embedding_func:
        return "No se puede realizar búsqueda semántica (modelo no disponible)"
    
    try:
        # 1. Generar embedding de la consulta
        embedding_consulta = embedding_func(consulta)
        
        # 2. Cargar últimas 500 notas (para no saturar RAM)
        conn = _get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, timestamp, contenido, etiquetas, embedding
            FROM notas_voz
            ORDER BY timestamp DESC
            LIMIT 500
        """)
        
        notas = cursor.fetchall()
        conn.close()
        
        if not notas:
            return "No hay notas guardadas"
        
        # 3. Calcular similitud con cada nota
        resultados = []
        
        for nota in notas:
            embedding_bytes = nota['embedding']
            
            if embedding_bytes:
                try:
                    np = _obtener_numpy()
                    if np:
                        embedding_nota = np.frombuffer(embedding_bytes, dtype=np.float32)
                        similitud = _similitud_coseno(embedding_consulta, embedding_nota)
                    else:
                        similitud = 0.0
                except Exception:
                    similitud = 0.0
            else:
                similitud = 0.0
            
            resultados.append({
                'id': nota['id'],
                'timestamp': nota['timestamp'],
                'contenido': nota['contenido'],
                'etiquetas': nota['etiquetas'],
                'similitud': similitud
            })
        
        # 4. Ordenar por similitud y tomar las top
        resultados.sort(key=lambda x: x['similitud'], reverse=True)
        top_resultados = resultados[:limite]
        
        # 5. Formatear salida
        lineas = []
        for r in top_resultados:
            fecha = r['timestamp'].split(' ')[0]  # Solo fecha
            etiquetas_str = ""
            if r['etiquetas']:
                try:
                    tags = json.loads(r['etiquetas'])
                    if tags:
                        etiquetas_str = f" [{', '.join(tags)}]"
                except Exception:
                    pass
            
            lineas.append(f"• {fecha}: {r['contenido'][:80]}{etiquetas_str}")
        
        if lineas:
            return f"Notas encontradas ({len(top_resultados)}):\n" + "\n".join(lineas)
        else:
            return "No se encontraron notas relacionadas"
            
    except Exception as e:
        log.error("[VOICE_NOTES] Error buscando notas: %s", e)
        return "Error al buscar notas"


def buscar_por_etiqueta(etiqueta: str) -> str:
    """
    Busca notas por etiqueta específica.
    
    Args:
        etiqueta: Etiqueta a buscar
    
    Returns:
        str: Resultados formateados
    """
    try:
        conn = _get_connection()
        cursor = conn.cursor()
        
        # Buscar notas que contengan la etiqueta en el JSON
        cursor.execute("""
            SELECT id, timestamp, contenido, etiquetas
            FROM notas_voz
            WHERE etiquetas LIKE ?
            ORDER BY timestamp DESC
            LIMIT 20
        """, (f'%{etiqueta}%',))
        
        notas = cursor.fetchall()
        conn.close()
        
        if not notas:
            return f"No hay notas con la etiqueta '{etiqueta}'"
        
        lineas = []
        for nota in notas:
            fecha = nota['timestamp'].split(' ')[0]
            lineas.append(f"• {fecha}: {nota['contenido'][:80]}")
        
        return f"Notas con etiqueta '{etiqueta}' ({len(notas)}):\n" + "\n".join(lineas)
        
    except Exception as e:
        log.error("[VOICE_NOTES] Error buscando por etiqueta: %s", e)
        return "Error al buscar por etiqueta"


def listar_notas_recientes(n: int = 10) -> str:
    """
    Lista las últimas n notas guardadas.
    
    Args:
        n: Número de notas a mostrar
    
    Returns:
        str: Notas formateadas
    """
    try:
        conn = _get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, timestamp, contenido, etiquetas
            FROM notas_voz
            ORDER BY timestamp DESC
            LIMIT ?
        """, (n,))
        
        notas = cursor.fetchall()
        conn.close()
        
        if not notas:
            return "No hay notas guardadas"
        
        lineas = []
        for nota in notas:
            hora = nota['timestamp'].split(' ')[1][:5]  # HH:MM
            etiquetas_str = ""
            if nota['etiquetas']:
                try:
                    tags = json.loads(nota['etiquetas'])
                    if tags:
                        etiquetas_str = f" [{', '.join(tags)}]"
                except Exception:
                    pass
            
            lineas.append(f"• {hora}: {nota['contenido'][:60]}{etiquetas_str}")
        
        return f"Últimas {len(notas)} notas:\n" + "\n".join(lineas)
        
    except Exception as e:
        log.error("[VOICE_NOTES] Error listando notas: %s", e)
        return "Error al listar notas"


def eliminar_ultima_nota() -> str:
    """Elimina la última nota guardada."""
    try:
        conn = _get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            DELETE FROM notas_voz
            WHERE id = (SELECT MAX(id) FROM notas_voz)
        """)
        
        eliminadas = cursor.rowcount
        conn.commit()
        conn.close()
        
        if eliminadas > 0:
            return "Última nota eliminada"
        else:
            return "No hay notas para eliminar"
            
    except Exception as e:
        log.error("[VOICE_NOTES] Error eliminando nota: %s", e)
        return "Error al eliminar nota"
