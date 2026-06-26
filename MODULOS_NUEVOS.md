# Módulos Nuevos de JARVIX - Documentación

## Resumen de Implementación

Se han implementado los siguientes módulos faltantes para completar la visión de JARVIX como asistente conversacional inteligente:

---

## 1. Memoria Episódica (`jarvis_core/memory/episodic_memory.py`)

**Propósito:** Registra eventos de actividad del usuario para responder preguntas sobre su historial.

### Funciones Principales:

- `inicializar_tabla()`: Crea las tablas SQLite en `~/.jarvis.db`
- `registrar(tipo, descripcion, app, duracion_seg)`: Guarda un evento
- `que_hice_hoy()`: Devuelve eventos de hoy
- `que_hice_ayer()`: Devuelve eventos de ayer
- `resumen_del_dia(fecha)`: Genera resumen en lenguaje natural
- `ultima_vez_que_use(app_o_tipo)`: Busca última vez que se usó algo
- `limpiar_antiguos(dias)`: Limpieza automática de eventos viejos

### Comandos Soportados:
- "¿qué hice hoy?"
- "¿qué hice ayer?"
- "¿cuándo usé VSCode por última vez?"
- "dame un resumen del día"

---

## 2. Memoria de Personas (`jarvis_core/memory/people_memory.py`)

**Propósito:** Gestiona información sobre personas importantes para el usuario.

### Funciones Principales:

- `inicializar_tabla()`: Crea tabla en `~/.jarvis.db`
- `guardar_persona(nombre, relacion, cumpleanos, gustos, notas)`: Guarda/actualiza persona
- `obtener_persona(nombre)`: Obtiene información de una persona
- `buscar_por_relacion(relacion)`: Busca por tipo de relación
- `proximos_cumpleanos(dias)`: Cumpleaños en próximos N días
- `obtener_contexto_personas(nombres)`: Contexto para incluir en prompts de IA
- `detectar_patron_persona(texto)`: Detecta patrones como "mi mamá se llama X"

### Patrones Detectados Automáticamente:
- "mi mamá se llama Rosa" → guarda relación
- "el cumpleaños de Ana es el 15/03" → guarda fecha
- "a mi amigo Carlos le gusta el fútbol" → guarda gusto

### Comandos Soportados:
- "guarda que mi mamá se llama Rosa"
- "¿qué sé sobre Rosa?"
- "¿cuándo cumple años mi mamá?"
- "actualiza que a Rosa le gusta el teatro"

---

## 3. Motor de Sugerencias Proactivas (`jarvis_core/proactive_engine.py`)

**Propósito:** Observa la actividad y hace sugerencias oportunas sin ser intrusivo.

### Características:

- **Hilo en background:** No bloquea el bucle principal
- **Sistema de créditos:** Máx 3 interrupciones/hora, mín 10 min entre cada una
- **Condiciones monitoreadas:**
  1. Cumpleaños en próximas 24h
  2. Actividad continua ≥90 minutos (sugiere descanso)
  3. Recordatorios que vencen en ≤15 minutos
  4. App activa ≥30 minutos con contexto relevante
  5. Buenos días (primera actividad del día)
  6. Buenas noches (inactividad después de 22:00)

### Respeto al Usuario:
- Respeta horario de silencio configurable
- Respeta días de no molestar
- No interrumpe si el usuario está hablando activamente
- Si el usuario dice "ahora no" o "estoy ocupado", silencia por 30 minutos

---

## 4. Búsqueda Web Automática (`jarvis_core/web_search.py`)

**Propósito:** Permite a JARVIX buscar información en internet cuando es necesario.

### Características:

- **Evaluación con IA local:** Decide si necesita búsqueda antes de ejecutar
- **Búsqueda en DuckDuckGo:** En español, primeros 5 resultados
- **Extracción limpia:** Usa trafilatura para contenido de páginas
- **Cache por sesión:** Evita búsquedas repetidas

### Flujo:
1. Usuario hace pregunta
2. IA evalúa si necesita información actualizada de internet
3. Si sí → busca en DuckDuckGo
4. Extrae contenido de primera URL
5. Formatea resultados y envía a IA con contexto
6. IA responde naturalmente mencionando fuentes

### Comandos Manuales:
- "busca en internet..." → fuerza búsqueda
- "googlea..." → fuerza búsqueda
- "no busques, respóndeme tú" → desactiva para esa orden

---

## 5. Autoconfiguración Conversacional (`jarvis_core/config_manager.py`)

**Propósito:** JARVIX se autoconfigura mediante conversación sin reiniciarse.

### Archivo de Configuración:
- Ubicación: `~/.jarvis_config.json`
- Se lee al iniciar y se escribe inmediatamente al cambiar

### Tipos de Cambios Soportados:

#### Horarios:
- "no me molestes después de las 9pm"
- "los domingos no me hables"

#### Comportamiento:
- "sé más breve"
- "no me saludes en las mañanas"
- "habla solo cuando te pregunte"

#### Apps:
- "cuando tenga VSCode abierto no interrumpas"
- "si abro Netflix silénciate"

#### Nombre del Usuario:
- "no me llames Juan, llámame Juancho"

#### Reglas Libres:
- Cualquier preferencia no clasificada se guarda como texto

### Flujo de Confirmación:
1. JARVIX detecta instrucción de configuración
2. Resume el cambio y pregunta "¿quieres que recuerde esto?"
3. Si confirma → aplica inmediatamente
4. Si rechaza o no responde en 20 segundos → descarta

### Comandos de Consulta:
- "¿cómo estás configurado?" → resume todas las preferencias
- "¿qué reglas tienes?" → mismo resultado

### Comandos de Borrado:
- "olvida que te dije que no interrumpieras con Chrome" → encuentra y elimina

---

## Integración en `jarvis_core/app.py`

### Inicialización:
```python
# En __init__ de JarvisApp:
inicializar_episodica()      # Memoria episódica
inicializar_personas()       # Memoria de personas
_anunciar_cumpleanos_proximos()  # Anuncia cumpleaños al iniciar
iniciar_proactive(...)       # Motor de sugerencias
```

### Procesamiento de Órdenes:
1. Registrar evento en memoria episódica
2. Detectar patrón de persona → pedir confirmación
3. Detectar instrucción de configuración → pedir confirmación
4. Construir contexto enriquecido (personas + reglas)
5. Búsqueda web automática si es necesario
6. Enviar a IA con contexto completo

---

## Dependencias Requeridas

Para instalar las nuevas dependencias:

```bash
pip install duckduckgo-search trafilatura
```

Las memorias usan SQLite que viene incluido en Python.

---

## Verificación de Funcionamiento

### Prueba Memoria Episódica:
```python
from jarvis_core.memory.episodic_memory import registrar, que_hice_hoy
registrar("app_abierta", "Inició VSCode", app="VSCode")
eventos = que_hice_hoy()
print(eventos)
```

### Prueba Memoria de Personas:
```python
from jarvis_core.memory.people_memory import guardar_persona, obtener_persona
guardar_persona("Rosa", relacion="mamá", cumpleanos="03-15")
info = obtener_persona("Rosa")
print(info)
```

### Prueba Búsqueda Web:
```python
from jarvis_core.web_search import buscar_web
resultados = buscar_web("noticias sobre inteligencia artificial hoy")
print(resultados)
```

### Prueba Autoconfiguración:
```python
from jarvis_core.config_manager import ConfigManager
config = ConfigManager()
config.load()
resultado = config.detectar_instruccion("llámame Juancho")
print(resultado)
```

---

## Archivos Creados/Modificados

### Nuevos Archivos:
- `jarvis_core/memory/episodic_memory.py`
- `jarvis_core/memory/people_memory.py`
- `jarvis_core/proactive_engine.py`
- `jarvis_core/web_search.py`

### Archivos Modificados:
- `jarvis_core/app.py` (integración de todos los módulos)
- `jarvis_core/config_manager.py` (ya existía, se mantiene)

### Archivos de Datos:
- `~/.jarvis.db` (SQLite para memorias episódica y de personas)
- `~/.jarvis_config.json` (configuración dinámica)
- `~/.jarvis_memory.json` (sin cambios, memoria original)

---

## Notas Importantes

1. **No se modificó:** La memoria de personas original (`~/.jarvis_memory.json`) se mantiene intacta.

2. **Lazy loading:** Todos los imports pesados están dentro de funciones para arranque instantáneo.

3. **Try/except:** Cada módulo nuevo tiene manejo de errores para no romper JARVIX si falla.

4. **Confirmaciones:** Toda acción destructiva o cambio de configuración requiere confirmación explícita.

5. **Persistencia:** Las memorias usan SQLite que es más eficiente para consultas complejas.

6. **Thread-safe:** El motor de sugerencias corre en hilo separado y no bloquea la conversación.
