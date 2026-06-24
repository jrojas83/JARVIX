# config.py — Jarvis v5
# Las API keys se leen del archivo .env (nunca hardcodeadas aquí).
# Para configurar: cp .env.example .env  y rellena tus claves.

import os
from dotenv import load_dotenv

# Carga el archivo .env desde la carpeta del proyecto
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(_BASE_DIR, ".env"))

HOME = os.path.expanduser("~")

# ─── API Keys — leídas desde .env (ya no usadas para IAs online) ─────────────────────────────
# Nota: Las IAs online han sido eliminadas. Solo se soporta Ollama (IA local).
GROQ_API_KEY        = ""  # No usado
GEMINI_API_KEY      = ""  # No usado
ANTHROPIC_API_KEY   = ""  # No usado
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY", "")

# ─── Preferencias ─────────────────────────────────────────────
CIUDAD_DEFAULT     = os.getenv("CIUDAD_DEFAULT", "Cali,CO")
MODELO             = os.getenv("MODELO_OLLAMA", "qwen2.5:3b")
PALABRA_ACTIVACION = os.getenv("PALABRA_ACTIVACION", "jarvis")

# ─── Perfil de usuario ────────────────────────────────────────
NOMBRE_USUARIO    = os.getenv("NOMBRE_USUARIO", "").strip()
HORARIO_TRABAJO   = os.getenv("HORARIO_TRABAJO", "8-18").strip()
GENERO_ASISTENTE  = os.getenv("GENERO_ASISTENTE", "masculino").strip().lower()

def _hora_en_rango(hora_actual: int, rango: str) -> bool:
    """Devuelve True si hora_actual está dentro del rango HH-HH."""
    try:
        inicio, fin = (int(x) for x in rango.split("-"))
        return inicio <= hora_actual < fin
    except Exception:
        return False

def saludo_contextual() -> str:
    """Genera saludo según hora y perfil del usuario. Sin IA, solo lógica."""
    from datetime import datetime
    hora = datetime.now().hour
    nombre = f", {NOMBRE_USUARIO}" if NOMBRE_USUARIO else ""
    adj_activo = "activa" if GENERO_ASISTENTE == "femenino" else "activo"

    if 5 <= hora < 12:
        base = f"Buenos días{nombre}"
    elif 12 <= hora < 19:
        base = f"Buenas tardes{nombre}"
    else:
        base = f"Buenas noches{nombre}"

    # Contexto laboral
    if _hora_en_rango(hora, HORARIO_TRABAJO):
        ctx = " — en horario de trabajo"
    else:
        ctx = ""

    return f"Jarvis {adj_activo}. {base}{ctx}. ¿En qué te ayudo?"

# ─── Ollama ───────────────────────────────────────────────────
URL_OLLAMA = "http://localhost:11434/api/generate"

# ─── Catálogo de modelos Ollama ──────────────────────────────
# Organizados por RAM requerida. Para Intel N100 / 8 GB RAM:
# recomendamos los de la categoría "ligeros" o "balanceados".
#
# LIGEROS (RAM libre < 3 GB)
#   smollm2:1.7b      ~1.1 GB  Diseñado para hardware limitado
#   qwen2.5:1.5b      ~1.0 GB  Más liviano viable con buena calidad
#   deepseek-coder:1.3b ~0.8 GB Solo código — muy eficiente
#   gemma2:2b         ~1.6 GB  Razona bien, bueno para español
#
# BALANCEADOS (RAM libre 3-5 GB) — recomendados para N100
#   qwen2.5:3b        ~1.9 GB  Balance calidad/velocidad ← DEFAULT
#   phi3:mini         ~2.3 GB  Excelente calidad para su tamaño (Microsoft)
#   phi3.5:mini       ~2.4 GB  Versión mejorada de phi3
#   llama3.2:3b       ~2.0 GB  Bueno en español (Meta)
#   deepseek-coder:6.7b ~3.8 GB Solo código — alta calidad
#
# POTENTES (RAM libre > 5 GB)
#   mistral:7b        ~4.1 GB  Mejor calidad general
#   qwen2.5:7b        ~4.7 GB  Excelente para código
#   llama3.1:8b       ~4.7 GB  Multilingüe, muy bueno

MODELOS_OLLAMA = [
    # Ligeros — para hardware muy limitado
    "smollm2:1.7b",
    "qwen2.5:1.5b",
    "deepseek-coder:1.3b",
    "gemma2:2b",
    # Balanceados — recomendados para Intel N100 / 8 GB RAM
    "qwen2.5:3b",        # default
    "phi3:mini",
    "phi3.5:mini",
    "llama3.2:3b",
    "deepseek-coder:6.7b",
    # Potentes — para equipos con más recursos
    "mistral:7b",
    "qwen2.5:7b",
    "llama3.1:8b",
]

# MODELO_ONLINE eliminado - ya no se soportan IAs online

# ─── Voz ──────────────────────────────────────────────────────
TIMEOUT_ESCUCHA = 5
IDIOMA_VOZ      = "es-ES"

# ─── Aplicaciones permitidas ──────────────────────────────────
# Formato: { "apodo_en_español": "comando_linux" }
# Para añadir más apps: agrega aquí y listo.
APPS_PERMITIDAS = {
    # Navegadores
    "navegador":        "firefox",
    "firefox":          "firefox",
    "chrome":           "google-chrome",
    "chromium":         "chromium-browser",
    # Editores / IDEs
    "codigo":           "code",
    "vscode":           "code",
    "editor":           "code",
    "gedit":            "gedit",
    "mousepad":         "mousepad",
    # Gestión de archivos
    "archivos":         "thunar",
    "thunar":           "thunar",
    "nautilus":         "nautilus",
    # Terminal
    "terminal":         "xfce4-terminal",
    "konsole":          "konsole",
    "bash":             "xfce4-terminal",
    # Ofimática
    "libreoffice":      "libreoffice",
    "writer":           "libreoffice --writer",
    "calc":             "libreoffice --calc",
    "impress":          "libreoffice --impress",
    # Multimedia
    "vlc":              "vlc",
    "musica":           "rhythmbox",
    "video":            "vlc",
    "camara":           "cheese",
    # Comunicación
    "telegram":         "telegram-desktop",
    "discord":          "discord",
    "whatsapp":         "firefox --new-window https://web.whatsapp.com",
    "correo":           "thunderbird",
    # Utilidades
    "calculadora":      "gnome-calculator",
    "captura":          "gnome-screenshot",
    "monitor":          "gnome-system-monitor",
    "configuracion":    "gnome-control-center",
    "bluetooth":        "blueman-manager",
    "gimp":             "gimp",
    # XFCE
    "xfce":             "xfce4-settings-manager",
}

# ─── Carpetas conocidas ───────────────────────────────────────
CARPETAS = {
    "proyectos":    f"{HOME}/Proyectos",
    "documentos":   f"{HOME}/Documentos",
    "descargas":    f"{HOME}/Descargas",
    "escritorio":   f"{HOME}/Escritorio",
    "imagenes":     f"{HOME}/Imágenes",
    "fotos":        f"{HOME}/Imágenes",
    "musica":       f"{HOME}/Música",
    "videos":       f"{HOME}/Videos",
    "trabajo":      f"{HOME}/Documentos/Trabajo",
    "facturas":     f"{HOME}/Documentos/Facturas",
    "home":         HOME,
    "inicio":       HOME,
    "personal":     f"{HOME}/Documentos/Personal",
}

# ─── Archivos conocidos por apodo ─────────────────────────────
ARCHIVOS_CONOCIDOS = {
    "presupuesto":  f"{HOME}/Documentos/Trabajo/presupuesto_2025.ods",
    "curriculum":   f"{HOME}/Documentos/CV_actualizado.odt",
    "mi web":       f"{HOME}/Proyectos/mi-web",
    "notas":        f"{HOME}/Documentos/notas.txt",
    "inventario":   f"{HOME}/Documentos/inventario.ods",
}

# ─── URLs de acceso rápido ────────────────────────────────────
URLS_WEB = {
    "whatsapp":     "https://web.whatsapp.com",
    "gmail":        "https://mail.google.com",
    "correo web":   "https://mail.google.com",
    "youtube":      "https://www.youtube.com",
    "google":       "https://www.google.com",
    "maps":         "https://maps.google.com",
    "mapa":         "https://maps.google.com",
    "github":       "https://github.com",
    "translate":    "https://translate.google.com",
    "traductor":    "https://translate.google.com",
    "chatgpt":      "https://chat.openai.com",
    "claude":       "https://claude.ai",
    "drive":        "https://drive.google.com",
    "calendar":     "https://calendar.google.com",
    "calendario":   "https://calendar.google.com",
    "meet":         "https://meet.google.com",
    "spotify":      "https://open.spotify.com",
    "netflix":      "https://www.netflix.com",
    "linkedin":     "https://www.linkedin.com",
    "wikipedia":    "https://es.wikipedia.org",
    "noticias":     "https://news.google.com",
}
