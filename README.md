# 🤖 JARVIX — Asistente Personal de Escritorio con IA Local

> Asistente modular, autónomo y 100% funcional sin internet.  
> Voz · Texto · OCR · Rutinas proactivas · Plugins · Ollama · Linux

---

## Tabla de Contenidos

<details>
<summary><strong>📦 Introducción</strong></summary>

- [1. Descripción General](#1-descripción-general)
- [2. Objetivo del Proyecto](#2-objetivo-del-proyecto)
- [3. Características Principales](#3-características-principales)
- [4. Tecnologías Utilizadas](#4-tecnologías-utilizadas)

</details>

<details>
<summary><strong>🚀 Instalación y Configuración</strong></summary>

- [5. Requisitos del Sistema](#5-requisitos-del-sistema)
- [6. Instalación](#6-instalación)
- [7. Variables de Entorno (.env)](#7-variables-de-entorno-env)
- [8. Primer Inicio](#8-primer-inicio)
- [9. Modo 100% Offline](#9-modo-100-offline)

</details>

<details>
<summary><strong>🗣 Uso</strong></summary>

- [10. Uso Básico](#10-uso-básico)
- [11. Comandos Disponibles](#11-comandos-disponibles)
- [12. Sistema de Voz](#12-sistema-de-voz)

</details>

<details>
<summary><strong>🧠 Sistemas Internos</strong></summary>

- [13. Sistema de Memoria](#13-sistema-de-memoria)
- [14. Sistema de Visión (OCR)](#14-sistema-de-visión-ocr)
- [15. Sistema de Autonomía](#15-sistema-de-autonomía)
- [16. Sistema de Plugins](#16-sistema-de-plugins)
- [17. Sistema de Caché](#17-sistema-de-caché)
- [18. Sistema de Logs](#18-sistema-de-logs)
- [19. Sistema de Eventos (Event Bus)](#19-sistema-de-eventos-event-bus)

</details>

<details>
<summary><strong>🔌 Integraciones</strong></summary>

- [20. Integración con Ollama (IA local)](#20-integración-con-ollama-ia-local)
- [21. Integración con IAs en Línea](#21-integración-con-ias-en-línea)
- [22. Integración con APIs Externas](#22-integración-con-apis-externas)

</details>

<details>
<summary><strong>🏗 Arquitectura</strong></summary>

- [23. Arquitectura General](#23-arquitectura-general)
- [24. Estructura de Carpetas](#24-estructura-de-carpetas)
- [25. Flujo Interno del Sistema](#25-flujo-interno-del-sistema)
- [26. Explicación de Módulos](#26-explicación-de-módulos)

</details>

<details>
<summary><strong>🛠 Para Desarrolladores</strong></summary>

- [27. Crear un Plugin](#27-crear-un-plugin)
- [28. Crear una Acción](#28-crear-una-acción)
- [29. Crear un Intent](#29-crear-un-intent)
- [30. Crear una Rutina Personalizada](#30-crear-una-rutina-personalizada)

</details>

<details>
<summary><strong>🔧 Configuración Avanzada</strong></summary>

- [31. Configuración de Modelos IA](#31-configuración-de-modelos-ia)
- [32. Configuración de Voz](#32-configuración-de-voz)
- [33. Configuración de OCR y Visión](#33-configuración-de-ocr-y-visión)
- [34. Configuración de Rutinas y Autonomía](#34-configuración-de-rutinas-y-autonomía)

</details>

<details>
<summary><strong>🐛 Solución de Problemas</strong></summary>

- [35. Errores Comunes](#35-errores-comunes)
- [36. Problemas de Voz](#36-problemas-de-voz)
- [37. Problemas de Visión y OCR](#37-problemas-de-visión-y-ocr)
- [38. Problemas con Ollama](#38-problemas-con-ollama)
- [39. Problemas con IAs Online](#39-problemas-con-ias-online)
- [40. Problemas de Rendimiento](#40-problemas-de-rendimiento)
- [41. FAQ](#41-faq)

</details>

<details>
<summary><strong>📋 Proyecto</strong></summary>

- [42. Seguridad y Permisos](#42-seguridad-y-permisos)
- [43. Rendimiento y Optimización](#43-rendimiento-y-optimización)
- [44. Testing y Diagnóstico](#44-testing-y-diagnóstico)
- [45. Roadmap](#45-roadmap)
- [46. Changelog](#46-changelog)
- [47. Licencia y Créditos](#47-licencia-y-créditos)

</details>

---

## 1. Descripción General

**JARVIX** es un asistente personal de escritorio para Linux, controlable por voz y texto, diseñado para funcionar **completamente sin internet** gracias a Ollama y OCR local. Puede hablar contigo, ver lo que hay en tu pantalla, recordar tus rutinas, proponer acciones de forma proactiva y extenderse con plugins sin tocar el código base.

No es un chatbot. Es un agente de escritorio que observa, recuerda y actúa.

---

## 2. Objetivo del Proyecto

Crear un asistente de escritorio **ligero, modular y privado** que:

- Funcione **sin internet** en su modo principal (Ollama + OCR local)
- Use IAs en línea como acelerador opcional, no como dependencia
- Sea **extensible por cualquier persona** sin conocer el código interno
- Tenga **memoria real** entre sesiones y rutinas proactivas
- Pueda **ver la pantalla** y proponer ayuda contextual

---

## 3. Características Principales

| Característica | Descripción |
|---|---|
| 🗣 Voz + Texto | Entrada por micrófono o teclado, salida por voz (espeak) |
| 🧠 Multi-IA | Groq, Gemini, Anthropic, Ollama — con failover automático |
| 🏠 100% Offline | Ollama (IA local) + pytesseract (OCR) sin internet |
| 👁 Visión | Lee la pantalla con OCR, detecta ventana activa, propone acciones |
| ⏰ Autonomía | Rutinas proactivas, alerta de inactividad, saludos automáticos |
| 🔌 Plugins | Extiende funciones copiando un archivo `.py` en `/plugins` |
| 💾 Memoria | Persiste preferencias, alias y rutinas entre sesiones |
| ⚡ Caché | Respuestas repetidas sin llamar a la API (TTL configurable) |
| 🔔 Notificaciones | Alertas de escritorio nativas (notify-send) |
| 📊 Diagnóstico | `python jarvis.py test` verifica todos los componentes |

---

## 4. Tecnologías Utilizadas

| Categoría | Tecnología | Uso |
|---|---|---|
| Lenguaje | Python 3.10+ | Core del proyecto |
| IA local | Ollama | Modelo de lenguaje sin internet |
| IA online | Groq, Gemini, Anthropic | Respuestas rápidas con API |
| Voz entrada | SpeechRecognition + PyAudio | Escucha el micrófono |
| Voz salida | espeak / pyttsx3 | Convierte texto a voz |
| OCR | pytesseract + Tesseract | Lee texto de la pantalla |
| Captura pantalla | mss + Pillow | Screenshot local sin GPU |
| Ventana activa | xdotool / wmctrl | Detecta qué app está abierta |
| DB | SQLite | Recordatorios y notas |
| Config | python-dotenv | Variables de entorno |
| Concurrencia | asyncio + threading | Anti-congelamientos |
| Notificaciones | libnotify (notify-send) | Alertas de escritorio |
| WhatsApp | Selenium + Firefox | Automatización web |
| Clima | OpenWeatherMap API | Consulta de clima (opcional) |

---

## 5. Requisitos del Sistema

### Mínimos
- Linux Ubuntu 20.04+ / Debian 11+ / Linux Mint 20+
- Python 3.10+
- 4 GB RAM (8 GB recomendado para modelos Ollama)
- 10 GB espacio en disco (para Ollama + modelo)
- Micrófono (solo si usas modo voz)

### Para funciones específicas
| Función | Requisito adicional |
|---|---|
| IA local | Ollama instalado + modelo descargado |
| Visión / OCR | `tesseract-ocr`, `mss`, `Pillow`, `pytesseract` |
| Detección de ventana | `xdotool` o `wmctrl` |
| WhatsApp | Firefox + selenium |
| Notificaciones desktop | `libnotify-bin` |
| Clima | API key de OpenWeatherMap (gratuita) |

### Compatibilidad de hardware para Ollama
| Hardware | Modelo recomendado | RAM necesaria |
|---|---|---|
| Intel N100 / 8 GB | qwen2.5:3b | ~3 GB |
| Intel i5 / 8 GB | phi3:mini | ~4 GB |
| Intel i7 / 16 GB | mistral:7b | ~8 GB |
| Cualquier con GPU NVIDIA | cualquier 7B | según VRAM |

---

## 6. Instalación

### Instalación rápida (recomendada)

```bash
git clone https://github.com/jrojas83/JARVIX.git
cd JARVIX
bash instalar.sh
```

El instalador hace todo automáticamente:
1. Instala paquetes del sistema (`apt`)
2. Crea entorno virtual Python (`.venv`)
3. Instala dependencias Python (incluyendo visión/OCR)
4. Te pide API keys (todas opcionales)
5. Instala y configura Ollama
6. Descarga el modelo de IA local que elijas
7. Crea alias y acceso directo en el escritorio

### Instalación manual paso a paso

```bash
# 1. Paquetes del sistema
sudo apt update
sudo apt install -y python3 python3-venv python3-dev espeak \
    libnotify-bin xdotool wmctrl tesseract-ocr tesseract-ocr-spa \
    portaudio19-dev libasound2-dev firefox curl

# 2. Entorno virtual
python3 -m venv .venv
source .venv/bin/activate

# 3. Dependencias Python
pip install -r requirements.txt

# 4. Dependencias de visión (offline)
pip install mss Pillow pytesseract

# 5. Copiar configuración
cp .env.example .env
# Editar .env con tus claves

# 6. Ollama
curl -fsSL https://ollama.com/install.sh | sh
ollama serve &
ollama pull qwen2.5:3b
```

---

## 7. Variables de Entorno (.env)

```env
# ── IAs en línea (todas opcionales) ──────────────────────────
GROQ_API_KEY=            # gratis: console.groq.com
GEMINI_API_KEY=          # gratis: aistudio.google.com/app/apikey
ANTHROPIC_API_KEY=       # pago: console.anthropic.com
OPENWEATHER_API_KEY=     # gratis: openweathermap.org/api

# ── IA preferida ──────────────────────────────────────────────
# auto | groq | gemini | anthropic | ollama
IA_PREFERIDA=auto

# ── Ollama (IA local) ─────────────────────────────────────────
MODELO_OLLAMA=qwen2.5:3b
URL_OLLAMA=http://localhost:11434/api/generate

# ── Perfil de usuario ─────────────────────────────────────────
NOMBRE_USUARIO=          # para saludos personalizados
CIUDAD_DEFAULT=Cali,CO   # ciudad para clima
HORARIO_TRABAJO=8-18     # para saludos contextuales
GENERO_ASISTENTE=masculino

# ── Autonomía ─────────────────────────────────────────────────
AUTONOMY_INACTIVIDAD_MIN=60   # minutos sin actividad para alertar (0=off)
```

### Modo sin ninguna clave

Si dejas todas las claves vacías, JARVIX funciona completamente con Ollama. Ver sección [9. Modo 100% Offline](#9-modo-100-offline).

---

## 8. Primer Inicio

```bash
# Activar el entorno virtual
source .venv/bin/activate

# Asegurarse que Ollama está corriendo
ollama serve &

# Iniciar JARVIX
python jarvis.py
```

Al iniciar verás:
```
🤖 JARVIX v9 — modo: texto — IA: auto
Buenos días, [nombre]. ¿En qué te ayudo hoy?

Jarvis ›
```

### Comandos de diagnóstico al primer inicio

```bash
python jarvis.py test        # diagnóstico completo de todos los componentes
```

O desde dentro de JARVIX:
```
> diagnóstico de visión      → verifica OCR y dependencias visuales
> plugins                    → lista plugins cargados
> cache                      → estadísticas de caché
```

---

## 9. Modo 100% Offline

JARVIX funciona completamente sin internet. Esta es su configuración mínima offline:

### Qué funciona sin internet
- ✅ Procesamiento de órdenes con Ollama (IA local)
- ✅ Voz (espeak + SpeechRecognition con modelo local)
- ✅ Visión de pantalla (pytesseract OCR)
- ✅ Detección de ventana activa (xdotool)
- ✅ Recordatorios y notas (SQLite local)
- ✅ Control del sistema (volumen, WiFi, Bluetooth, apps)
- ✅ Autonomía y rutinas proactivas
- ✅ Memoria persistente
- ✅ Todos los plugins locales

### Qué requiere internet
- ❌ Clima (`clima.py` → OpenWeatherMap API)
- ❌ IAs online (Groq, Gemini, Anthropic)
- ❌ WhatsApp Web (requiere conectar Firefox)
- ❌ Búsquedas web

### Configuración para modo offline total

En `.env`:
```env
IA_PREFERIDA=ollama
# dejar vacías: GROQ_API_KEY, GEMINI_API_KEY, ANTHROPIC_API_KEY
```

Asegúrate de tener Ollama corriendo:
```bash
ollama serve
```

### Verificar modo offline

```
> estado de IA
```
JARVIX responde indicando qué IAs están disponibles.

---

## 10. Uso Básico

```bash
python jarvis.py              # modo texto (teclado)
python jarvis.py --voz        # modo voz continua (micrófono siempre activo)
python jarvis.py --espera     # modo espera: di "jarvis" para activar

# Con los alias instalados (terminal nueva):
jarvis
jarvis-voz
jarvis-espera
```

### Ejemplos rápidos

```
> qué hora es
> abre firefox
> clima en bogotá
> recuérdame en 20 minutos tomar agua
> anota: comprar leche
> qué hay en pantalla
> mis rutinas
> estado de IA
```

---

## 11. Comandos Disponibles

### 🖥 Apps y sistema
```
abre firefox / chrome / spotify / code
abre la carpeta documentos / descargas
qué hay en documentos
busca el cv en descargas
sube el volumen / baja el volumen / silencia
cómo está el sistema
suspende el equipo / apaga / reinicia
```

### 🌐 Web y búsqueda
```
busca en google qué es machine learning
busca en youtube música vallenata
busca en wikipedia el big bang
```

### 🌤 Clima
```
clima en medellín
pronóstico para mañana en cali
temperatura en bogotá
```

### 📱 WhatsApp
```
manda whatsapp a Mamá: ya llegué
lee los mensajes de Juan
abre whatsapp
```

### ⏰ Recordatorios
```
recuérdame en 30 minutos tomar el medicamento
recuérdame en 1 hora y 30 minutos la reunión
lista mis recordatorios
cancela los recordatorios
```

### 📝 Notas
```
anota: comprar leche
lee mis notas
borra las notas
busca en mis notas mercado
```

### 🔌 Red y conectividad
```
activa el wifi / desactiva el wifi
lista redes wifi
conecta al wifi MiRed
activa bluetooth / desactiva bluetooth
```

### 👁 Visión de pantalla (offline)
```
qué hay en pantalla          → descripción de ventana + contexto OCR
lee la pantalla              → extrae todo el texto visible (OCR)
analiza la pantalla          → propone ayuda según el contexto
ventana activa               → solo el título de la ventana actual
diagnóstico de visión        → verifica dependencias instaladas
```

### ⏰ Autonomía y rutinas
```
mis rutinas                  → lista todas las rutinas configuradas
activar rutina buenos_dias   → activa el saludo matutino (8:00 lunes-viernes)
desactivar rutina check_tarde
```

### 🤖 IA y modelos
```
estado de IA                 → qué IAs están disponibles
cambia la IA a groq
cambia la IA a ollama
cambia el modelo a phi3:mini
lista los modelos
uso de tokens
```

### 🔧 Diagnóstico
```
python jarvis.py test        → diagnóstico completo desde terminal
diagnóstico de visión        → dentro de JARVIX, verifica OCR
cache                        → estadísticas del caché
plugins                      → lista plugins cargados
```

---

## 12. Sistema de Voz

JARVIX tiene tres modos de operación:

### Modo texto (default)
```bash
python jarvis.py
```
Escribe en la consola. La respuesta se imprime y también se lee en voz alta.

### Modo voz continua
```bash
python jarvis.py --voz
```
El micrófono está siempre activo. JARVIX escucha, procesa y responde por voz.

### Modo espera
```bash
python jarvis.py --espera
```
Escucha constantemente pero solo se activa cuando detecta la palabra "jarvis". Útil para tenerlo corriendo en background.

### Configuración de voz

En `.env`:
```env
# Motor de voz: espeak (default, sin instalación extra) o pyttsx3
VOZ_MOTOR=espeak

# Velocidad de espeak (150 = normal, más alto = más rápido)
VOZ_VELOCIDAD=150
```

### Cambiar velocidad de voz (espeak)
```bash
# En acciones.py o directamente en terminal:
espeak -s 130 "Prueba de velocidad lenta"
espeak -s 180 "Prueba de velocidad rápida"
```

---

## 13. Sistema de Memoria

JARVIX tiene tres niveles de memoria:

### Memoria de conversación (`memoria.json`)
Historial de las últimas 40 interacciones de la sesión actual. Se usa como contexto para la IA.

```json
[
  {"role": "user", "content": "cómo genero un CSV en python"},
  {"role": "assistant", "content": "Puedes usar el módulo csv..."}
]
```

### Memoria persistente (`~/.jarvis_memory.json`)
Preferencias, alias, macros y rutinas que persisten entre sesiones.

```json
{
  "nombre_usuario": "Juan",
  "alias": {"mi editor": "code"},
  "macros": {
    "modo trabajo": ["abre code", "abre terminal", "pon música"]
  },
  "rutinas": [...]
}
```

### Base de datos SQLite (`~/.jarvis.db`)
Recordatorios y notas guardados con persistencia entre reinicios.

```sql
-- Tablas principales:
CREATE TABLE recordatorios (id, mensaje, tiempo, activo);
CREATE TABLE notas (id, texto, fecha);
```

---

## 14. Sistema de Visión (OCR)

### Cómo funciona

JARVIX puede "ver" lo que hay en tu pantalla usando dos estrategias combinadas:

1. **Detección de ventana activa** — via `xdotool` (instantáneo, sin captura de pantalla)
2. **OCR de pantalla completa** — via `pytesseract` + `mss` (local, sin internet)

Todo corre localmente. Ninguna imagen sale de tu computador.

### Arquitectura del módulo

```
jarvis_core/vision.py
├── ventana_activa()      → xdotool / wmctrl / xprop (cascada de fallbacks)
├── leer_pantalla()       → mss captura → Pillow preprocesa → tesseract OCR
├── describir()           → ventana_activa + análisis de palabras clave
├── describir_breve()     → una línea para mensajes de autonomía
├── proponer_accion()     → detecta errores, emails, código abierto
└── estado_dependencias() → diagnóstico de qué está instalado
```

### Instalar dependencias de visión manualmente

```bash
# Python
pip install mss Pillow pytesseract

# Sistema
sudo apt install tesseract-ocr tesseract-ocr-spa xdotool wmctrl
```

### Caché de visión

Para evitar hacer OCR repetidamente, los resultados se cachean por 15 segundos (configurable en `ScreenVision(cache_seg=15)`).

### Preprocesamiento de imagen

Antes de pasar al OCR, la imagen se procesa para mejorar la precisión:
- Conversión a escala de grises
- Aumento de contraste (x2)
- Filtro de nitidez

### Uso avanzado (desde código)

```python
from jarvis_core.vision import ScreenVision

v = ScreenVision(monitor=1, cache_seg=15, lang_ocr="spa+eng")

# Ventana activa (rápido, sin OCR)
print(v.ventana_activa())      # "VS Code — jarvis.py"

# OCR completo
print(v.leer_pantalla())       # todo el texto visible

# Descripción contextual
print(v.describir())           # "Ventana activa: VS Code. Parece que estás programando."

# Propuesta de ayuda
p = v.proponer_accion()
if p: print(p)                 # "Veo un error en pantalla. ¿Te ayudo a interpretarlo?"
```

---

## 15. Sistema de Autonomía

### Qué hace

El motor de autonomía corre en un **hilo daemon en background** mientras JARVIX está activo. Se comunica con el bucle principal via una cola thread-safe (`queue.Queue`).

### Tres funciones principales

#### 1. Rutinas programadas
Disparadores por hora y día de la semana. Por defecto:

| ID | Hora | Días | Mensaje | Estado |
|---|---|---|---|---|
| `buenos_dias` | 08:00 | Lun-Vie | "Buenos días. ¿Listo para empezar?" | ✅ Activa |
| `check_tarde` | 15:00 | Lun-Vie | "¿Cómo va el día?" | ⬜ Inactiva |
| `cierre_dia` | 20:00 | Lun-Vie | "¿Cerramos el día?" | ⬜ Inactiva |

#### 2. Detector de inactividad
Si pasan X minutos sin que el usuario interactúe, JARVIX pregunta si todo está bien. X se configura con `AUTONOMY_INACTIVIDAD_MIN` en `.env` (default: 60 min).

#### 3. Notificaciones de escritorio
Cada mensaje proactivo también dispara un `notify-send` visual en el escritorio.

### Comandos de voz para rutinas

```
mis rutinas                      → lista todas
activar rutina buenos_dias
desactivar rutina check_tarde
```

### Añadir rutina personalizada (desde código)

```python
# En cualquier plugin o en jarvis.py:
autonomy.agregar_rutina(
    id="reunion_lunes",
    desc="Recordatorio de reunión semanal",
    hora="09:30",
    dias=["lunes"],
    mensaje="Recuerda que tienes reunión de equipo en 30 minutos."
)
```

### Cómo se integra con jarvis.py

```python
# jarvis.py — fragmento de integración
from jarvis_core.autonomy import AutonomyEngine, cola_autonomia

_autonomy = AutonomyEngine(inactividad_min=60)
_autonomy.start()

# En el bucle principal, antes de pedir input:
while not cola_autonomia.empty():
    msg = cola_autonomia.get_nowait()
    hablar(msg)

# Cada vez que el usuario habla:
_autonomy.registrar_interaccion()
```

---

## 16. Sistema de Plugins

### Estructura de un plugin mínimo

```python
# plugins/mi_plugin.py
NOMBRE      = "mi_plugin"
DESCRIPCION = "Hace algo útil"
PATRONES    = ["activa X", "ejecuta X", "haz X"]

def ejecutar(orden: str, params: dict) -> str:
    return "Respuesta que Jarvis dirá en voz alta"
```

Guarda el archivo en `/plugins/` y reinicia JARVIX. El plugin se carga automáticamente.

### Plugins incluidos

| Plugin | Función |
|---|---|
| `vision_plugin.py` | Comandos de visión de pantalla |
| `autonomy_plugin.py` | Gestión de rutinas por voz |
| `spotify.py` (ejemplo) | Controlar Spotify |

### Plugins con intents v8

```python
# plugins/mi_plugin_v8.py
NOMBRE = "mi_plugin"
INTENTS = [
    {
        "nombre": "mi_accion",
        "frases": ["haz X", "ejecuta X", "activa X", "quiero que hagas X"],
        "accion": "mi_accion_handler",
    }
]

def ejecutar(orden: str, params: dict) -> str:
    accion = params.get("accion", "")
    if accion == "mi_accion_handler":
        return "Acción ejecutada"
    return ""
```

---

## 17. Sistema de Caché

El módulo `cache.py` guarda respuestas en memoria con TTL (tiempo de expiración). Evita llamar a la API repetidamente para la misma pregunta.

| TTL | Tipo de dato |
|---|---|
| 5 minutos | Respuestas de IA |
| 10 minutos | Consultas de clima |
| 30 segundos | Info del sistema (CPU, RAM) |

En consola, escribe `cache` para ver estadísticas:
```
> cache
Caché: 12 entradas — Hit rate: 73% — Tamaño: 8.2 KB
```

---

## 18. Sistema de Logs

Todo queda registrado en `~/.jarvis.log`.

```bash
# Ver en tiempo real
tail -f ~/.jarvis.log

# Filtrar por módulo
tail -f ~/.jarvis.log | grep AUTONOMY
tail -f ~/.jarvis.log | grep VISION
tail -f ~/.jarvis.log | grep ERROR
```

Formato:
```
2025-01-15 08:00:01 [INFO] [jarvis.autonomy] Rutina disparada: buenos_dias
2025-01-15 08:00:05 [INFO] Orden recibida: abre firefox
2025-01-15 08:00:05 [OK]   Firefox abierto
```

---

## 19. Sistema de Eventos (Event Bus)

`jarvis_core/events/` implementa un bus de eventos async. Los módulos publican y se suscriben a eventos sin acoplarse directamente.

```python
# Publicar un evento
await event_bus.emit("usuario_habló", {"texto": orden})

# Suscribirse
@event_bus.on("usuario_habló")
async def handler(data):
    print(f"El usuario dijo: {data['texto']}")
```

---

## 20. Integración con Ollama (IA local)

### Instalar Ollama

```bash
curl -fsSL https://ollama.com/install.sh | sh
```

### Iniciar el servidor

```bash
ollama serve
```

### Descargar un modelo

```bash
ollama pull qwen2.5:3b      # recomendado para N100
ollama pull phi3:mini       # buena calidad, 2.3 GB
ollama pull mistral:7b      # mejor calidad, 4.1 GB
```

### Cambiar modelo desde JARVIX

```
> cambia el modelo a phi3:mini
> lista los modelos
```

### Verificar que Ollama responde

```bash
curl http://localhost:11434/api/generate \
  -d '{"model":"qwen2.5:3b","prompt":"hola","stream":false}'
```

### Si Ollama no inicia

```bash
# Ver errores
journalctl -u ollama -f

# Reiniciar
sudo systemctl restart ollama

# Verificar puerto
ss -tlnp | grep 11434
```

---

## 21. Integración con IAs en Línea

### Flujo de selección (modo `auto`)

```
Orden del usuario
    │
    ▼
¿Hay respuesta en caché?  → Sí → Respuesta inmediata
    │ No
    ▼
¿IA online disponible?    → Sí → Groq / Gemini / Anthropic (first-wins)
    │ No
    ▼
Ollama local              → Respuesta (más lenta pero sin internet)
```

### Prioridad de IAs en modo `auto`

1. Groq (más rápido, gratuito)
2. Gemini (muy rápido, gratuito)
3. Anthropic (más caro, mayor calidad)
4. Ollama (local, siempre disponible)

### Circuit breaker

Si una IA falla X veces seguidas, se desactiva temporalmente y pasa al siguiente proveedor. Se reactiva automáticamente después de un tiempo.

### Forzar una IA específica

```
> cambia la IA a groq
> cambia la IA a ollama
> cambia la IA a auto
```

---

## 22. Integración con APIs Externas

### OpenWeatherMap (clima)

1. Crear cuenta en [openweathermap.org](https://openweathermap.org/api)
2. Copiar API key (plan gratuito tiene 1000 llamadas/día)
3. En `.env`: `OPENWEATHER_API_KEY=tu_clave`
4. Usar: `clima en medellín`

### WhatsApp Web (Selenium)

Requiere Firefox instalado. En el primer uso abrirá Firefox y pedirá escanear el QR de WhatsApp Web.

```bash
sudo apt install firefox
pip install selenium webdriver-manager
```

Uso: `manda whatsapp a Mamá: ya llegué`

---

## 23. Arquitectura General

```
┌─────────────────────────────────────────────────────┐
│                     jarvis.py                       │
│              (Entrypoint — delega a core)           │
└──────────────────────┬──────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────┐
│                  jarvis_core/app.py                 │
│         Bucle principal async + Event Bus           │
│                                                     │
│  ┌─────────┐ ┌──────────┐ ┌─────────┐ ┌─────────┐ │
│  │ intents │ │ plugins/ │ │ memory/ │ │ agent/  │ │
│  └────┬────┘ └────┬─────┘ └────┬────┘ └────┬────┘ │
│       └───────────┴────────────┴────────────┘       │
└──────────────────────┬──────────────────────────────┘
                       │
         ┌─────────────▼────────────────┐
         │       acciones.py            │
         │  (dispatcher de acciones)    │
         └──────────────────────────────┘
                       │
    ┌──────────────────┼──────────────────┐
    │                  │                  │
┌───▼───┐        ┌─────▼────┐      ┌─────▼────┐
│ia_    │        │autonomy  │      │vision.py │
│online │        │.py       │      │(OCR)     │
│.py    │        │(hilo bg) │      │(local)   │
└───────┘        └──────────┘      └──────────┘
```

---

## 24. Estructura de Carpetas

```
JARVIX/
├── jarvis.py              # Entrypoint — delega a jarvis_core/app.py
├── jarvis_core/           # Core modular v8+
│   ├── app.py             # Bucle principal async + event bus
│   ├── ai/                # Orquestación IA (timeouts/retries/circuit breaker)
│   ├── intents/           # Intent registry + normalización
│   ├── plugins/           # Loader de plugins
│   ├── events/            # EventBus async
│   ├── memory/            # Memoria persistente
│   ├── agent/             # Agent mode (planificación)
│   ├── autonomy.py        # Motor de autonomía proactiva ← NUEVO
│   └── vision.py          # Visión de pantalla OCR       ← NUEVO
├── plugins/               # Plugins del usuario
│   ├── vision_plugin.py   # Comandos de visión           ← NUEVO
│   └── autonomy_plugin.py # Comandos de rutinas          ← NUEVO
├── acciones.py            # Dispatcher de acciones del sistema
├── intenciones.py         # Patrones y grupos de funcionalidades
├── config.py              # Lee .env y expone configuración
├── logger.py              # Logging → ~/.jarvis.log
├── cache.py               # Caché en memoria con TTL
├── consola.py             # Colores ANSI + métricas de tiempo
├── diagnostico.py         # Autodiagnóstico completo
├── recordatorios.py       # Recordatorios + notas (SQLite)
├── clima.py               # OpenWeatherMap
├── whatsapp.py            # WhatsApp Web (Selenium)
├── ia_online.py           # Multi-IA: Groq, Gemini, Anthropic
├── voz.py                 # Entrada/salida de voz
├── instalar.sh            # Instalador automático
├── requirements.txt       # Dependencias Python
├── .env.example           # Plantilla de configuración
├── .env                   # Tu config real (NO en Git)
├── .gitignore
└── README.md
```

---

## 25. Flujo Interno del Sistema

```
Orden del usuario (voz o texto)
    │
    ▼
plugins → ¿algún PATRONES coincide?
    │ Sí → ejecutar() del plugin → hablar(respuesta)
    │ No
    ▼
procesar_sin_ia() → ¿patrón conocido?
    │ Sí → accion directa → hablar(respuesta)
    │ No
    ▼
¿es petición de código?
    │ Sí → ia_online o ollama → hablar(código)
    │ No
    ▼
ia_online disponible?
    │ Sí → preguntar_online() → hablar(respuesta)
    │ No
    ▼
preguntar_ia_local() (Ollama) → ejecutar(decision) → hablar(respuesta)

══════════════════════════════════════════════════
En paralelo (hilo daemon):
AutonomyEngine._loop() → cola_autonomia.put(msg)
→ bucle principal lo saca → hablar(msg)
```

---

## 26. Explicación de Módulos

| Módulo | Responsabilidad |
|---|---|
| `jarvis.py` | Punto de entrada. Parsea argumentos, inicia BD, carga plugins, bucle principal |
| `jarvis_core/app.py` | Runtime async v8, event bus, memoria persistente, agent mode |
| `jarvis_core/autonomy.py` | Hilo daemon con rutinas, inactividad, cola de mensajes proactivos |
| `jarvis_core/vision.py` | OCR local, detección de ventana, propuestas contextuales |
| `acciones.py` | Funciones que ejecutan órdenes: abrir apps, archivos, sistema |
| `intenciones.py` | Listas de patrones y grupos de funcionalidades |
| `ia_online.py` | Abstracción multi-IA con circuit breaker y first-wins |
| `cache.py` | Caché en RAM con TTL por tipo de dato |
| `consola.py` | Colores ANSI, métricas de latencia, impresión formateada |
| `diagnostico.py` | Verificación de todos los componentes con latencias |
| `voz.py` | SpeechRecognition + espeak, modo espera con backoff exponencial |
| `recordatorios.py` | CRUD de recordatorios y notas en SQLite, restauración al iniciar |
| `clima.py` | Consultas a OpenWeatherMap con caché |
| `whatsapp.py` | Selenium + Firefox para WhatsApp Web |
| `config.py` | Lee `.env`, expone constantes globales, saludo contextual |
| `logger.py` | Logging centralizado a `~/.jarvis.log` |

---

## 27. Crear un Plugin

### Estructura mínima (compatible v7 y v8)

```python
# plugins/mi_herramienta.py

NOMBRE      = "mi_herramienta"
DESCRIPCION = "Hace algo específico"
VERSION     = "1.0"

# Frases que activan este plugin
PATRONES = [
    "ejecuta mi herramienta",
    "activa herramienta",
    "herramienta personalizada",
]

def ejecutar(orden: str, params: dict) -> str:
    """
    orden  → el texto completo que dijo el usuario
    params → dict vacío por defecto (para compatibilidad futura)
    return → string que Jarvis dirá en voz alta
    """
    return "Mi herramienta ejecutada correctamente."
```

### Plugin con lógica de extracción

```python
# plugins/conversor.py
import re

NOMBRE   = "conversor"
DESCRIPCION = "Convierte monedas y unidades"
PATRONES = ["convierte", "cuánto es", "cuanto es", "en dólares", "en euros"]

def ejecutar(orden: str, params: dict) -> str:
    # Extraer número de la orden
    numeros = re.findall(r'\d+\.?\d*', orden)
    if not numeros:
        return "¿Qué cantidad quieres convertir?"
    
    cantidad = float(numeros[0])
    
    if "dólar" in orden or "usd" in orden:
        resultado = cantidad * 4000  # ejemplo COP
        return f"{cantidad} dólares son aproximadamente {resultado:,.0f} pesos."
    
    return f"No reconozco esa conversión. Cantidad detectada: {cantidad}"
```

### Recargar plugins sin reiniciar

En la consola de JARVIX:
```
> plugins
```
Esto lista todos los plugins cargados. Para recargar, reinicia JARVIX.

---

## 28. Crear una Acción

Las acciones viven en `acciones.py` y son funciones que ejecutan algo en el sistema.

```python
# En acciones.py, añadir:

def accion_abrir_calculadora() -> str:
    """Abre la calculadora del sistema."""
    import subprocess
    try:
        subprocess.Popen(["gnome-calculator"])
        return "Abriendo calculadora."
    except FileNotFoundError:
        try:
            subprocess.Popen(["kcalc"])
            return "Abriendo calculadora."
        except FileNotFoundError:
            return "No encontré una calculadora instalada."
```

Luego en `jarvis.py`, en el `dispatcher` de `ejecutar()`:
```python
"calculadora": lambda: accion_abrir_calculadora(),
```

Y en `procesar_sin_ia()`:
```python
if any(p in o for p in ["abre la calculadora", "calculadora", "abrir calculadora"]):
    return {"accion": "calculadora", "parametros": {}}
```

---

## 29. Crear un Intent

Los intents permiten que JARVIX entienda sinónimos y variaciones naturales del lenguaje.

```python
# En intenciones.py, añadir:
PATRONES_CALCULADORA = [
    "abre la calculadora",
    "calculadora",
    "necesito calcular algo",
    "abre el modo calculadora",
    "quiero hacer una cuenta",
]
```

---

## 30. Crear una Rutina Personalizada

```python
# Desde código (en un plugin o en jarvis.py):
autonomy.agregar_rutina(
    id="recordatorio_agua",
    desc="Recordatorio de hidratación",
    hora="10:00",
    dias=["lunes", "martes", "miércoles", "jueves", "viernes"],
    mensaje="¿Ya tomaste agua esta mañana? Recuerda hidratarte."
)
```

O editando directamente `~/.jarvis_memory.json`:
```json
{
  "rutinas": [
    {
      "id": "mi_rutina",
      "desc": "Mi recordatorio",
      "hora": "09:00",
      "dias": ["lunes", "miércoles", "viernes"],
      "mensaje": "Texto que dirá Jarvis",
      "activa": true
    }
  ]
}
```

---

## 31. Configuración de Modelos IA

### Elegir el modelo de Ollama según tu hardware

```bash
# Ver modelos instalados
ollama list

# Ver uso de RAM de un modelo antes de descargarlo
ollama show qwen2.5:3b --modelfile

# Cambiar modelo activo
# En .env:
MODELO_OLLAMA=qwen2.5:3b
```

### Timeout de Ollama

Si Ollama tarda mucho (>120s), JARVIX lo informa y sugiere cambiar a un modelo más liviano:
```
> cambia el modelo a qwen2.5:1.5b
```

---

## 32. Configuración de Voz

### Cambiar motor de voz

```bash
# Verificar que espeak está instalado
espeak "prueba de voz"

# Velocidad y tono
espeak -s 130 -p 50 "hola, soy jarvis"
```

### Si no se escucha la voz

```bash
# Verificar dispositivo de audio
aplay -l
speaker-test -t wav

# Verificar espeak
which espeak
espeak "prueba"
```

### Voz en modo sin internet

`espeak` funciona completamente offline. No requiere ninguna conexión.

---

## 33. Configuración de OCR y Visión

### Verificar instalación de Tesseract

```bash
tesseract --version
tesseract --list-langs   # debe incluir "spa" y "eng"
```

### Si OCR devuelve texto en blanco o basura

1. Verifica que `tesseract-ocr-spa` está instalado:
   ```bash
   sudo apt install tesseract-ocr-spa
   ```
2. El preprocesamiento de imagen puede necesitar ajuste para tu pantalla. Edita en `vision.py`:
   ```python
   # Aumentar contraste si el OCR falla en pantallas de baja resolución
   img = ImageEnhance.Contrast(img).enhance(3.0)  # prueba con 2.0, 3.0, 4.0
   ```

### Cambiar idioma del OCR

```python
# En jarvis_core/vision.py, al instanciar:
vision = ScreenVision(lang_ocr="spa")       # solo español
vision = ScreenVision(lang_ocr="spa+eng")   # español + inglés (default)
vision = ScreenVision(lang_ocr="eng")       # solo inglés
```

---

## 34. Configuración de Rutinas y Autonomía

### Variables de entorno

```env
AUTONOMY_INACTIVIDAD_MIN=60   # 0 para desactivar la alerta de inactividad
```

### Activar rutinas adicionales

```
> activar rutina check_tarde
> activar rutina cierre_dia
```

### Ajustar el intervalo de revisión

En `jarvis.py` donde se instancia `AutonomyEngine`:
```python
_autonomy = AutonomyEngine(
    inactividad_min=60,
    check_seg=60,       # revisa cada 60 segundos (bajar = más preciso pero más CPU)
    notif_desktop=True
)
```

---

## 35. Errores Comunes

### `ModuleNotFoundError: No module named 'groq'`

```bash
source .venv/bin/activate
pip install groq
```

### `FileNotFoundError: [Errno 2] No such file or directory: 'espeak'`

```bash
sudo apt install espeak
```

### `OSError: [Errno -9996] Invalid input device`

El micrófono no está configurado o no es accesible:
```bash
# Listar dispositivos de entrada
arecord -l

# Probar micrófono
arecord -d 3 /tmp/test.wav && aplay /tmp/test.wav
```

### `PermissionError` al abrir apps

```bash
# Asegúrate de no estar corriendo como root
whoami   # debe ser tu usuario normal, no root
```

---

## 36. Problemas de Voz

### JARVIX no escucha

1. Verificar micrófono:
   ```bash
   arecord -l
   arecord -d 3 test.wav && aplay test.wav
   ```
2. Instalar PyAudio:
   ```bash
   sudo apt install portaudio19-dev libasound2-dev
   pip install pyaudio
   ```
3. En modo `--espera`, di claramente "jarvis" (sin ruido de fondo).

### La voz suena robótica / muy rápida

```bash
# Ajustar velocidad de espeak
espeak -s 120 "prueba de velocidad"
```

Modifica la llamada a `espeak` en `voz.py` con `-s 120` (más lento) o `-s 170` (más rápido).

### `ALSA lib pcm.c` warnings en consola

Son advertencias inofensivas de ALSA. Para suprimirlas:
```bash
# Redirigir stderr al arrancar
python jarvis.py 2>/dev/null
```

---

## 37. Problemas de Visión y OCR

### `"Visión no disponible. Instala: pip install mss Pillow pytesseract"`

```bash
source .venv/bin/activate
pip install mss Pillow pytesseract
sudo apt install tesseract-ocr tesseract-ocr-spa
```

### `"Ventana desconocida"` siempre

Instalar xdotool:
```bash
sudo apt install xdotool
```

Probar manualmente:
```bash
xdotool getactivewindow
xdotool getwindowname $(xdotool getactivewindow)
```

### OCR lento (>5 segundos)

- Reduce `max_width` en `ScreenVision(max_width=800)` — menos píxeles = más rápido
- Aumenta `cache_seg` en `ScreenVision(cache_seg=30)` — cachea más tiempo

### OCR no detecta texto en pantallas HiDPI (4K)

Las pantallas 4K pueden hacer que el texto sea muy pequeño para Tesseract. Intenta:
```python
# En vision.py, cambiar max_width a algo mayor:
ScreenVision(max_width=2560)
```

---

## 38. Problemas con Ollama

### `"Ollama no está corriendo"`

```bash
ollama serve
# O como servicio del sistema:
sudo systemctl start ollama
```

### `"La IA local tardó demasiado"`

Cambiar a un modelo más liviano:
```
> cambia el modelo a qwen2.5:1.5b
```
O en `.env`: `MODELO_OLLAMA=qwen2.5:1.5b`

### Ollama consume demasiada RAM

```bash
# Ver modelos instalados y su tamaño
ollama list

# Eliminar modelos que no uses
ollama rm mistral:7b
```

### `"Error de conexión a Ollama"`

Verificar el puerto:
```bash
curl http://localhost:11434
# Debe responder: "Ollama is running"

ss -tlnp | grep 11434
```

Si está bloqueado por firewall:
```bash
sudo ufw allow 11434/tcp
```

---

## 39. Problemas con IAs Online

### `"API key no válida"` o `401 Unauthorized`

Verificar que la clave en `.env` no tiene espacios ni comillas:
```env
GROQ_API_KEY=gsk_abc123...   # correcto
GROQ_API_KEY="gsk_abc123"    # incorrecto
```

### Groq / Gemini responde muy lento

Cambiar a modo auto para que use el más rápido disponible:
```
> cambia la IA a auto
```

### Rate limit excedido

```
> cambia la IA a ollama
```
O espera unos minutos y el circuit breaker reactiva la IA online automáticamente.

---

## 40. Problemas de Rendimiento

### JARVIX consume mucho CPU en reposo

El motor de autonomía revisa cada 60 segundos. Si quieres reducirlo:
```python
# En jarvis.py, al instanciar AutonomyEngine:
_autonomy = AutonomyEngine(check_seg=120)  # revisa cada 2 minutos
```

### Respuestas muy lentas con Ollama

1. Usa un modelo más pequeño: `qwen2.5:1.5b` o `smollm2:1.7b`
2. Cierra otras aplicaciones para liberar RAM
3. Si tienes GPU NVIDIA: Ollama la usa automáticamente

```bash
# Verificar si Ollama usa GPU
ollama ps
nvidia-smi  # ver uso de GPU
```

---

## 41. FAQ

**¿Funciona sin internet?**  
Sí. Con Ollama y sin claves de API en línea, todo funciona offline excepto clima, WhatsApp y búsquedas web.

**¿Mis datos salen de mi computador?**  
Solo si usas IAs en línea (Groq, Gemini, Anthropic) o el clima. El OCR, Ollama, memoria y rutinas son 100% locales.

**¿Funciona en Windows?**  
El proyecto está diseñado para Linux. En Windows faltarían: `xdotool`, `espeak`, `notify-send`, y comandos de sistema como `nmcli`. Con WSL2 podría funcionar parcialmente.

**¿Puedo cambiar la voz de Jarvis?**  
Sí, `espeak` tiene varios idiomas y voces:
```bash
espeak --voices=es   # listar voces en español
espeak -v es+f3 "Hola"  # voz femenina
```

**¿Cómo agrego mis propias frases para un comando existente?**  
En `intenciones.py`, añade tu frase al array correspondiente:
```python
PATRONES_SISTEMA = [..., "cómo va el computador", "estado del pc"]
```

**¿Puedo tener múltiples instancias de JARVIX?**  
No se recomienda. Habría conflictos con el micrófono y los archivos de memoria.

**¿Cómo actualizo JARVIX?**  
```bash
git pull origin main
bash instalar.sh   # actualiza dependencias si las hay nuevas
```

---

## 42. Seguridad y Permisos

- Las API keys están en `.env` — **nunca** en el código fuente
- `.env` está en `.gitignore` — **nunca** se sube a Git
- JARVIX no requiere `sudo` para funcionar en modo normal
- Los screenshots del OCR **nunca** salen del computador
- El historial de conversación se guarda en `memoria.json` localmente

Para compartir el proyecto, usa solo `.env.example` (sin claves reales):
```bash
cp .env.example .env.shared   # comparte esto, nunca .env
```

---

## 43. Rendimiento y Optimización

| Situación | Optimización |
|---|---|
| Respuestas lentas | Usar `IA_PREFERIDA=groq` o modelo Ollama más pequeño |
| Alto uso de RAM | `ollama rm modelos-grandes`, usar `qwen2.5:1.5b` |
| OCR lento | `ScreenVision(max_width=800, cache_seg=30)` |
| CPU alto en background | `AutonomyEngine(check_seg=120)` |
| Inicializacion lenta | Tener Ollama ya corriendo antes de iniciar Jarvis |

---

## 44. Testing y Diagnóstico

### Diagnóstico completo

```bash
python jarvis.py test
```

Verifica: Ollama, cada API key (petición real), espeak, micrófono, plugins, SQLite, caché, OCR.

### Diagnóstico de visión

Desde dentro de JARVIX:
```
> diagnóstico de visión
```

### Probar OCR manualmente

```bash
source .venv/bin/activate
python -c "
from jarvis_core.vision import ScreenVision
v = ScreenVision()
print(v.estado_dependencias())
print('---')
print(v.ventana_activa())
"
```

### Probar autonomía manualmente

```bash
python -c "
from jarvis_core.autonomy import AutonomyEngine
a = AutonomyEngine()
print(a.listar_rutinas())
"
```

---

## 45. Roadmap

- [x] Arquitectura modular v8 (intents, plugins, async, event bus)
- [x] Memoria persistente real
- [x] Visión de pantalla 100% offline (OCR)
- [x] Motor de autonomía proactiva (rutinas, inactividad)
- [ ] Interfaz gráfica opcional (GTK o web local)
- [ ] Memoria episódica más rica (qué hice hoy, ayer, esta semana)
- [ ] Integración con calendario (agenda local)
- [ ] Plugin de Telegram (notificaciones bidireccionales)
- [ ] Modo multi-pantalla para OCR
- [ ] Propuestas de IA basadas en historial de uso

---

## 46. Changelog

### v9 (actual)
- ✅ `jarvis_core/vision.py` — visión de pantalla 100% offline (OCR + xdotool)
- ✅ `jarvis_core/autonomy.py` — motor de autonomía proactiva (hilo daemon + cola)
- ✅ `plugins/vision_plugin.py` — comandos de visión por voz
- ✅ `plugins/autonomy_plugin.py` — gestión de rutinas por voz
- ✅ `instalar.sh` actualizado con dependencias de OCR y autonomía

### v8
- Arquitectura modular real (jarvis_core/)
- Sistema de intents con sinónimos naturales
- Event-driven / async (anti-congelamientos)
- Failover "first model wins" con circuit breaker
- Memory persistente (~/.jarvis_memory.json)
- Agent mode (primer corte)

### v7
- Caché con TTL
- Consola con colores y métricas de tiempo
- Diagnóstico completo
- Sistema de plugins
- Perfil de usuario

---

## 47. Licencia y Créditos

Proyecto personal de código abierto. Úsalo, modifícalo y compártelo.

**Tecnologías de terceros utilizadas:**
- [Ollama](https://ollama.com) — runtime de LLMs locales
- [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) — Google, Apache License 2.0
- [mss](https://github.com/BoboTiG/python-mss) — captura de pantalla multiplataforma
- [SpeechRecognition](https://github.com/Jlillis/SpeechRecognition) — reconocimiento de voz
- [espeak](http://espeak.sourceforge.net) — síntesis de voz offline
- [Groq](https://groq.com), [Google Gemini](https://ai.google.dev), [Anthropic](https://anthropic.com) — IAs en línea

---

*Documentación actualizada para JARVIX v9 — Autonomía + Visión offline*
