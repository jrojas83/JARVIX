# acciones.py — Jarvis v5
# Dispatcher: ejecuta cada tipo de acción y devuelve string para voz.
# Para añadir una nueva acción: crea la función aquí y regístrala en jarvis.py.

import subprocess
import os
import glob
from logger import log
from config import APPS_PERMITIDAS, CARPETAS, ARCHIVOS_CONOCIDOS, URLS_WEB
from recordatorios import (
    crear_recordatorio,
    listar_recordatorios,
    cancelar_recordatorio,
    agregar_nota,
    leer_notas,
    borrar_nota,
    buscar_en_notas,
    notificar,
)
from clima import obtener_clima, obtener_pronostico
from whatsapp import (
    abrir_whatsapp_web,
    enviar_mensaje_whatsapp,
    leer_mensajes_whatsapp,
    recordatorio_whatsapp,
    estado_whatsapp,
    cerrar_driver,
)
from ia_online import (
    generar_codigo,
    preguntar_online,
    es_peticion_de_codigo,
    detectar_lenguaje,
    ia_disponible,
)
from jarvis_core.intents.patterns import (
    ayuda_grupos,
    ayuda_grupo,
    ayuda_total,
    GRUPOS_FUNCIONALIDADES,
)

# ─── Apps ─────────────────────────────────────────────────────
def abrir_app(nombre_app):
    cmd = APPS_PERMITIDAS.get(nombre_app.lower())
    if cmd:
        subprocess.Popen(cmd.split(), start_new_session=True)
        log.info("App abierta: %s", nombre_app)
        # Registrar evento en memoria episódica
        from jarvis_core import episodic_memory as em
        em.registrar("app_abierta", app=nombre_app, descripcion=f"Abrió {nombre_app}")
        return f"Abriendo {nombre_app}"
    log.warning("App no registrada: %s", nombre_app)
    return f"No tengo registrada la app: {nombre_app}"

# ─── Carpetas ─────────────────────────────────────────────────
def abrir_carpeta_en_gestor(ruta):
    if os.path.exists(ruta):
        for gestor in ["thunar", "nautilus", "xdg-open"]:
            try:
                subprocess.Popen([gestor, ruta], start_new_session=True)
                log.info("Carpeta abierta: %s", ruta)
                return f"Abriendo carpeta: {ruta}"
            except FileNotFoundError:
                continue
    return f"No encontré la carpeta: {ruta}"

def abrir_carpeta_conocida(apodo):
    ruta = CARPETAS.get(apodo.lower())
    if ruta:
        return abrir_carpeta_en_gestor(ruta)
    return f"No conozco la carpeta: {apodo}"

# ─── Archivos ─────────────────────────────────────────────────
def abrir_archivo_conocido(apodo):
    ruta = ARCHIVOS_CONOCIDOS.get(apodo.lower())
    if not ruta:
        return None
    if os.path.isdir(ruta):
        subprocess.Popen(["code", ruta], start_new_session=True)
        return f"Abriendo proyecto en VS Code: {apodo}"
    if os.path.isfile(ruta):
        subprocess.Popen(["xdg-open", ruta], start_new_session=True)
        return f"Abriendo archivo: {apodo}"
    return f"El archivo '{apodo}' no existe en la ruta guardada"

def buscar_archivo_en_carpeta(nombre_archivo, carpeta_apodo):
    carpeta_ruta = CARPETAS.get(carpeta_apodo.lower())
    if not carpeta_ruta:
        return f"No conozco la carpeta: {carpeta_apodo}"
    if not os.path.exists(carpeta_ruta):
        return f"La carpeta no existe: {carpeta_ruta}"
    nombre_lower = nombre_archivo.lower()
    encontrados = [a for a in os.listdir(carpeta_ruta) if nombre_lower in a.lower()]
    if not encontrados:
        return f"No encontré '{nombre_archivo}' en {carpeta_apodo}"
    ruta_completa = os.path.join(carpeta_ruta, encontrados[0])
    subprocess.Popen(["xdg-open", ruta_completa], start_new_session=True)
    if len(encontrados) > 1:
        otros = ", ".join(encontrados[1:3])
        return f"Abriendo: {encontrados[0]}. También encontré: {otros}"
    return f"Abriendo: {encontrados[0]}"

def listar_archivos_carpeta(carpeta_apodo, extension=None):
    ruta = CARPETAS.get(carpeta_apodo.lower())
    if not ruta:
        return f"No conozco la carpeta: {carpeta_apodo}"
    if not os.path.exists(ruta):
        return f"La carpeta no existe aún: {ruta}"
    try:
        archivos = os.listdir(ruta)
    except PermissionError:
        return "No tengo permiso para leer esa carpeta"
    if not archivos:
        return f"La carpeta {carpeta_apodo} está vacía"
    if extension:
        ext_lower = extension.lower().lstrip(".")
        archivos = [a for a in archivos if a.lower().endswith(f".{ext_lower}")]
        if not archivos:
            return f"No hay archivos .{ext_lower} en {carpeta_apodo}"
    dirs  = [a for a in archivos if os.path.isdir(os.path.join(ruta, a))]
    files = [a for a in archivos if os.path.isfile(os.path.join(ruta, a))]
    resumen = []
    if dirs:
        resumen.append(f"Carpetas ({len(dirs)}): {', '.join(dirs[:5])}")
        if len(dirs) > 5:
            resumen.append(f"...y {len(dirs)-5} más")
    if files:
        resumen.append(f"Archivos ({len(files)}): {', '.join(files[:6])}")
        if len(files) > 6:
            resumen.append(f"...y {len(files)-6} más")
    return ". ".join(resumen)

# ─── URLs y búsqueda web ──────────────────────────────────────
def abrir_url(url):
    if not url.startswith("http"):
        url = "https://" + url
    subprocess.Popen(["xdg-open", url], start_new_session=True)
    return f"Abriendo {url} en el navegador"

def abrir_url_conocida(nombre):
    url = URLS_WEB.get(nombre.lower())
    if url:
        return abrir_url(url)
    return f"No tengo registrado: {nombre}"

def buscar_en_web(consulta, motor="google"):
    motores = {
        "google":     "https://www.google.com/search?q=",
        "youtube":    "https://www.youtube.com/results?search_query=",
        "wikipedia":  "https://es.wikipedia.org/w/index.php?search=",
        "duckduckgo": "https://duckduckgo.com/?q=",
    }
    base = motores.get(motor.lower(), motores["google"])
    url  = base + consulta.replace(" ", "+")
    subprocess.Popen(["xdg-open", url], start_new_session=True)
    return f"Buscando '{consulta}' en {motor}"

def abrir_whatsapp():
    return abrir_url("https://web.whatsapp.com")

# ─── Sistema ──────────────────────────────────────────────────
def obtener_info_sistema():
    info = []
    try:
        r = subprocess.run(["top", "-bn1"], capture_output=True, text=True)
        for line in r.stdout.split("\n"):
            if "Cpu" in line or "cpu" in line:
                info.append(line.strip())
                break
    except Exception:
        pass
    try:
        r = subprocess.run(["df", "-h", "/"], capture_output=True, text=True)
        lines = r.stdout.strip().split("\n")
        if len(lines) > 1:
            p = lines[1].split()
            info.append(f"Disco: {p[2]} usados de {p[1]}, {p[3]} libres")
    except Exception:
        pass
    try:
        r = subprocess.run(["free", "-h"], capture_output=True, text=True)
        lines = r.stdout.strip().split("\n")
        if len(lines) > 1:
            p = lines[1].split()
            info.append(f"RAM: {p[2]} usada de {p[1]}, {p[3]} libre")
    except Exception:
        pass
    return ". ".join(info) if info else "No pude obtener info del sistema"

def controlar_volumen(accion):
    try:
        cmds = {
            "subir":    ["pactl", "set-sink-volume", "@DEFAULT_SINK@", "+10%"],
            "bajar":    ["pactl", "set-sink-volume", "@DEFAULT_SINK@", "-10%"],
            "silenciar":["pactl", "set-sink-mute", "@DEFAULT_SINK@", "toggle"],
            "mute":     ["pactl", "set-sink-mute", "@DEFAULT_SINK@", "toggle"],
            "maximo":   ["pactl", "set-sink-volume", "@DEFAULT_SINK@", "100%"],
        }
        if accion in cmds:
            subprocess.run(cmds[accion])
            log.info("Volumen: %s", accion)
            return f"Volumen: {accion}"
        return f"Acción de volumen no reconocida: {accion}"
    except Exception as e:
        log.error("controlar_volumen: %s", e)
        return f"Error controlando volumen: {e}"

# ─── Clima ────────────────────────────────────────────────────
def accion_clima(operacion="actual", ciudad=None):
    if operacion == "pronostico":
        return obtener_pronostico(ciudad)
    return obtener_clima(ciudad)

# ─── WhatsApp ─────────────────────────────────────────────────
def accion_whatsapp(operacion, contacto="", mensaje="", tiempo=""):
    if operacion == "abrir":
        ok, msg = abrir_whatsapp_web(esperar_qr=True)
        return msg
    elif operacion == "enviar":
        if not contacto:
            return "Necesito saber a quién enviar el mensaje."
        if not mensaje:
            return "¿Qué mensaje quieres enviar?"
        return enviar_mensaje_whatsapp(contacto, mensaje)
    elif operacion == "leer":
        if not contacto:
            return "¿De qué contacto quieres leer mensajes?"
        return leer_mensajes_whatsapp(contacto)
    elif operacion == "recordatorio":
        from recordatorios import _parsear_tiempo
        segundos, desc = _parsear_tiempo(tiempo)
        if not segundos:
            return f"No entendí el tiempo '{tiempo}'."
        return recordatorio_whatsapp(contacto, mensaje, segundos)
    elif operacion == "estado":
        return estado_whatsapp()
    elif operacion == "cerrar":
        cerrar_driver()
        return "WhatsApp Web cerrado."
    return "Operación de WhatsApp no reconocida."

# ─── Código ───────────────────────────────────────────────────
def accion_codigo(peticion, lenguaje=None, solo_portapapeles=False):
    return generar_codigo(peticion, lenguaje, pegar_vscode=not solo_portapapeles)

# ─── Recordatorios ────────────────────────────────────────────
def accion_recordatorio(operacion, mensaje="", tiempo=""):
    if operacion == "crear":
        return crear_recordatorio(mensaje, tiempo)
    elif operacion == "listar":
        return listar_recordatorios()
    elif operacion == "cancelar":
        return cancelar_recordatorio()
    return "No entendí qué hacer con el recordatorio."

# ─── Notas ────────────────────────────────────────────────────
def accion_nota(operacion, texto="", termino=""):
    if operacion == "agregar":
        return agregar_nota(texto)
    elif operacion == "leer":
        return leer_notas()
    elif operacion == "borrar":
        return borrar_nota()
    elif operacion == "buscar":
        return buscar_en_notas(termino)
    return "No entendí qué hacer con las notas."

# ─── Energía ──────────────────────────────────────────────────
def control_energia(accion):
    try:
        if accion == "apagar":
            subprocess.Popen(["systemctl", "poweroff"])
            return "Apagando el sistema..."
        elif accion == "reiniciar":
            subprocess.Popen(["systemctl", "reboot"])
            return "Reiniciando el sistema..."
        elif accion == "suspender":
            print("\n⚠️  SUSPENDER — Triple confirmación requerida")
            for i, pregunta in enumerate([
                "¿Confirmas suspender? (si/no): ",
                "¿Seguro? Perderás trabajo no guardado (si/no): ",
                "¿Última confirmación — suspender ahora? (si/no): ",
            ], 1):
                resp = input(f"  [{i}/3] {pregunta}").strip().lower()
                if resp not in ("si", "sí", "s", "yes"):
                    return "Suspensión cancelada."
            subprocess.Popen(["systemctl", "suspend"])
            return "Suspendiendo el sistema..."
        return f"Acción no reconocida: {accion}"
    except Exception as e:
        log.error("control_energia: %s", e)
        return f"Error: {e}"

# ─── WiFi ─────────────────────────────────────────────────────
def controlar_wifi(accion):
    try:
        if accion == "estado":
            r = subprocess.run(["nmcli", "radio", "wifi"], capture_output=True, text=True)
            return f"WiFi: {r.stdout.strip()}"
        elif accion == "activar":
            subprocess.run(["nmcli", "radio", "wifi", "on"], check=True)
            return "WiFi activado."
        elif accion == "desactivar":
            subprocess.run(["nmcli", "radio", "wifi", "off"], check=True)
            return "WiFi desactivado."
        elif accion == "listar":
            r = subprocess.run(
                ["nmcli", "-f", "SSID,SIGNAL,SECURITY", "device", "wifi", "list"],
                capture_output=True, text=True
            )
            lineas = r.stdout.strip().split("\n")
            if len(lineas) <= 1:
                return "No encontré redes WiFi. ¿Está el WiFi activado?"
            return "Redes WiFi disponibles:\n" + "\n".join(lineas[:9])
        elif accion.startswith("conectar:"):
            ssid = accion.split(":", 1)[1].strip()
            r = subprocess.run(
                ["nmcli", "device", "wifi", "connect", ssid],
                capture_output=True, text=True, timeout=20
            )
            return f"Conectado a '{ssid}'." if r.returncode == 0 else f"No pude conectarme a '{ssid}'."
        return f"Acción WiFi no reconocida: {accion}"
    except FileNotFoundError:
        return "nmcli no disponible. Instala: sudo apt install network-manager"
    except Exception as e:
        log.error("controlar_wifi: %s", e)
        return f"Error WiFi: {e}"

# ─── Bluetooth ────────────────────────────────────────────────
def controlar_bluetooth(accion):
    try:
        if accion == "estado":
            r = subprocess.run(["rfkill", "list", "bluetooth"], capture_output=True, text=True)
            if "Soft blocked: no" in r.stdout:
                return "Bluetooth: ACTIVADO"
            elif "Soft blocked: yes" in r.stdout:
                return "Bluetooth: DESACTIVADO"
            return f"Estado Bluetooth:\n{r.stdout.strip()}"
        elif accion == "activar":
            subprocess.run(["rfkill", "unblock", "bluetooth"], check=True)
            subprocess.run(["bluetoothctl", "power", "on"], capture_output=True, timeout=5)
            return "Bluetooth activado."
        elif accion == "desactivar":
            subprocess.run(["rfkill", "block", "bluetooth"], check=True)
            return "Bluetooth desactivado."
        elif accion == "abrir":
            for gestor in ["blueman-manager", "blueberry", "gnome-bluetooth"]:
                try:
                    subprocess.Popen([gestor], start_new_session=True)
                    return f"Abriendo gestor Bluetooth ({gestor})."
                except FileNotFoundError:
                    continue
            return "No encontré gestor Bluetooth. Instala: sudo apt install blueman"
        return f"Acción Bluetooth no reconocida: {accion}"
    except FileNotFoundError:
        return "rfkill no disponible. Instala: sudo apt install rfkill"
    except Exception as e:
        log.error("controlar_bluetooth: %s", e)
        return f"Error Bluetooth: {e}"

# ─── Cambio de modelo Ollama ──────────────────────────────────
_modelo_ollama_activo = {"nombre": None}

def cambiar_modelo_ollama(nombre=None):
    try:
        r = subprocess.run(["ollama", "list"], capture_output=True, text=True)
        lineas = r.stdout.strip().split("\n")[1:]
        disponibles = [l.split()[0] for l in lineas if l.strip()]
    except Exception:
        disponibles = []

    if nombre is None:
        if not disponibles:
            return "No hay modelos Ollama descargados."
        actual = _modelo_ollama_activo["nombre"] or "por defecto (config.py)"
        lista  = "\n".join(f"  • {m}" for m in disponibles)
        return f"Modelo Ollama activo: {actual}\nDisponibles:\n{lista}"

    nombre_lower = nombre.lower()
    match = next((m for m in disponibles if nombre_lower in m.lower()), None)
    if match:
        _modelo_ollama_activo["nombre"] = match
        import config as cfg
        cfg.MODELO = match
        log.info("Modelo Ollama cambiado a: %s", match)
        return f"Modelo Ollama cambiado a: {match}"
    return f"No encontré el modelo '{nombre}'. Disponibles: {', '.join(disponibles) if disponibles else 'ninguno'}"

def get_modelo_ollama():
    return _modelo_ollama_activo["nombre"]

# ─── Ayuda por voz ────────────────────────────────────────────
def accion_funcionalidades(tipo, grupo=None):
    """
    tipo: "grupos" | "total" | "grupo_especifico"
    grupo: nombre del grupo si tipo=="grupo_especifico"
    """
    if tipo == "grupos":
        return ayuda_grupos()
    elif tipo == "total":
        return ayuda_total()
    elif tipo == "grupo_especifico" and grupo:
        return ayuda_grupo(grupo)
    return ayuda_grupos()


# ─── Memoria episódica ────────────────────────────────────────
def que_hice_hoy():
    from jarvis_core.episodic_memory import que_hice_hoy as _q
    return _q()

def que_hice_ayer():
    from jarvis_core.episodic_memory import que_hice_ayer as _q
    return _q()

def resumen_del_dia():
    from jarvis_core.episodic_memory import resumen_del_dia as _r
    return _r()

def ultima_vez_app(orden: str):
    # Extrae el nombre de la app/cosa de la orden
    # Ej: "cuándo usé firefox" → "firefox"
    palabras_clave = ["usé", "abrí", "ejecuté", "corrí", "vi"]
    for p in palabras_clave:
        if p in orden:
            termino = orden.split(p)[-1].strip()
            from jarvis_core.episodic_memory import ultima_vez_que_use
            return ultima_vez_que_use(termino)
    return "No entendí qué app o acción buscas."

