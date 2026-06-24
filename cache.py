# cache.py — Jarvis v7
# Caché en memoria para respuestas de IA y datos de API.
# Clave = hash(orden_normalizada), valor = (timestamp, respuesta).
# TTL configurable por tipo de dato.
#
# Uso:
#   from cache import cache
#   resp = cache.get("qué hora es")
#   cache.set("clima en cali", resultado, ttl=300)
#   cache.clear()  # vaciar todo (útil en test)

import hashlib
import time
from datetime import datetime
from logger import log
from functools import lru_cache

# TTL en segundos según tipo de consulta
TTL_CLIMA    = 300   # 5 minutos  — el clima cambia lento
TTL_SISTEMA  = 60    # 1 minuto   — CPU/RAM fluctúa más
TTL_IA       = 300   # 5 minutos  — respuestas de conversación
TTL_DEFAULT  = 300


@lru_cache(maxsize=4096)
def _normalizar(texto: str) -> str:
    """Normaliza orden para que variaciones triviales den la misma clave."""
    return texto.lower().strip().rstrip("?¿.,")


@lru_cache(maxsize=4096)
def _clave(texto: str) -> str:
    """Genera clave MD5 cacheada para textos normalizados."""
    return hashlib.md5(_normalizar(texto).encode()).hexdigest()


class Cache:
    def __init__(self, max_size: int = 1000):
        self._store: dict[str, tuple[float, object]] = {}
        self._hits   = 0
        self._misses = 0
        self._max_size = max_size

    def get(self, orden: str, ttl: int = TTL_DEFAULT):
        """
        Devuelve la respuesta cacheada si existe y no expiró.
        Retorna None si no hay caché válida.
        """
        key = _clave(orden)
        entry = self._store.get(key)
        if entry is None:
            self._misses += 1
            return None
        ts, valor = entry
        if (time.monotonic() - ts) > ttl:
            del self._store[key]
            self._misses += 1
            log.debug("Cache MISS (expirado): %s", orden[:50])
            return None
        self._hits += 1
        log.debug("Cache HIT: %s", orden[:50])
        return valor

    def set(self, orden: str, valor: object, ttl: int = TTL_DEFAULT):
        """Guarda una respuesta en caché. ttl solo se usa al leer."""
        key = _clave(orden)
        # Evitar crecimiento ilimitado: eliminar entradas más antiguas si excede max_size
        if len(self._store) >= self._max_size:
            # Eliminar 10% de las entradas más antiguas
            items_ordenados = sorted(self._store.items(), key=lambda x: x[1][0])
            for k, _ in items_ordenados[:max(1, self._max_size // 10)]:
                del self._store[k]
        self._store[key] = (time.monotonic(), valor)
        log.debug("Cache SET: %s", orden[:50])

    def invalidar(self, orden: str):
        """Elimina una entrada específica."""
        key = _clave(orden)
        self._store.pop(key, None)

    def clear(self):
        """Vacía todo el caché."""
        n = len(self._store)
        self._store.clear()
        # Limpiar también el caché de lru_cache
        _normalizar.cache_clear()
        _clave.cache_clear()
        log.info("Caché vaciado (%d entradas eliminadas)", n)

    def stats(self) -> str:
        total = self._hits + self._misses
        ratio = (self._hits / total * 100) if total else 0
        entradas = len(self._store)
        return (
            f"Caché: {entradas} entradas activas | "
            f"{self._hits} hits / {self._misses} misses ({ratio:.0f}% efectividad)"
        )

    def purgar_expirados(self, ttl: int = TTL_DEFAULT):
        """Elimina entradas expiradas. Llamar periódicamente si se desea."""
        ahora = time.monotonic()
        antes = len(self._store)
        self._store = {
            k: v for k, v in self._store.items()
            if (ahora - v[0]) <= ttl
        }
        eliminados = antes - len(self._store)
        if eliminados:
            log.debug("Caché: %d entradas expiradas purgadas", eliminados)


# Instancia global — importar desde aquí
cache = Cache()
