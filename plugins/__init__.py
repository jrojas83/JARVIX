# plugins/__init__.py — Jarvis v7
# Sistema de plugins: descubrimiento y registro automático.
#
# ─── CÓMO CREAR UN PLUGIN ─────────────────────────────────────
#
# 1. Crea un archivo en plugins/  p.ej: plugins/spotify.py
# 2. Define en él:
#
#    NOMBRE     = "spotify"          # identificador único (sin espacios)
#    DESCRIPCION = "Control de Spotify"
#    PATRONES   = ["pon música", "pausa", "siguiente canción"]
#
#    def ejecutar(orden: str, params: dict) -> str:
#        # Hace lo que sea y devuelve un string para hablar
#        return "Reproduciendo en Spotify"
#
#    # Opcional: acción estructurada (igual que dispatcher de jarvis.py)
#    ACCION = "spotify"   # nombre de la acción en el JSON de Ollama
#
# 3. Reinicia Jarvis. El plugin se carga solo.
#
# ─── CONVENCIONES ─────────────────────────────────────────────
# - ejecutar() SIEMPRE devuelve str (puede ser vacío "")
# - Si el plugin falla, debe devolver un mensaje de error amigable
# - Los plugins no deben importar entre sí (usa config.py si necesitan datos)
# ──────────────────────────────────────────────────────────────

import importlib
import os
import sys
from logger import log

_PLUGINS_DIR = os.path.dirname(os.path.abspath(__file__))
_plugins_registrados: dict[str, object] = {}


def cargar_plugins() -> list[str]:
    """
    Escanea plugins/ y carga todos los .py que no sean __init__.
    Retorna lista de nombres de plugins cargados.
    """
    cargados = []
    if _PLUGINS_DIR not in sys.path:
        sys.path.insert(0, os.path.dirname(_PLUGINS_DIR))

    for archivo in sorted(os.listdir(_PLUGINS_DIR)):
        if not archivo.endswith(".py") or archivo.startswith("_"):
            continue
        nombre_modulo = archivo[:-3]
        try:
            modulo = importlib.import_module(f"plugins.{nombre_modulo}")
            # Validación mínima
            if not hasattr(modulo, "ejecutar"):
                log.warning("Plugin %s ignorado: falta función ejecutar()", nombre_modulo)
                continue
            nombre = getattr(modulo, "NOMBRE", nombre_modulo)
            _plugins_registrados[nombre] = modulo
            cargados.append(nombre)
            log.info("Plugin cargado: %s", nombre)
        except Exception as e:
            log.error("Error cargando plugin %s: %s", nombre_modulo, e)

    return cargados


def listar_plugins() -> list[dict]:
    """Retorna info de todos los plugins cargados."""
    resultado = []
    for nombre, modulo in _plugins_registrados.items():
        resultado.append({
            "nombre":      nombre,
            "descripcion": getattr(modulo, "DESCRIPCION", "Sin descripción"),
            "patrones":    getattr(modulo, "PATRONES", []),
            "accion":      getattr(modulo, "ACCION", nombre),
        })
    return resultado


def detectar_plugin(orden: str) -> tuple[str, object] | None:
    """
    Comprueba si algún plugin reconoce la orden por sus PATRONES.
    Retorna (nombre_plugin, modulo) o None.
    """
    o = orden.lower().strip()
    for nombre, modulo in _plugins_registrados.items():
        patrones = getattr(modulo, "PATRONES", [])
        if any(p in o for p in patrones):
            return nombre, modulo
    return None


def ejecutar_plugin(nombre: str, orden: str, params: dict = None) -> str | None:
    """
    Ejecuta un plugin por nombre.
    Retorna la respuesta string o None si no existe.
    """
    modulo = _plugins_registrados.get(nombre)
    if not modulo:
        return None
    try:
        return modulo.ejecutar(orden, params or {})
    except Exception as e:
        log.error("Error en plugin %s: %s", nombre, e)
        return f"El plugin {nombre} falló: {e}"


def ejecutar_por_orden(orden: str) -> str | None:
    """
    Detecta automáticamente el plugin adecuado y lo ejecuta.
    Retorna la respuesta o None si ningún plugin coincide.
    """
    resultado = detectar_plugin(orden)
    if resultado is None:
        return None
    nombre, modulo = resultado
    log.info("Plugin activado: %s para orden: %s", nombre, orden[:60])
    try:
        return modulo.ejecutar(orden, {})
    except Exception as e:
        log.error("Error ejecutando plugin %s: %s", nombre, e)
        return f"Error en plugin {nombre}: {e}"


def resumen_plugins() -> str:
    """Texto legible para el comando 'qué plugins tienes'."""
    plugins = listar_plugins()
    if not plugins:
        return "No hay plugins instalados. Añade archivos .py en la carpeta plugins/"
    lineas = [f"  • {p['nombre']}: {p['descripcion']}" for p in plugins]
    return f"Plugins activos ({len(plugins)}):\n" + "\n".join(lineas)
