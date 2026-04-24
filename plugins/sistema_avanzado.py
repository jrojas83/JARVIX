# plugins/sistema_avanzado.py — Plugin de ejemplo para Jarvis v7
# Muestra información avanzada del sistema que va más allá de acciones.py
#
# Para desactivar: renombra a _sistema_avanzado.py o elimina el archivo.

import subprocess
import os
from logger import log

NOMBRE      = "sistema_avanzado"
DESCRIPCION = "Temperatura CPU, uso de disco detallado, procesos pesados"
ACCION      = "sistema_avanzado"

PATRONES = [
    "temperatura",
    "qué tan caliente",
    "cuánto disco",
    "cuanto disco",
    "proceso más pesado",
    "proceso mas pesado",
    "qué consume más",
    "que consume mas",
    "top procesos",
]


def _cmd(args: list[str], fallback="no disponible") -> str:
    try:
        return subprocess.check_output(args, text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:
        return fallback


def ejecutar(orden: str, params: dict) -> str:
    o = orden.lower()

    if any(p in o for p in ["temperatura", "caliente"]):
        temp = _cmd(["sensors"], fallback="")
        if not temp:
            return "No encontré el comando 'sensors'. Instálalo con: sudo apt install lm-sensors"
        # Extraer línea relevante
        for linea in temp.splitlines():
            if "Core 0" in linea or "Package" in linea or "temp1" in linea:
                return f"Temperatura: {linea.strip()}"
        return f"Temperatura:\n{temp[:300]}"

    if any(p in o for p in ["disco", "almacenamiento"]):
        df = _cmd(["df", "-h", "--output=source,size,used,avail,pcent,target"])
        lineas = [l for l in df.splitlines() if "/dev/" in l or "Filesystem" in l]
        return "Uso de disco:\n" + "\n".join(lineas[:6])

    if any(p in o for p in ["proceso", "consume", "top"]):
        ps = _cmd([
            "ps", "aux", "--sort=-%cpu",
            "--no-headers", "-o", "pid,comm,%cpu,%mem"
        ])
        top5 = "\n".join(ps.splitlines()[:5])
        return f"Procesos más pesados (PID · nombre · CPU · RAM):\n{top5}"

    return "No entendí qué información del sistema quieres ver."
