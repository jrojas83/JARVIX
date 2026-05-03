"""
plugins/autonomy_plugin.py
==========================
Plugin de autonomía y rutinas para JARVIX v7/v8.
Permite gestionar rutinas por voz.
100% offline.

Comandos:
  "mis rutinas"
  "activar rutina buenos_dias"
  "desactivar rutina check_tarde"
  "agregar rutina"
"""

NOMBRE      = "autonomy"
DESCRIPCION = "Gestiona rutinas proactivas de Jarvis"
VERSION     = "1.0"

PATRONES = [
    "mis rutinas", "listar rutinas", "qué rutinas tienes", "que rutinas tienes",
    "activar rutina", "desactivar rutina", "agregar rutina",
    "rutinas activas", "ver rutinas",
]

# La instancia de AutonomyEngine se inyecta desde jarvis.py
# Se guarda aquí al arrancar
_engine = None


def set_engine(engine):
    """Llamado desde jarvis.py al iniciar para inyectar el motor."""
    global _engine
    _engine = engine


def ejecutar(orden: str, params: dict) -> str:
    if _engine is None:
        return "Motor de autonomía no inicializado. Revisa la integración en jarvis.py."

    o = orden.lower().strip()

    if any(p in o for p in ["mis rutinas", "listar rutinas", "ver rutinas",
                             "qué rutinas", "que rutinas", "rutinas activas"]):
        return _engine.listar_rutinas()

    if "activar rutina" in o:
        rid = o.replace("activar rutina", "").strip()
        return _engine.activar_rutina(rid) if rid else "¿Cuál rutina quieres activar?"

    if "desactivar rutina" in o:
        rid = o.replace("desactivar rutina", "").strip()
        return _engine.desactivar_rutina(rid) if rid else "¿Cuál rutina quieres desactivar?"

    return _engine.listar_rutinas()
