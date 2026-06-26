# jarvis_core/web_search.py — Búsqueda web automática para JARVIX
# ================================================================================
# Permite a JARVIX buscar información en internet cuando es necesario.
#
# Características:
#   - Evaluación con IA local para decidir si necesita búsqueda
#   - Búsqueda en DuckDuckGo en español
#   - Extracción limpia de contenido con trafilatura
#   - Cache de búsquedas por sesión
#   - Integración transparente en el flujo conversacional

import hashlib
from typing import Any, Dict, List, Optional
from datetime import datetime

from logger import log


class WebSearchEngine:
    """
    Motor de búsqueda web para JARVIX.
    Decide cuándo buscar, ejecuta la búsqueda y formatea resultados.
    """
    
    def __init__(self, ollama_caller=None):
        self.ollama_caller = ollama_caller
        self._cache_busquedas: Dict[str, Dict] = {}  # Cache por sesión
        self._max_resultados = 5
        self._max_contenido_caracteres = 2000
    
    def _necesita_busqueda(self, pregunta: str) -> bool:
        """
        Usa IA local para determinar si la pregunta requiere información de internet.
        
        Args:
            pregunta: La pregunta del usuario
        
        Returns:
            True si necesita búsqueda web
        """
        if not self.ollama_caller:
            # Si no hay IA, usar heurística simple
            return self._heuristica_necesita_busqueda(pregunta)
        
        try:
            prompt = f"""¿Necesita esta pregunta información actualizada de internet para responderse correctamente?
Pregunta: "{pregunta}"

Responde SOLO "sí" o "no". Considera que necesita internet si:
- Pregunta sobre noticias, eventos actuales o información que cambia frecuentemente
- Pregunta sobre precios, clima, resultados deportivos
- Pregunta "qué es" algo que podría ser un producto/servicio reciente
- Menciona fechas recientes (hoy, esta semana, este mes)

No necesita internet si:
- Es conocimiento general estable
- Es una opinión personal
- Es una pregunta sobre cómo hacer algo
- Es un saludo o conversación casual"""

            respuesta = self.ollama_caller(prompt, max_tokens=10)
            respuesta_lower = respuesta.lower().strip()
            
            necesita = any(p in respuesta_lower for p in ["sí", "si", "yes"])
            log.info("[WEBSEARCH] ¿Necesita búsqueda? %s (IA dijo: %s)", necesita, respuesta_lower[:20])
            return necesita
        
        except Exception as e:
            log.warning("[WEBSEARCH] Error consultando IA para búsqueda: %s", e)
            return self._heuristica_necesita_busqueda(pregunta)
    
    def _heuristica_necesita_busqueda(self, pregunta: str) -> bool:
        """Heurística simple para decidir si necesita búsqueda."""
        pregunta_lower = pregunta.lower()
        
        # Palabras que indican necesidad de búsqueda
        indicadores_busqueda = [
            "noticia", "noticias", "última hora", "ultima hora",
            "clima", "tiempo", "temperatura", "pronóstico",
            "precio", "cuánto cuesta", "quanto custa",
            "resultado", "marcador", "ganó", "gano",
            "hoy", "ahora", "actual", "reciente",
            "quién es", "qué es", "cuál es",  # Cuando es sobre algo específico
            "busca", "busca en internet", "googlea",
        ]
        
        # Verificar indicadores
        for indicador in indicadores_busqueda:
            if indicador in pregunta_lower:
                return True
        
        # Verificar si menciona fechas recientes
        if any(f in pregunta_lower for f in ["hoy", "esta semana", "este mes", "este año"]):
            return True
        
        return False
    
    def _buscar_duckduckgo(self, query: str) -> List[Dict[str, str]]:
        """
        Ejecuta búsqueda en DuckDuckGo.
        
        Args:
            query: Término de búsqueda
        
        Returns:
            Lista de resultados con título, URL y fragmento
        """
        try:
            from duckduckgo_search import DDGS
            
            with DDGS() as ddgs:
                resultados = list(ddgs.text(query, max_results=self._max_resultados))
                
                resultados_formateados = []
                for r in resultados:
                    resultados_formateados.append({
                        "titulo": r.get("title", "Sin título"),
                        "url": r.get("href", ""),
                        "fragmento": r.get("body", "")[:200]
                    })
                
                log.info("[WEBSEARCH] Encontrados %d resultados para: %s", len(resultados_formateados), query[:50])
                return resultados_formateados
        
        except ImportError:
            log.warning("[WEBSEARCH] duckduckgo-search no instalado")
            return []
        except Exception as e:
            log.warning("[WEBSEARCH] Error en búsqueda: %s", e)
            return []
    
    def _extraer_contenido(self, url: str) -> Optional[str]:
        """
        Extrae texto limpio de una URL usando trafilatura.
        
        Args:
            url: URL de la página
        
        Returns:
            Texto extraído o None si falla
        """
        try:
            import trafilatura
            
            contenido = trafilatura.fetch_url(url)
            if contenido:
                texto = trafilatura.extract(contenido, limit=self._max_contenido_caracteres)
                if texto:
                    # Limitar longitud
                    return texto[:self._max_contenido_caracteres]
            
            return None
        
        except ImportError:
            log.warning("[WEBSEARCH] trafilatura no instalado")
            return None
        except Exception as e:
            log.warning("[WEBSEARCH] Error extrayendo contenido: %s", e)
            return None
    
    def _generar_cache_key(self, query: str) -> str:
        """Genera una clave única para cachear búsquedas."""
        return hashlib.md5(query.lower().encode()).hexdigest()
    
    def buscar(self, pregunta: str, forzar: bool = False) -> Optional[Dict[str, Any]]:
        """
        Ejecuta búsqueda web completa si es necesaria.
        
        Args:
            pregunta: La pregunta original del usuario
            forzar: Si True, busca sin evaluar si es necesario
        
        Returns:
            Diccionario con resultados o None si no se busca
        """
        # Verificar cache primero
        cache_key = self._generar_cache_key(pregunta)
        if cache_key in self._cache_busquedas and not forzar:
            log.info("[WEBSEARCH] Usando resultado cacheado")
            return self._cache_busquedas[cache_key]
        
        # Decidir si buscar
        if not forzar and not self._necesita_busqueda(pregunta):
            return None
        
        # Ejecutar búsqueda
        log.info("[WEBSEARCH] Buscando: %s", pregunta[:100])
        resultados = self._buscar_duckduckgo(pregunta)
        
        if not resultados:
            return None
        
        # Extraer contenido de la primera URL
        primera_url = resultados[0].get("url")
        contenido_extraido = None
        if primera_url:
            contenido_extraido = self._extraer_contenido(primera_url)
        
        # Construir resultado
        resultado = {
            "query": pregunta,
            "resultados": resultados,
            "contenido_principal": contenido_extraido,
            "timestamp": datetime.now(),
            "fuente": "DuckDuckGo"
        }
        
        # Guardar en cache
        self._cache_busquedas[cache_key] = resultado
        
        return resultado
    
    def formatear_para_ia(self, resultados: Dict[str, Any], pregunta: str) -> str:
        """
        Formatea los resultados de búsqueda para incluir en el prompt de la IA.
        
        Args:
            resultados: Resultados de la búsqueda
            pregunta: Pregunta original
        
        Returns:
            Texto formateado para la IA
        """
        if not resultados:
            return ""
        
        lineas = ["\n\n--- INFORMACIÓN DE INTERNET ---"]
        lineas.append(f"Búsqueda: {pregunta}")
        lineas.append(f"Fuente: {resultados.get('fuente', 'Web')}")
        lineas.append("")
        
        # Contenido principal si existe
        if resultados.get("contenido_principal"):
            lineas.append("Contenido principal:")
            lineas.append(resultados["contenido_principal"][:1000])
            lineas.append("")
        
        # Lista de resultados
        lineas.append("Resultados encontrados:")
        for i, r in enumerate(resultados.get("resultados", [])[:5], 1):
            lineas.append(f"{i}. {r['titulo']}")
            lineas.append(f"   {r['fragmento'][:150]}")
            if r.get('url'):
                lineas.append(f"   URL: {r['url'][:80]}")
            lineas.append("")
        
        lineas.append("--- FIN INFORMACIÓN ---\n")
        lineas.append("Usa esta información para responder la pregunta de manera natural.")
        lineas.append("Menciona brevemente la fuente al final si es relevante.\n")
        
        return "\n".join(lineas)
    
    def limpiar_cache(self) -> None:
        """Limpia el cache de búsquedas."""
        self._cache_busquedas.clear()
        log.info("[WEBSEARCH] Cache limpiado")


# Instancia global
_search_engine: Optional[WebSearchEngine] = None


def get_search_engine(ollama_caller=None) -> WebSearchEngine:
    """Obtiene la instancia global del motor de búsqueda."""
    global _search_engine
    if _search_engine is None:
        _search_engine = WebSearchEngine(ollama_caller=ollama_caller)
    return _search_engine


def buscar_web(pregunta: str, forzar: bool = False, ollama_caller=None) -> Optional[Dict[str, Any]]:
    """Función conveniente para búsqueda web rápida."""
    engine = get_search_engine(ollama_caller)
    return engine.buscar(pregunta, forzar)
