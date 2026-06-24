# -*- coding: utf-8 -*-
"""
Patrones de intenciones para Jarvis v6.

Este módulo centraliza TODOS los patrones de detección de intenciones.
Los patrones se usan en jarvis_core/intents/builtins.py para registrar
los intents en el sistema centralizado.

CÓMO AÑADIR UN NUEVO COMANDO
────────────────────────────────────────────────────────────────────
1. Añade una lista PATRONES_MI_COSA = ["frase 1", "variante 2", ...]
2. Registra el intent en jarvis_core/intents/builtins.py
3. En acciones.py, crea la función accion_mi_cosa() si no existe

CRITERIO PARA LOS PATRONES
────────────────────────────────────────────────────────────────────
- Incluir SIEMPRE la versión con tilde y sin tilde
- Incluir variantes coloquiales colombianas/latinoamericanas
- Incluir el imperativo ("abre") y el infinitivo ("abrir")
- Incluir variantes con pronombre ("dime", "muéstrame")
- Evitar patrones demasiado cortos que causen falsos positivos
  (ej: "hora" solo puede capturar "temperatura", mejor "qué hora")
"""

from __future__ import annotations

# ─── Sistema y control ────────────────────────────────────────────
PATRONES_HORA: tuple[str, ...] = (
    "qué hora es", "que hora es", "dime la hora", "qué horas son",
    "que horas son", "dime qué hora es", "hora actual",
    "qué hora tienes", "que hora tienes",
)

PATRONES_FECHA: tuple[str, ...] = (
    "qué día es", "que dia es", "fecha de hoy", "qué fecha es",
    "que fecha es", "qué fecha tenemos", "que fecha tenemos",
    "cuál es la fecha", "cual es la fecha", "dime la fecha",
    "qué día es hoy", "que dia es hoy",
)

PATRONES_SISTEMA: tuple[str, ...] = (
    "cómo está el sistema", "como esta el sistema",
    "info del sistema", "información del sistema",
    "estado del sistema", "recursos del sistema",
    "cómo va el sistema", "como va el sistema",
    "cuánta ram", "cuanta ram", "uso de cpu",
    "espacio en disco", "cuánto disco", "cuanto disco",
    "rendimiento del sistema",
)

# Palabras exactas de salida (se comparan con ==, no "in")
PATRONES_SALIR: tuple[str, ...] = (
    "salir", "adios", "adiós", "hasta luego", "cerrar jarvis",
    "apaga jarvis", "cierra jarvis", "exit", "bye", "chao",
    "nos vemos", "hasta pronto",
)

# ─── Volumen ──────────────────────────────────────────────────────
PATRONES_VOL_SUBIR: tuple[str, ...] = (
    "sube el volumen", "más volumen", "subir volumen",
    "sube el audio", "más audio", "volumen más alto",
    "aumenta el volumen", "aumenta el audio",
    "sube el sonido", "más sonido", "súbele al volumen",
    "subele al volumen", "pon más volumen",
)

PATRONES_VOL_BAJAR: tuple[str, ...] = (
    "baja el volumen", "menos volumen", "bajar volumen",
    "baja el audio", "menos audio", "volumen más bajo",
    "disminuye el volumen", "baja el sonido",
    "menos sonido", "bájale al volumen", "bajale al volumen",
)

PATRONES_VOL_SILENCIO: tuple[str, ...] = (
    "silencia", "mute", "sin sonido", "silenciar",
    "modo silencio", "quita el sonido", "pon en silencio",
    "mutear", "cállate", "callate", "sin audio",
)

PATRONES_VOL_MAXIMO: tuple[str, ...] = (
    "volumen al máximo", "volumen maximo", "al máximo el volumen",
    "sube el volumen al máximo", "volumen al tope",
    "ponlo al máximo", "ponlo al maximo",
)

# ─── Clima ────────────────────────────────────────────────────────
PATRONES_CLIMA: tuple[str, ...] = (
    "clima", "tiempo", "temperatura", "llueve", "va a llover",
    "pronóstico", "pronostico", "lloverá", "llovera",
    "cómo está el tiempo", "como esta el tiempo",
    "qué clima hace", "que clima hace",
    "va a hacer calor", "va a hacer frio", "va a hacer frío",
    "está lloviendo", "esta lloviendo",
)

PATRONES_CLIMA_PRONOS: tuple[str, ...] = (
    "pronóstico", "pronostico", "mañana", "próximos días",
    "proximos dias", "esta semana", "para mañana",
    "pronóstico del tiempo", "para la semana",
)

# ─── Recordatorios ────────────────────────────────────────────────
PATRONES_RECORDATORIO_CREAR: tuple[str, ...] = (
    "recuérdame", "recuerdame", "pon un recordatorio",
    "avísame en", "avisame en", "crea un recordatorio",
    "ponme un recordatorio", "acuérdame", "acordame",
    "no me dejes olvidar", "recuérdame que", "recuerdame que",
)

PATRONES_RECORDATORIO_LISTAR: tuple[str, ...] = (
    "qué recordatorios", "que recordatorios",
    "mis recordatorios", "recordatorios activos",
    "cuántos recordatorios", "cuantos recordatorios",
    "ver recordatorios", "listar recordatorios",
    "qué tengo pendiente", "que tengo pendiente",
)

PATRONES_RECORDATORIO_CANCELAR: tuple[str, ...] = (
    "cancela el recordatorio", "cancelar recordatorio",
    "borra el recordatorio", "elimina el recordatorio",
    "quita el recordatorio", "borra el aviso",
)

# ─── Notas ────────────────────────────────────────────────────────
PATRONES_NOTA_AGREGAR: tuple[str, ...] = (
    "anota:", "anota ", "toma nota", "guarda nota",
    "añade una nota", "agrega una nota", "escribe una nota",
    "apunta:", "apunta ", "nota rápida", "guarda esto:",
)

PATRONES_NOTA_LEER: tuple[str, ...] = (
    "muéstrame mis notas", "muéstrame las notas",
    "mis notas", "ver notas", "leer notas",
    "qué notas tengo", "que notas tengo",
    "muestra mis notas", "cuáles son mis notas",
    "cuales son mis notas", "dame mis notas",
)

PATRONES_NOTA_BORRAR: tuple[str, ...] = (
    "borra la última nota", "elimina la nota",
    "borra la nota", "eliminar nota",
    "borra la ultima nota", "quita la última nota",
    "borra mi última nota",
)

PATRONES_NOTA_BUSCAR: tuple[str, ...] = (
    "busca en mis notas", "buscar en notas",
    "busca en notas", "encuentra en notas",
    "busca mis notas", "filtra mis notas",
)

# ─── WiFi ─────────────────────────────────────────────────────────
PATRONES_WIFI: tuple[str, ...] = (
    "wifi", "wi-fi", "red inalámbrica", "red inalambrica",
    "internet", "conexión wifi", "conexion wifi",
)

PATRONES_WIFI_ACTIVAR: tuple[str, ...] = (
    "activa", "enciende", "activar", "encender", "conecta el",
    "prende el wifi", "prende", "habilita",
)

PATRONES_WIFI_DESACT: tuple[str, ...] = (
    "desactiva", "apaga", "desactivar", "apagar",
    "deshabilita", "corta el wifi", "desconecta el wifi",
)

PATRONES_WIFI_LISTAR: tuple[str, ...] = (
    "listar", "redes", "qué redes", "que redes",
    "ver redes", "cuáles redes", "cuales redes",
    "redes disponibles", "busca redes",
)

# ─── Bluetooth ────────────────────────────────────────────────────
PATRONES_BLUETOOTH: tuple[str, ...] = ("bluetooth", "bluet")
PATRONES_BT_ACTIVAR: tuple[str, ...] = ("activa", "enciende", "activar", "encender", "habilita")
PATRONES_BT_DESACT: tuple[str, ...] = ("desactiva", "apaga", "desactivar", "apagar", "deshabilita")
PATRONES_BT_ABRIR: tuple[str, ...] = ("abre", "abrir", "gestor", "configuración", "configuracion")

# ─── Energía ──────────────────────────────────────────────────────
PATRONES_SUSPENDER: tuple[str, ...] = (
    "suspende", "suspender", "hiberna", "hibernar",
    "pon en suspensión", "modo suspensión",
)

PATRONES_APAGAR: tuple[str, ...] = (
    "apaga el equipo", "apagar el equipo", "apaga el pc",
    "apaga el computador", "apaga la computadora",
    "apaga el sistema", "apagar el sistema",
    "apaga la máquina", "apaga la maquina",
)

PATRONES_REINICIAR: tuple[str, ...] = (
    "reinicia el equipo", "reiniciar el equipo", "reinicia el pc",
    "reinicia el computador", "reinicia el sistema",
    "reiniciar", "reboot", "reinicia la máquina",
)

# ─── Búsqueda web ─────────────────────────────────────────────────
PATRONES_BUSCAR_GOOGLE: tuple[str, ...] = (
    "busca en google", "buscar en google", "googlea",
    "busca google", "búscame en google", "buscame en google",
    "abre google y busca",
)

PATRONES_BUSCAR_YOUTUBE: tuple[str, ...] = (
    "busca en youtube", "buscar en youtube", "busca en you tube",
    "pon en youtube", "busca youtube", "búscame en youtube",
    "buscame en youtube", "busca un video de",
)

PATRONES_BUSCAR_WIKI: tuple[str, ...] = (
    "busca en wikipedia", "buscar en wikipedia",
    "qué es según wikipedia", "que es segun wikipedia",
    "wikipedia sobre",
)

# ─── IA y modelos ─────────────────────────────────────────────────
PATRONES_IA_ESTADO: tuple[str, ...] = (
    "qué ia", "que ia", "estado de las ia", "ias disponibles",
    "qué ia estás usando", "que ia estas usando",
    "qué inteligencia", "que inteligencia",
    "estado de la ia", "qué ia tengo activa",
)

PATRONES_TOKENS: tuple[str, ...] = (
    "tokens usados", "cuántos tokens", "cuantos tokens",
    "uso de tokens", "reporte de tokens", "consumo de tokens",
    "cuánto he gastado", "cuanto he gastado",
)

PATRONES_CAMBIAR_IA: tuple[str, ...] = (
    "cambia a ", "cambia la ia a ", "activa ia ",
    "usa la ia ", "cambia la inteligencia a ",
    "quiero usar ", "activa ",
)

PATRONES_MODELO_OLL: tuple[str, ...] = (
    "cambia el modelo a ", "cambia el modelo ollama a ",
    "usa el modelo ", "usa ollama ", "cambia modelo a ",
)

PATRONES_MODELOS_LIST: tuple[str, ...] = (
    "qué modelos hay", "que modelos hay",
    "modelos disponibles", "listar modelos",
    "qué modelos tienes", "que modelos tienes",
    "qué modelos de ollama", "que modelos de ollama",
)

# ─── WhatsApp ─────────────────────────────────────────────────────
PATRONES_WA_ABRIR: tuple[str, ...] = ("abre whatsapp", "abrir whatsapp", "ejecuta whatsapp")
PATRONES_WA_ESTADO: tuple[str, ...] = ("estado whatsapp", "whatsapp conectado")
PATRONES_WA_CERRAR: tuple[str, ...] = ("cierra whatsapp", "cerrar whatsapp")

# ─── Funcionalidades (ayuda por voz) ──────────────────────────────
PATRONES_FUNCIONES_TODAS: tuple[str, ...] = (
    "funcionalidades totales", "todas las funcionalidades",
    "qué puedes hacer todo", "ayuda completa",
    "funciones totales", "todo lo que puedes hacer",
    "dame todo", "dime todo lo que sabes hacer",
)

PATRONES_FUNCIONES_GRUPOS: tuple[str, ...] = (
    "funcionalidades por grupos", "grupos de funciones",
    "qué grupos hay", "funciones por grupos",
    "qué categorías tienes", "que categorias tienes",
    "qué puedes hacer", "que puedes hacer",
    "ayuda", "ayúdame", "ayudame",
)

# ════════════════════════════════════════════════════════════════════
# GRUPOS DE FUNCIONALIDADES
# ════════════════════════════════════════════════════════════════════
GRUPOS_FUNCIONALIDADES: dict[str, dict] = {
    "apps": {
        "nombre": "Apps y archivos",
        "descripcion": "Abrir aplicaciones, carpetas y buscar archivos",
        "comandos": [
            "abre firefox / chrome / código / terminal / vlc",
            "ejecuta la calculadora / gimp / telegram",
            "abre la carpeta documentos / descargas / imágenes",
            "qué hay en documentos",
            "muéstrame los PDFs de descargas",
            "busca cv en documentos",
        ],
    },
    "web": {
        "nombre": "Búsqueda web",
        "descripcion": "Buscar en Google, YouTube y Wikipedia",
        "comandos": [
            "busca en google recetas colombianas",
            "googlea el precio del dólar",
            "busca en youtube música vallenata",
            "pon en youtube una canción de Carlos Vives",
            "busca en wikipedia inteligencia artificial",
        ],
    },
    "clima": {
        "nombre": "Clima",
        "descripcion": "Clima actual y pronóstico por ciudad",
        "comandos": [
            "cómo está el clima",
            "clima en medellín / bogotá / nueva york",
            "temperatura en cali",
            "pronóstico para mañana",
            "va a llover hoy",
        ],
    },
    "wifi": {
        "nombre": "WiFi y red",
        "descripcion": "Controlar la conexión WiFi",
        "comandos": [
            "activa el wifi / desactiva el wifi",
            "listar redes wifi / redes disponibles",
            "estado del wifi",
            "conéctame a NombreRed",
        ],
    },
    "bluetooth": {
        "nombre": "Bluetooth",
        "descripcion": "Controlar el Bluetooth",
        "comandos": [
            "activa bluetooth / desactiva bluetooth",
            "estado bluetooth",
            "abre el gestor bluetooth",
        ],
    },
    "whatsapp": {
        "nombre": "WhatsApp Web",
        "descripcion": "Enviar y leer mensajes de WhatsApp",
        "comandos": [
            "abre whatsapp",
            "manda whatsapp a Mamá: ya llegué",
            "manda mensaje a Juan: nos vemos a las 3",
            "lee mis mensajes de Pedro",
            "recuérdame por whatsapp en 1 hora a Ana: llamar",
        ],
    },
    "recordatorios": {
        "nombre": "Recordatorios",
        "descripcion": "Crear y gestionar recordatorios — se restauran al reiniciar Jarvis",
        "comandos": [
            "recuérdame en 10 minutos llamar a mamá",
            "ponme un recordatorio en 2 horas y 30 minutos la reunión",
            "avísame en media hora salir",
            "qué recordatorios tengo / qué tengo pendiente",
            "cancela el recordatorio",
        ],
    },
    "notas": {
        "nombre": "Notas rápidas",
        "descripcion": "Guardar y consultar notas por voz",
        "comandos": [
            "anota: comprar leche",
            "apunta: llamar al médico mañana",
            "muéstrame mis notas",
            "busca en mis notas leche",
            "borra la última nota",
        ],
    },
    "ia": {
        "nombre": "IA y modelos",
        "descripcion": "Cambiar la IA activa y consultar uso de tokens",
        "comandos": [
            "cambia a groq / gemini / anthropic / ollama / auto",
            "qué ia está activa / estado de las ia",
            "cuántos tokens usé / reporte de tokens",
            "cambia el modelo a phi3:mini",
            "qué modelos hay",
        ],
    },
    "codigo": {
        "nombre": "Generación de código",
        "descripcion": "Genera código con IA — se copia al portapapeles y se pega en VSCode",
        "comandos": [
            "escribe una función python para leer un CSV",
            "genera un script bash para hacer backup",
            "crea un componente react de login",
            "implementa un algoritmo de ordenamiento en javascript",
            "escribe una consulta SQL para buscar usuarios activos",
        ],
    },
    "sistema": {
        "nombre": "Sistema",
        "descripcion": "Volumen, hora, fecha y estado de recursos",
        "comandos": [
            "sube / baja el volumen / silencia / volumen al máximo",
            "cómo está el sistema / cuánta RAM",
            "qué hora es / qué día es / fecha de hoy",
        ],
    },
    "energia": {
        "nombre": "Energía",
        "descripcion": "Apagar, reiniciar o suspender el equipo",
        "comandos": [
            "apaga el equipo / reinicia el equipo",
            "suspende el equipo",
        ],
    },
}


# ════════════════════════════════════════════════════════════════════
# FUNCIONES DE AYUDA
# ════════════════════════════════════════════════════════════════════

def ayuda_grupos() -> str:
    """
    Lista los grupos disponibles con descripción breve.
    Diseñada para ser leída por voz: sin emojis en el texto hablado,
    pero con formato claro en consola.
    """
    lineas = [f"Tengo {len(GRUPOS_FUNCIONALIDADES)} grupos de funcionalidades:"]
    for g in GRUPOS_FUNCIONALIDADES.values():
        lineas.append(f"  {g['nombre']}: {g['descripcion']}")
    lineas.append("Di 'funcionalidades de [grupo]' para ver los comandos de ese grupo.")
    lineas.append("Di 'funcionalidades totales' para ver todo de una vez.")
    return "\n".join(lineas)


def ayuda_grupo(nombre_grupo: str) -> str:
    """
    Devuelve los comandos de un grupo específico.
    Acepta nombre parcial: "clim" encuentra "clima".
    """
    nombre_lower = nombre_grupo.lower().strip()

    # Búsqueda exacta por clave primero
    grupo = GRUPOS_FUNCIONALIDADES.get(nombre_lower)

    # Búsqueda parcial por clave o nombre del grupo
    if not grupo:
        for clave, g in GRUPOS_FUNCIONALIDADES.items():
            if nombre_lower in clave or nombre_lower in g["nombre"].lower():
                grupo = g
                break

    if not grupo:
        claves = ", ".join(GRUPOS_FUNCIONALIDADES.keys())
        return f"No encontré el grupo '{nombre_grupo}'. Grupos disponibles: {claves}"

    lineas = [f"Grupo '{grupo['nombre']}': {grupo['descripcion']}", "Comandos de ejemplo:"]
    for cmd in grupo["comandos"]:
        lineas.append(f"  {cmd}")
    return "\n".join(lineas)


def ayuda_total() -> str:
    """
    Devuelve TODOS los comandos de todos los grupos.
    Útil para imprimir en consola; es largo para leer por voz.
    """
    lineas = ["Funcionalidades completas de Jarvis:"]
    for g in GRUPOS_FUNCIONALIDADES.values():
        lineas.append(f"\n{g['nombre']} ({g['descripcion']}):")
        for cmd in g["comandos"]:
            lineas.append(f"  {cmd}")
    return "\n".join(lineas)
