# jarvis_core/file_agent.py — Organizador de archivos agente
# ================================================================================
# Permite organizar archivos con instrucciones en lenguaje natural.
# JARVIX genera un plan de acción, lo muestra para aprobación, y ejecuta
# solo si el usuario confirma explícitamente.
#
# Características:
#   - Análisis de directorios con pathlib
#   - Generación de planes con Ollama local
#   - Ejecución segura (sin eliminación directa, usa "papelera")
#   - Confirmación explícita requerida antes de ejecutar

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

from logger import log


def _get_home() -> Path:
    """Obtiene el directorio home del usuario."""
    return Path.home()


def _get_trash_path() -> Path:
    """Obtiene la ruta de la papelera de JARVIX."""
    trash = _get_home() / '.jarvis_trash'
    trash.mkdir(parents=True, exist_ok=True)
    return trash


def analizar_directorio(ruta: str) -> Dict[str, Any]:
    """
    Analiza un directorio y retorna estadísticas.
    
    Args:
        ruta: Ruta del directorio a analizar
    
    Returns:
        dict: Estadísticas del directorio
    """
    try:
        path = Path(ruta)
        
        if not path.exists():
            return {'error': f'El directorio no existe: {ruta}'}
        
        if not path.is_dir():
            return {'error': f'No es un directorio: {ruta}'}
        
        # Listar contenido
        items = list(path.iterdir())
        archivos = [i for i in items if i.is_file()]
        carpetas = [i for i in items if i.is_dir()]
        
        # Extensiones encontradas
        extensiones: Dict[str, int] = {}
        for archivo in archivos:
            ext = archivo.suffix.lower() or '(sin extensión)'
            extensiones[ext] = extensiones.get(ext, 0) + 1
        
        # Archivos más grandes (top 10)
        archivos_con_tamano = [(a, a.stat().st_size) for a in archivos if a.exists()]
        archivos_con_tamano.sort(key=lambda x: x[1], reverse=True)
        mas_grandes = [(a.name, t) for a, t in archivos_con_tamano[:10]]
        
        # Archivos más antiguos (top 10)
        archivos_con_fecha = [(a, a.stat().st_mtime) for a in archivos if a.exists()]
        archivos_con_fecha.sort(key=lambda x: x[1])
        mas_antiguos = [(a.name, datetime.fromtimestamp(t).strftime('%Y-%m-%d')) 
                        for a, t in archivos_con_fecha[:10]]
        
        # Tamaño total
        tamaño_total = sum(t for _, t in archivos_con_tamano)
        
        # Duplicados por nombre
        nombres: Dict[str, List] = {}
        for archivo in archivos:
            nombre = archivo.name
            if nombre not in nombres:
                nombres[nombre] = []
            nombres[nombre].append(str(archivo))
        duplicados = {k: v for k, v in nombres.items() if len(v) > 1}
        
        return {
            'ruta': str(path.absolute()),
            'total_archivos': len(archivos),
            'total_carpetas': len(carpetas),
            'extensiones': extensiones,
            'mas_grandes': mas_grandes,
            'mas_antiguos': mas_antiguos,
            'duplicados': duplicados,
            'tamaño_total_mb': round(tamaño_total / (1024 * 1024), 2)
        }
        
    except Exception as e:
        log.error("[FILE_AGENT] Error analizando directorio: %s", e)
        return {'error': str(e)}


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
            log.warning("[FILE_AGENT] Ollama retornó status %d", response.status_code)
            return None
            
    except Exception as e:
        log.warning("[FILE_AGENT] Error llamando a Ollama: %s", e)
        return None


def generar_plan(objetivo: str, analisis: Dict[str, Any]) -> List[Dict]:
    """
    Genera un plan de organización usando Ollama.
    
    Args:
        objetivo: Instrucción del usuario en lenguaje natural
        analisis: Resultado de analizar_directorio()
    
    Returns:
        list[dict]: Lista de pasos del plan
    """
    if 'error' in analisis:
        return []
    
    # Construir prompt
    prompt = f"""Eres un asistente que organiza archivos de forma CONSERVADORA.
Objetivo del usuario: {objetivo}

Análisis del directorio:
- Total archivos: {analisis.get('total_archivos', 0)}
- Total carpetas: {analisis.get('total_carpetas', 0)}
- Extensiones: {json.dumps(analisis.get('extensiones', {}))}
- Tamaño total: {analisis.get('tamaño_total_mb', 0)} MB

Genera un plan de organización en formato JSON EXACTO como este:
[
  {{
    "paso": 1,
    "accion": "crear_carpeta",
    "destino": "Documentos",
    "razon": "Para guardar documentos PDF y DOCX"
  }},
  {{
    "paso": 2,
    "accion": "mover",
    "origen": "archivo.pdf",
    "destino": "Documentos/archivo.pdf",
    "razon": "Es un documento PDF"
  }}
]

Acciones posibles: crear_carpeta, mover, renombrar.
REGLAS IMPORTANTES:
1. NUNCA uses la acción "eliminar". En su lugar, sugiere mover a "Para revisar".
2. Sé conservador: en caso de duda, no muevas el archivo.
3. Crea carpetas lógicas basadas en las extensiones encontradas.
4. Responde SOLO con el JSON válido, sin texto adicional.
5. Si no hay nada que organizar, responde con una lista vacía []."""

    respuesta = _llamar_ollama(prompt, timeout=30)
    
    if not respuesta:
        return []
    
    # Intentar parsear JSON
    try:
        # Limpiar posibles bloques de código markdown
        if respuesta.startswith("```json"):
            respuesta = respuesta[7:]
        if respuesta.endswith("```"):
            respuesta = respuesta[:-3]
        respuesta = respuesta.strip()
        
        plan = json.loads(respuesta)
        
        if isinstance(plan, list):
            # Validar estructura
            plan_validado = []
            for paso in plan:
                if isinstance(paso, dict) and 'accion' in paso:
                    plan_validado.append(paso)
            return plan_validado
        else:
            log.warning("[FILE_AGENT] La respuesta no es una lista")
            return []
            
    except json.JSONDecodeError as e:
        log.warning("[FILE_AGENT] No se pudo parsear JSON: %s. Respuesta: %s", e, respuesta[:200])
        return []


def mostrar_plan(plan: List[Dict]) -> str:
    """
    Muestra un plan formateado para el usuario.
    
    Args:
        plan: Lista de pasos del plan
    
    Returns:
        str: Plan formateado
    """
    if not plan:
        return "No se generó un plan de organización."
    
    lineas = []
    resumen = {
        'mover': 0,
        'crear_carpeta': 0,
        'renombrar': 0,
        'eliminar': 0
    }
    
    for paso in plan:
        accion = paso.get('accion', 'desconocida')
        razon = paso.get('razon', '')
        
        if accion == 'mover':
            origen = paso.get('origen', '?')
            destino = paso.get('destino', '?')
            lineas.append(f"{paso.get('paso', '?')}. MOVER: {origen} → {destino}")
            resumen['mover'] += 1
        elif accion == 'crear_carpeta':
            destino = paso.get('destino', '?')
            lineas.append(f"{paso.get('paso', '?')}. CREAR CARPETA: {destino}")
            resumen['crear_carpeta'] += 1
        elif accion == 'renombrar':
            origen = paso.get('origen', '?')
            destino = paso.get('destino', '?')
            lineas.append(f"{paso.get('paso', '?')}. RENOMBRAR: {origen} → {destino}")
            resumen['renombrar'] += 1
        elif accion == 'eliminar':
            origen = paso.get('origen', '?')
            lineas.append(f"{paso.get('paso', '?')}. ELIMINAR: {origen} ⚠️")
            resumen['eliminar'] += 1
        else:
            lineas.append(f"{paso.get('paso', '?')}. {accion.upper()}")
        
        if razon:
            lineas[-1] += f" ({razon})"
    
    # Agregar resumen
    lineas.append("")
    lineas.append("--- RESUMEN ---")
    lineas.append(f"Archivos a mover: {resumen['mover']}")
    lineas.append(f"Carpetas a crear: {resumen['crear_carpeta']}")
    lineas.append(f"Archivos a renombrar: {resumen['renombrar']}")
    
    if resumen['eliminar'] > 0:
        lineas.append(f"⚠️  Archivos a eliminar: {resumen['eliminar']} (¡cuidado!)")
    
    lineas.append("")
    lineas.append("¿Confirmas este plan? Responde 'sí' para ejecutar o 'no' para cancelar.")
    
    return "\n".join(lineas)


def ejecutar_paso(paso: Dict, ruta_base: Path) -> bool:
    """
    Ejecuta un solo paso del plan.
    
    Args:
        paso: Diccionario con la definición del paso
        ruta_base: Ruta base del directorio
    
    Returns:
        bool: True si se ejecutó correctamente
    """
    accion = paso.get('accion', '')
    
    try:
        if accion == 'crear_carpeta':
            destino = ruta_base / paso.get('destino', '')
            destino.mkdir(parents=True, exist_ok=True)
            log.info("[FILE_AGENT] Carpeta creada: %s", destino)
            return True
            
        elif accion == 'mover':
            origen = ruta_base / paso.get('origen', '')
            destino = ruta_base / paso.get('destino', '')
            
            if not origen.exists():
                log.warning("[FILE_AGENT] Origen no existe: %s", origen)
                return False
            
            # Asegurar que el directorio de destino existe
            destino.parent.mkdir(parents=True, exist_ok=True)
            
            # Mover archivo
            shutil.move(str(origen), str(destino))
            log.info("[FILE_AGENT] Archivo movido: %s → %s", origen, destino)
            
            # Registrar en memoria episódica
            try:
                from jarvis_core.memory.episodic_memory import registrar
                registrar('archivo_movido', descripcion=f'{origen.name} → {destino.parent.name}')
            except Exception:
                pass
            
            return True
            
        elif accion == 'renombrar':
            origen = ruta_base / paso.get('origen', '')
            destino = ruta_base / paso.get('destino', '')
            
            if not origen.exists():
                log.warning("[FILE_AGENT] Origen no existe: %s", origen)
                return False
            
            origen.rename(destino)
            log.info("[FILE_AGENT] Archivo renombrado: %s → %s", origen, destino)
            return True
            
        elif accion == 'eliminar':
            # NUNCA eliminar directamente, mover a papelera
            origen = ruta_base / paso.get('origen', '')
            
            if not origen.exists():
                return False
            
            trash = _get_trash_path()
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            destino = trash / f"{timestamp}_{origen.name}"
            
            shutil.move(str(origen), str(destino))
            log.info("[FILE_AGENT] Archivo movido a papelera: %s", destino)
            return True
            
        else:
            log.warning("[FILE_AGENT] Acción desconocida: %s", accion)
            return False
            
    except Exception as e:
        log.error("[FILE_AGENT] Error ejecutando paso: %s", e)
        return False


def ejecutar_plan(plan: List[Dict], ruta: str, confirmado: bool = False) -> str:
    """
    Ejecuta un plan completo.
    
    Args:
        plan: Lista de pasos del plan
        ruta: Ruta del directorio
        confirmado: Si es True, ejecuta; si es False, solo muestra
    
    Returns:
        str: Resultado de la ejecución
    """
    if not confirmado:
        return mostrar_plan(plan)
    
    if not plan:
        return "No hay plan para ejecutar."
    
    ruta_base = Path(ruta)
    exitosos = 0
    fallidos = 0
    
    for paso in plan:
        if ejecutar_paso(paso, ruta_base):
            exitosos += 1
        else:
            fallidos += 1
    
    # Registrar evento en memoria episódica
    try:
        from jarvis_core.memory.episodic_memory import registrar
        registrar('plan_ejecutado', 
                  descripcion=f'Organización: {exitosos} éxitos, {fallidos} fallos',
                  app='file_agent')
    except Exception:
        pass
    
    return f"Plan ejecutado: {exitosos} pasos exitosos, {fallidos} fallidos"


def organizar(orden: str) -> str:
    """
    Función principal para organizar archivos.
    
    Args:
        orden: Instrucción del usuario en lenguaje natural
    
    Returns:
        str: Plan generado o resultado de ejecución
    """
    # Extraer ruta de la orden usando Ollama
    prompt_ruta = f"""De esta instrucción: '{orden}', extrae solo la ruta del directorio mencionada.
Si no hay ruta explícita, responde con 'Descargas'.
Solo la ruta, nada más. Ejemplos:
- "organiza mis descargas" → Descargas
- "ordena la carpeta documentos" → Documentos
- "limpia /home/usuario/proyectos" → /home/usuario/proyectos"""

    respuesta_ruta = _llamar_ollama(prompt_ruta, timeout=15)
    
    if not respuesta_ruta:
        ruta_defecto = 'Descargas'
    else:
        ruta_defecto = respuesta_ruta.strip()
    
    # Resolver ruta relativa al home
    ruta_completa = _get_home() / ruta_defecto
    
    if not ruta_completa.exists():
        # Intentar con la ruta literal
        ruta_completa = Path(ruta_defecto)
        
        if not ruta_completa.exists():
            return f"No encontré el directorio: {ruta_defecto}. Intenta con una ruta absoluta."
    
    # Analizar directorio
    analisis = analizar_directorio(str(ruta_completa))
    
    if 'error' in analisis:
        return analisis['error']
    
    # Generar plan
    plan = generar_plan(orden, analisis)
    
    if not plan:
        return "No pude generar un plan de organización. Intenta ser más específico."
    
    # Mostrar plan y esperar confirmación
    return mostrar_plan(plan)


def get_estado() -> Dict[str, Any]:
    """Retorna información sobre el estado del file agent."""
    return {
        'trash_path': str(_get_trash_path()),
        'home': str(_get_home())
    }
