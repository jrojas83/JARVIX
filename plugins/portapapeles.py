# plugins/portapapeles.py — Plugin de ejemplo para Jarvis v7
# Operaciones con el portapapeles del sistema (xclip / xsel).

import subprocess
from logger import log

NOMBRE      = "portapapeles"
DESCRIPCION = "Leer y escribir en el portapapeles del sistema"
ACCION      = "portapapeles"

PATRONES = [
    "qué hay en el portapapeles",
    "que hay en el portapapeles",
    "copia esto al portapapeles",
    "copia al clipboard",
    "pegar portapapeles",
    "contenido portapapeles",
    "leer portapapeles",
]


def _tiene_xclip() -> bool:
    try:
        subprocess.check_output(["which", "xclip"], stderr=subprocess.DEVNULL)
        return True
    except Exception:
        return False


def ejecutar(orden: str, params: dict) -> str:
    o = orden.lower()

    if any(p in o for p in ["qué hay", "que hay", "leer", "contenido", "pegar"]):
        if not _tiene_xclip():
            return "Necesito xclip para leer el portapapeles. Instálalo con: sudo apt install xclip"
        try:
            contenido = subprocess.check_output(
                ["xclip", "-selection", "clipboard", "-o"],
                text=True, stderr=subprocess.DEVNULL
            ).strip()
            if not contenido:
                return "El portapapeles está vacío"
            return f"Portapapeles: {contenido[:200]}"
        except Exception as e:
            return f"No pude leer el portapapeles: {e}"

    # "copia esto al portapapeles: <texto>"
    if "copia" in o and "portapapeles" in o:
        for sep in [":", "–", "-", "portapapeles"]:
            if sep in o:
                texto = o.split(sep, 1)[-1].strip()
                if texto:
                    try:
                        proc = subprocess.Popen(
                            ["xclip", "-selection", "clipboard"],
                            stdin=subprocess.PIPE
                        )
                        proc.communicate(input=texto.encode())
                        return f"Copiado al portapapeles: {texto[:60]}"
                    except Exception as e:
                        return f"Error al copiar: {e}"

    return "No entendí qué hacer con el portapapeles."
