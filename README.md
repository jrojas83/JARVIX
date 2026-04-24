# 🤖 Jarvis v8 — Asistente modular (intents + plugins + async)

Asistente personal por voz y texto para Linux Ubuntu/Debian.
Controla tu escritorio, consulta el clima, envía mensajes de WhatsApp y genera código con IA.

## Novedades en v8 (gran salto)

- **Sistema de intents (no comandos rígidos)**: entiende sinónimos y formas naturales.
  - Ejemplo (misma intención “música”):
    - “abre spotify”
    - “pon música”
    - “quiero escuchar algo”
    - “abre mi reproductor”
- **Arquitectura modular real**: el entrypoint `jarvis.py` se mantiene, pero todo el runtime vive en `jarvis_core/`.
- **Event-driven / async (anti-congelamientos)**:
  - `asyncio` + ejecución en background para IO/SDKs bloqueantes
  - cola/bus de eventos (`jarvis_core/events/`)
  - tareas concurrentes y cancelación (cuando “first model wins”)
- **Failover inteligente ultra rápido**:
  - timeouts + retries + circuit breaker
  - strategy **“first model wins”**: en `auto` consulta proveedores en paralelo y usa el primero que responde bien
- **Memoria real** (persistente) además de conversación:
  - preferencias
  - alias/comandos aprendidos
  - macros (“modos”) como “modo trabajo”
  - archivo: `~/.jarvis_memory.json`
- **Agent mode (primer corte)**:
  - dispara con `agente: <objetivo>`
  - genera un plan JSON con IA (base para flujos tipo: “busca → resume → guarda → envía”)

## Novedades en v7 (histórico)

| Módulo | Qué hace |
|---|---|
| `cache.py` | Caché en memoria con TTL. Respuestas repetidas de IA no vuelven a llamar a la API durante 5 minutos. Muestra `[CACHÉ]` en consola cuando usa respuesta guardada. |
| `consola.py` | Colores ANSI y métricas de tiempo. Cada respuesta muestra la fuente y latencia: `[GROQ 820ms]`, `[OLLAMA 14s]`, `[PATRÓN]`, `[PLUGIN]`. Sin dependencias externas. |
| `diagnostico.py` | `python jarvis.py test` verifica todo: Ollama, cada API key (petición real), espeak, micrófono, plugins, SQLite y caché. Con tiempo de respuesta por componente. |
| `voz.py` | Modo `--espera` robusto con backoff exponencial si el micrófono falla (2s → 4s → ... → 30s máx). Nunca cae en silencio. |
| `config.py` | Perfil de usuario: `NOMBRE_USUARIO`, `HORARIO_TRABAJO`, `GENERO_ASISTENTE`. Saludo contextual sin IA. |
| `plugins/` | Sistema de plugins: cada `.py` en la carpeta se carga automáticamente. Añadir un comando nuevo = copiar un archivo. El core no se toca. |

### Nuevas variables `.env`

```env
NOMBRE_USUARIO=Andrés
HORARIO_TRABAJO=8-18
GENERO_ASISTENTE=masculino
```

### Nuevos comandos de consola

```
test        → autodiagnóstico completo
cache       → estadísticas del caché
plugins     → plugins instalados y sus patrones
```

### Crear un plugin (ejemplo mínimo)

```python
# plugins/mi_plugin.py
NOMBRE      = "mi_plugin"
DESCRIPCION = "Hace algo útil"
PATRONES    = ["activa X", "ejecuta X"]

def ejecutar(orden: str, params: dict) -> str:
    return "Respuesta de texto"
```

Reinicia Jarvis — el plugin aparece automáticamente.

### Plugins v8: intents desde plugins (sin tocar el core)

Un plugin ahora también puede **registrar intents** (sinónimos/phrases) para cambiar por completo la UX sin editar `jarvis_core/`.

Ejemplo: `plugins/spotify.py` (incluido):

- Puede exponer `register_intents(registry)`
- O declarar `INTENTS = [Intent(...), ...]`

---

---

## ✨ Qué puede hacer

| Función | Ejemplo de comando |
|---|---|
| 🖥 Abrir apps | `abre firefox`, `abre el editor de código` |
| 📁 Gestionar archivos | `qué hay en documentos`, `busca el cv en descargas` |
| 🔍 Buscar en web | `busca en youtube música vallenata` |
| 🌤 Clima | `clima en medellín`, `pronóstico para mañana` |
| 📱 WhatsApp Web | `manda whatsapp a Mamá: ya llegué` |
| ⏰ Recordatorios | `recuérdame en 30 minutos tomar el medicamento` |
| 📝 Notas rápidas | `anota: comprar leche` |
| 🤖 Generar código | `escribe una función python para leer un CSV` |
| 🔊 Sistema | `sube el volumen`, `cómo está el sistema` |
| 🗣 Ayuda por voz | `funcionalidades por grupos`, `funcionalidades totales` |

---

## 🚀 Instalación rápida

```bash
# 1. Clonar o descargar el proyecto
git clone https://github.com/TU_USUARIO/jarvis.git
cd jarvis

# 2. Configurar las API keys
cp .env.example .env
# Edita .env con tu editor y añade tus claves (ver sección Configuración)

# 3. Instalar todo automáticamente
bash instalar.sh
```

El instalador:
- Crea un entorno virtual Python (`.venv`)
- Instala todas las dependencias desde `requirements.txt`
- Configura tu archivo `.env` con las API keys
- Descarga el modelo de IA local (Ollama)
- Crea alias de consola y acceso directo en el escritorio

---

## ⚙️ Configuración

Las API keys se guardan en el archivo `.env` (nunca en Git).

```bash
cp .env.example .env
```

Edita `.env`:

```env
GROQ_API_KEY=tu_clave         # gratis en console.groq.com
GEMINI_API_KEY=tu_clave       # gratis en aistudio.google.com/app/apikey
ANTHROPIC_API_KEY=tu_clave    # en console.anthropic.com
OPENWEATHER_API_KEY=tu_clave  # gratis en openweathermap.org/api

CIUDAD_DEFAULT=Cali,CO        # ciudad para el clima
IA_PREFERIDA=auto             # auto | groq | gemini | anthropic | ollama
```

**No necesitas todas las claves.** Con solo una ya funciona la IA online.
Sin ninguna, usa Ollama local (requiere tenerlo instalado).

---

## ▶️ Uso

```bash
python jarvis.py              # modo texto
python jarvis.py --voz        # modo voz continua
python jarvis.py --espera     # di "jarvis" para activar

# Con alias (tras reiniciar terminal):
jarvis
jarvis-voz
jarvis-espera
```

---

## 🗣 Sistema de ayuda por voz

Jarvis puede explicarte sus propias funciones por voz:

```
funcionalidades por grupos      → lista todos los grupos disponibles
funcionalidades de clima        → comandos del grupo "clima"
funcionalidades de whatsapp     → comandos del grupo "whatsapp"
funcionalidades totales         → todos los comandos de todos los grupos
ingresar a recordatorios        → comandos del grupo "recordatorios"
```

---

## 📦 Estructura del proyecto

```
jarvis/
├── jarvis.py          # Entrypoint compatible → delega al core (v8)
├── jarvis_core/       # Core modular (v8)
│   ├── app.py         # Bucle principal async + event bus + memoria real
│   ├── ai/            # Orquestación IA (timeouts/retries/circuit breaker/first-wins)
│   ├── intents/       # Intent registry + builtins + normalización
│   ├── plugins/       # Loader de intents desde plugins/
│   ├── events/        # EventBus (cola async)
│   ├── memory/        # Memoria persistente (prefs/macros/alias)
│   └── agent/         # Agent mode (planificación inicial)
├── acciones.py        # Dispatcher de acciones
├── intenciones.py     # Patrones de detección y grupos de funcionalidades
├── config.py          # Configuración (lee de .env)
├── logger.py          # Logging centralizado → ~/.jarvis.log
├── recordatorios.py   # Recordatorios SQLite + notas
├── clima.py           # OpenWeatherMap
├── whatsapp.py        # WhatsApp Web (Selenium)
├── ia_online.py       # Multi-IA: Groq, Gemini, Anthropic
├── voz.py             # Entrada/salida de voz
├── instalar.sh        # Instalador automático
├── requirements.txt   # Dependencias Python
├── .env.example       # Plantilla de configuración (sí se sube a Git)
├── .env               # Tu configuración real (NO se sube a Git)
├── .gitignore         # Excluye .env y archivos personales
└── README.md
```

---

## 🔄 Flujo de IA

```
Orden del usuario
      │
      ▼
plugins → intents → cache/alias/macro → IA
      │
IA Orchestrator (v8): first model wins + circuit breaker + retries + timeouts
      │
      ▼
hablar(respuesta)    ← Texto → voz (espeak/pyttsx3)
```

---

## 🛠 Para desarrolladores: añadir funcionalidades

Jarvis está diseñado para ser extendido sin romper nada existente.

### Añadir un nuevo “comando” en v8 (recomendado): intent + plugin

- Crea un archivo en `plugins/` (ej: `plugins/browser.py`, `plugins/spotify.py`)
- Registra intents en el plugin (sinónimos, frases naturales)
- Implementa `ejecutar()` si quieres compatibilidad v7/v8

Con esto agregas funciones nuevas **sin tocar el core**.

### Añadir un nuevo comando (legacy v7)

**Paso 1:** En `intenciones.py`, añade los patrones:
```python
PATRONES_MI_COMANDO = ["frase 1", "frase 2", "variante"]
```

Si crea un grupo nuevo, agrégalo a `GRUPOS_FUNCIONALIDADES`:
```python
"mi_grupo": {
    "nombre": "Mi funcionalidad",
    "descripcion": "Qué hace",
    "comandos": ["ejemplo 1", "ejemplo 2"]
}
```

**Paso 2:** En `acciones.py`, crea la función:
```python
def accion_mi_comando(param1, param2=""):
    # Tu lógica aquí
    return "Texto que Jarvis dirá en voz alta"
```

**Paso 3:** En `jarvis.py`, registra la detección en `procesar_sin_ia()`:
```python
from intenciones import PATRONES_MI_COMANDO

if any(p in o for p in PATRONES_MI_COMANDO):
    return {"accion": "mi_comando", "parametros": {"param1": "valor"}}
```

**Paso 4:** En `jarvis.py`, registra la ejecución en el `dispatcher` de `ejecutar()`:
```python
"mi_comando": lambda: accion_mi_comando(params.get("param1", ""), params.get("param2", "")),
```

Eso es todo. Sin tocar el resto del código.

---

## 📊 Logs y base de datos

| Archivo | Contenido |
|---|---|
| `~/.jarvis.log` | Registro de eventos, errores y acciones |
| `~/.jarvis.db` | Recordatorios, notas y uso de tokens (SQLite) |
| `memoria.json` | Historial de conversación (últimas 40 interacciones) |
| `~/.jarvis_memory.json` | Memoria persistente v8: prefs/macros/alias |

Para ver los logs en tiempo real:
```bash
tail -f ~/.jarvis.log
```

---

## 🔐 Seguridad

- Las API keys **nunca** se escriben en el código fuente
- El archivo `.env` está en `.gitignore` y **no se sube a Git**
- Para colaborar: comparte solo `.env.example` con los campos vacíos

---

## 📋 Requisitos del sistema

- Linux Ubuntu / Debian / Mint
- Python 3.10+
- Firefox (para WhatsApp Web)
- `espeak` o `pyttsx3` (para voz)
- Ollama (opcional, para IA local sin internet)
- Micrófono (para modo voz)
