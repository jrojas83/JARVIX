"""
plugins/vision_plugin.py
========================
Plugin de visión de pantalla para JARVIX v7/v8.
Compatible con el sistema de plugins existente (PATRONES + ejecutar).
100% offline.

Comandos que agrega:
  "qué hay en pantalla"
  "lee la pantalla"
  "analiza la pantalla"
  "ventana activa"
  "diagnóstico de visión"
"""

from jarvis_core.vision import ScreenVision

NOMBRE      = "vision"
DESCRIPCION = "Ve y analiza lo que hay en pantalla (100% local, sin internet)"
VERSION     = "1.0"

PATRONES = [
    "qué hay en pantalla", "que hay en pantalla",
    "lee la pantalla", "leer pantalla", "leer la pantalla",
    "analiza la pantalla", "analizar pantalla",
    "qué ves", "que ves", "describe la pantalla",
    "qué tengo abierto", "que tengo abierto",
    "ventana activa", "qué ventana tengo", "que ventana tengo",
    "diagnóstico de visión", "diagnostico de vision",
    "estado de visión", "instalar visión",
]

# Instancia compartida (se crea una sola vez al cargar el plugin)
_vision = ScreenVision()


def ejecutar(orden: str, params: dict) -> str:
    o = orden.lower().strip()

    # Diagnóstico
    if any(p in o for p in ["diagnóstico", "diagnostico", "estado de visión",
                             "estado de vision", "instalar visión", "instalar vision"]):
        return _vision.estado_dependencias()

    # Solo ventana activa (rápido, sin OCR)
    if any(p in o for p in ["ventana activa", "qué ventana tengo", "que ventana tengo"]):
        return f"Ventana activa: {_vision.ventana_activa()}"

    # OCR completo
    if any(p in o for p in ["lee la pantalla", "leer pantalla", "leer la pantalla",
                             "qué dice", "que dice"]):
        return _vision.leer_pantalla()

    # Analizar y proponer
    if any(p in o for p in ["analiza", "analizar", "propón", "proponer", "sugiéreme"]):
        propuesta = _vision.proponer_accion()
        if propuesta:
            return propuesta
        desc = _vision.describir()
        return f"{desc} No detecto nada concreto en lo que ayudarte ahora mismo."

    # Descripción general (default)
    return _vision.describir()
