from __future__ import annotations

import asyncio
import json
import os
import sys
from dataclasses import dataclass

from logger import log
from cache import cache, TTL_IA
from consola import (
    cronometro,
    imprimir_banner,
    imprimir_estado,
    imprimir_orden,
    imprimir_respuesta,
)
from config import (
    NOMBRE_USUARIO,
    saludo_contextual,
    URL_OLLAMA,
    MODELO,
)
from voz import hablar, escuchar, escuchar_con_activacion

from jarvis_core.ai.orchestrator import AiOrchestrator
from jarvis_core.plugins.compat import PluginCompat
from jarvis_core.intents.registry import IntentRegistry
from jarvis_core.intents.builtins import builtin_intents
from jarvis_core.plugins.intent_loader import PluginIntentLoader
from jarvis_core.events.bus import EventBus
from jarvis_core.memory.store import MemoryStore
from jarvis_core.agent.runner import AgentRunner

from jarvis_core.legacy_bridge import ejecutar as ejecutar_sync
from jarvis_core.legacy_bridge import procesar_sin_ia as procesar_sin_ia_legacy
from jarvis_core.conversation import ConversationEngine, cola_conversacion
from jarvis_core.semantic_cache import ProcesadorSemantico, construir_intents_jarvix
from jarvis_core.episodic_memory import inicializar_tabla as _init_episodic
from jarvis_core.people_memory import inicializar_tabla as _init_people

# ──────────────────────────────────────────────────────────────────────────────
# CONVERSACIÓN CONTINUA — Configuración
# ──────────────────────────────────────────────────────────────────────────────

MENSAJE_SISTEMA = f"""Eres JARVIX, el asistente personal de {NOMBRE_USUARIO}.
Corres en Linux y conoces perfectamente el contexto del escritorio.
Hablas en español de manera natural, conversacional y proactiva.
Recuerda toda la conversación previa y usa ese contexto para responder.
Si el usuario hace referencia a "eso que me dijiste", "lo de antes" o similar,
retoma lo hablado anteriormente en esta conversación.
""".strip()

MAX_HISTORIAL = 40  # Máximo de mensajes (usuario + assistant) en memoria


def _construir_mensajes_ia(orden: str, historial: list[dict]) -> list[dict]:
    """
    Construye la lista completa de mensajes para enviar a la IA:
    [mensaje_sistema] + historial_recortado + [orden_actual]
    Incluye contexto de personas mencionadas si las hay.
    """
    # Recortar historial si excede el máximo (dejamos espacio para system + nuevo)
    historial_recortado = historial[-(MAX_HISTORIAL - 2):] if len(historial) > MAX_HISTORIAL - 2 else historial
    
    # Obtener contexto de personas mencionadas en la orden actual
    from jarvis_core import people_memory as pm
    contexto_personas = pm.obtener_contexto_personas(orden, max_personas=3)
    
    # Construir mensaje de sistema con contexto adicional si hay personas
    mensaje_sistema_completo = MENSAJE_SISTEMA
    if contexto_personas:
        mensaje_sistema_completo += f"\n\n{contexto_personas}"
    
    mensajes = [{"role": "system", "content": mensaje_sistema_completo}]
    mensajes.extend(historial_recortado)
    mensajes.append({"role": "user", "content": orden})
    
    return mensajes


def _escanear_modelos_ollama() -> list[str]:
    """Escanea modelos de Ollama instalados localmente."""
    import requests
    
    try:
        r = requests.get("http://localhost:11434/api/tags", timeout=3)
        if r.status_code == 200:
            data = r.json()
            modelos = [m.get("name", "") for m in data.get("models", []) if m.get("name")]
            return modelos
    except Exception:
        pass
    return []


def _seleccionar_modelo_interactivo(modelos: list[str], modelo_default: str) -> str:
    """Permite al usuario seleccionar un modelo de la lista."""
    if not modelos:
        print(f"\n  {imprimir_estado('No se encontraron modelos de Ollama instalados.', 'warn')}")
        print(f"  {imprimir_estado('Instala uno con: ollama pull qwen2.5:3b', 'info')}")
        return modelo_default
    
    print(f"\n{'='*52}")
    print(f"  🤖 Modelos de Ollama disponibles ({len(modelos)}):")
    print(f"{'='*52}")
    
    for i, modelo in enumerate(modelos, 1):
        marca = "✓" if modelo == modelo_default else " "
        print(f"  [{marca}] {i}. {modelo}")
    
    print(f"\n  Modelo por defecto: {modelo_default}")
    print(f"  Escribe el número del modelo a usar, o Enter para continuar con el default.")
    
    try:
        seleccion = input("\n  Tu elección: ").strip()
        if not seleccion:
            return modelo_default
        
        idx = int(seleccion) - 1
        if 0 <= idx < len(modelos):
            modelo_elegido = modelos[idx]
            print(f"  {imprimir_estado(f'Usando modelo: {modelo_elegido}', 'ok')}")
            return modelo_elegido
        else:
            print(f"  {imprimir_estado('Selección inválida, usando modelo por defecto.', 'warn')}")
            return modelo_default
    except (ValueError, EOFError, KeyboardInterrupt):
        print(f"\n  {imprimir_estado('Usando modelo por defecto.', 'info')}")
        return modelo_default


MEMORIA_FILE = "memoria.json"


def _cargar_memoria() -> list[dict]:
    if os.path.exists(MEMORIA_FILE):
        try:
            with open(MEMORIA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            log.warning("No se pudo cargar memoria: %s", e)
    return []


def _guardar_memoria(historial: list[dict]) -> None:
    try:
        with open(MEMORIA_FILE, "w", encoding="utf-8") as f:
            json.dump(historial[-40:], f, indent=2, ensure_ascii=False)
    except Exception as e:
        log.warning("No se pudo guardar memoria: %s", e)


@dataclass
class AppConfig:
    mode: str  # texto | voz | espera


class JarvisApp:
    def __init__(self, cfg: AppConfig, modelo_ollama: str = MODELO) -> None:
        self.cfg = cfg
        self.plugins = PluginCompat()
        self.registry = IntentRegistry()
        self.registry.register_many(builtin_intents())
        self.plugin_intents = PluginIntentLoader()
        self.plugin_intents.register_into(self.registry)
        self.bus = EventBus()
        self.memory = MemoryStore()
        self.ai = AiOrchestrator(
            ollama_url=URL_OLLAMA,
            ollama_model=modelo_ollama,
        )
        self.agent = AgentRunner(self.ai)
        # Motor de conversación proactiva
        self.conversation = ConversationEngine(
            inactividad_min=30,  # Inicia conversación después de 30 min de inactividad
            check_seg=60,        # Revisa cada minuto
            max_conversaciones_dia=5  # Máximo 5 conversaciones por día
        )
        # Procesador semántico (cache + intent matcher + IA clasificadora)
        self._procesador: ProcesadorSemantico | None = None

    def _inicializar_procesador(self) -> ProcesadorSemantico:
        """Inicializa el procesador semántico con lazy loading."""
        if self._procesador is not None:
            return self._procesador
        
        import acciones as _acciones
        from jarvis_core.ia.ollama import llamar_ia as llamar_ia_ollama
        
        self._procesador = ProcesadorSemantico(
            fn_llamar_ia=llamar_ia_ollama,
            fn_respuesta_libre=llamar_ia_ollama,
            umbral_cache=0.92,
            umbral_intent=0.85,
        )
        
        for intent in construir_intents_jarvix(_acciones):
            self._procesador.registrar_intent(intent)
        
        return self._procesador

    async def _get_order(self) -> str:
        if self.cfg.mode == "espera":
            return await asyncio.to_thread(escuchar_con_activacion)
        if self.cfg.mode == "voz":
            return await asyncio.to_thread(escuchar)
        return await asyncio.to_thread(lambda: input("\nJarvis › ").strip())

    async def _execute_decision(self, decision: dict) -> str:
        # acciones.py es sync; lo corremos en thread para no bloquear el loop
        return await asyncio.to_thread(ejecutar_sync, decision)

    async def run(self) -> None:
        log.info("Jarvis core iniciado — modo: %s", self.cfg.mode)

        # Inicializar tabla de memoria episódica
        _init_episodic()
        
        # Inicializar tabla de memoria de personas
        _init_people()

        self.plugins.load()

        await self.bus.start(workers=2)
        
        # Iniciar motor de conversación proactiva
        self.conversation.start()

        imprimir_banner(version="8", modo=self.cfg.mode, ia_local=True, nombre_usuario=NOMBRE_USUARIO)
        saludo = saludo_contextual()
        await asyncio.to_thread(hablar, saludo)
        
        # Verificar cumpleaños próximos al iniciar
        from jarvis_core import people_memory as pm
        cumpleanos_proximos = pm.proximos_cumpleanos(dias=3)
        if cumpleanos_proximos:
            for cumple in cumpleanos_proximos:
                dias = cumple["dias_restantes"]
                nombre = cumple["nombre"]
                relacion = cumple.get("relacion", "")
                
                if dias == 0:
                    mensaje = f"¡Hoy es el cumpleaños de {nombre}!"
                    if relacion:
                        mensaje += f" Tu {relacion} está de fiesta."
                elif dias == 1:
                    mensaje = f"Mañana es el cumpleaños de {nombre}."
                    if relacion:
                        mensaje += f" Prepara algo especial para tu {relacion}."
                else:
                    mensaje = f"En {dias} días es el cumpleaños de {nombre}."
                
                await asyncio.to_thread(hablar, mensaje)

        historial = _cargar_memoria()
        
        # Seed macro default v8: "modo trabajo"
        if "trabajo" not in self.memory.state.macros:
            self.memory.state.macros["trabajo"] = [
                {"accion": "abrir_app", "parametros": {"app": "codigo"}},
                {"accion": "abrir_app", "parametros": {"app": "navegador"}},
                {"accion": "volumen", "parametros": {"accion": "silenciar"}},
            ]
            self.memory.save()

        while True:
            try:
                # Verificar mensajes de conversación proactiva
                while not cola_conversacion.empty():
                    msg_conv = cola_conversacion.get_nowait()
                    if msg_conv:
                        imprimir_respuesta(msg_conv, fuente="conversacion")
                        await asyncio.to_thread(hablar, msg_conv, usar_frase_transicion=False)
                        self.conversation.registrar_respuesta_jarvis(msg_conv)

                orden = await self._get_order()
                if not orden:
                    continue

                # Registrar interacción del usuario para el motor de conversación
                self.conversation.registrar_interaccion(orden)
                
                # Registrar evento en memoria episódica
                from jarvis_core import episodic_memory as em
                em.registrar("orden_recibida", descripcion=orden[:200])

                o = orden.lower().strip()
                
                # Comando para limpiar conversación
                if o in ("nueva conversación", "olvida lo anterior", "reinicia conversación", "borra historial"):
                    historial.clear()
                    _guardar_memoria(historial)
                    respuesta = "He olvidado toda la conversación previa. Empezamos desde cero."
                    imprimir_respuesta(respuesta, fuente="sistema")
                    await asyncio.to_thread(hablar, respuesta)
                    continue
                
                # Comandos de memoria de personas
                from jarvis_core import people_memory as pm
                
                # Detectar información sobre personas y preguntar si guardar
                info_persona = pm.detectar_info_persona(orden)
                if info_persona:
                    pregunta = pm.generar_pregunta_confirmacion(info_persona)
                    imprimir_respuesta(pregunta, fuente="personas")
                    await asyncio.to_thread(hablar, pregunta)
                    # Esperar confirmación del usuario
                    confirmacion = await asyncio.to_thread(lambda: input("\nJarvis › ").strip().lower())
                    if confirmacion in ("sí", "si", "yes", "ok", "dale", "confirma"):
                        pm.guardar_persona(
                            nombre=info_persona.get("nombre", ""),
                            relacion=info_persona.get("relacion", ""),
                            cumpleanos=info_persona.get("cumpleanos", ""),
                            gustos=info_persona.get("gustos", ""),
                            notas=info_persona.get("notas", "")
                        )
                        respuesta = f"Guardada la información sobre {info_persona.get('nombre', 'esta persona')}."
                        imprimir_respuesta(respuesta, fuente="personas")
                        await asyncio.to_thread(hablar, respuesta)
                        em.registrar("persona_guardada", descripcion=f"Se guardó información sobre {info_persona.get('nombre')}")
                    else:
                        imprimir_respuesta("No guardé la información.", fuente="personas")
                    continue
                
                # Consultas directas sobre personas
                if "qué sé sobre" in o or "que sé sobre" in o:
                    respuesta = pm.comando_que_se_sobre(orden)
                    imprimir_respuesta(respuesta, fuente="personas")
                    await asyncio.to_thread(hablar, respuesta)
                    continue
                
                if "cuándo cumple" in o or "cuando cumple" in o:
                    respuesta = pm.comando_cuando_cumple(orden)
                    imprimir_respuesta(respuesta, fuente="personas")
                    await asyncio.to_thread(hablar, respuesta)
                    continue
                
                if "actualiza" in o and ("le gusta" in o or "se llama" in o):
                    respuesta = pm.comando_actualizar_persona(orden)
                    imprimir_respuesta(respuesta, fuente="personas")
                    await asyncio.to_thread(hablar, respuesta)
                    continue
                
                if o in ("ayuda", "help"):
                    from jarvis_core.intents.patterns import ayuda_grupos

                    print(ayuda_grupos())
                    print("\n  Escribe 'funcionalidades totales' para ver todos los comandos.")
                    continue

                if o in ("plugins", "qué plugins tienes", "que plugins tienes"):
                    print(self.plugins.summary())
                    continue

                imprimir_orden(orden)
                log.info("Orden recibida: %s", orden[:100])
                
                # v8: Agent mode quick trigger (sintaxis: "agente: ...")
                if o.startswith("agente:"):
                    objective = orden.split(":", 1)[1].strip()
                    mensajes_ia = _construir_mensajes_ia(orden, historial)
                    plan = await self.agent.plan(objective, mensajes_ia)
                    if not plan:
                        imprimir_estado("No pude planear en modo agente.", "warn")
                        continue
                    result = await self.agent.execute(plan)
                    texto = f"Plan generado con {len(plan.steps)} paso(s)."
                    imprimir_respuesta(texto, fuente="agent")
                    await asyncio.to_thread(hablar, texto)
                    historial.append({"role": "assistant", "content": texto})
                    _guardar_memoria(historial)
                    continue

                # 1) Plugins (antes que todo)
                respuesta_plugin = self.plugins.try_handle(orden)
                if respuesta_plugin is not None:
                    imprimir_respuesta(respuesta_plugin, fuente="plugin")
                    await asyncio.to_thread(hablar, respuesta_plugin)
                    historial.append({"role": "assistant", "content": respuesta_plugin})
                    _guardar_memoria(historial)
                    continue

                # 2) Procesador semántico (cache + intent matcher + IA clasificadora)
                procesador = self._inicializar_procesador()
                respuesta_semantica, nivel = procesador.procesar(orden)
                if respuesta_semantica:
                    imprimir_respuesta(respuesta_semantica, fuente=nivel)
                    await asyncio.to_thread(hablar, respuesta_semantica)
                    historial.append({"role": "assistant", "content": respuesta_semantica})
                    _guardar_memoria(historial)
                    continue

                # 3) Caché IA (texto libre) - fallback adicional
                cached = cache.get(orden, ttl=TTL_IA)
                if cached is not None and isinstance(cached, str):
                    imprimir_respuesta(cached, fuente="cache")
                    await asyncio.to_thread(hablar, cached)
                    historial.append({"role": "assistant", "content": cached})
                    _guardar_memoria(historial)
                    continue

                # 2.5) Alias aprendidos (memoria)
                from jarvis_core.intents.normalize import normalize_text

                alias_key = normalize_text(orden)
                alias_dec = self.memory.state.aliases.get(alias_key)
                if isinstance(alias_dec, dict) and alias_dec.get("accion"):
                    respuesta = await self._execute_decision(alias_dec)
                    if respuesta:
                        imprimir_respuesta(respuesta, fuente="alias")
                        await asyncio.to_thread(hablar, respuesta)
                        historial.append({"role": "assistant", "content": respuesta})
                        _guardar_memoria(historial)
                    continue

                # 2.6) Macros (ej: "modo trabajo")
                if alias_key.startswith("modo "):
                    macro_name = alias_key.replace("modo ", "", 1).strip()
                    macro = self.memory.state.macros.get(macro_name)
                    if isinstance(macro, list) and macro:
                        respuesta = await self._execute_decision({"accion": "batch", "parametros": {"acciones": macro}})
                        if respuesta:
                            imprimir_respuesta(respuesta, fuente="macro")
                            await asyncio.to_thread(hablar, respuesta)
                            historial.append({"role": "assistant", "content": respuesta})
                            _guardar_memoria(historial)
                        continue

                # 3) Legacy rápido (por ahora): patrones directos
                match = self.registry.match(orden)
                if match is not None:
                    respuesta = await self._execute_decision(match.decision)
                    if respuesta:
                        imprimir_respuesta(respuesta, fuente="intent")
                        await asyncio.to_thread(hablar, respuesta)
                        historial.append({"role": "assistant", "content": respuesta})
                        _guardar_memoria(historial)
                    continue

                decision = await asyncio.to_thread(procesar_sin_ia_legacy, orden)
                if decision is not None:
                    respuesta = await self._execute_decision(decision)
                    if respuesta:
                        imprimir_respuesta(respuesta, fuente="patron")
                        await asyncio.to_thread(hablar, respuesta)
                        historial.append({"role": "assistant", "content": respuesta})
                        _guardar_memoria(historial)
                    continue

                # 4) IA local (Ollama) — AHORA CON HISTORIAL COMPLETO + SISTEMA
                with cronometro("ai") as c:
                    mensajes_ia = _construir_mensajes_ia(orden, historial)
                    resp = await self.ai.ask(orden, mensajes_ia, mode="ollama")

                if resp and resp.text:
                    imprimir_respuesta(resp.text, fuente=resp.provider, ms=c.ms)
                    await asyncio.to_thread(hablar, resp.text)
                    historial.append({"role": "assistant", "content": resp.text})
                    _guardar_memoria(historial)
                    cache.set(orden, resp.text, ttl=TTL_IA)
                    # Registrar respuesta en el motor de conversación
                    self.conversation.registrar_respuesta_jarvis(resp.text)
                    continue

                imprimir_estado("No pude obtener respuesta de ninguna IA.", "warn")

            except (EOFError, KeyboardInterrupt):
                print()
                await asyncio.to_thread(hablar, "Hasta luego")
                log.info("Jarvis cerrado por el usuario")
                await self.bus.stop()
                return
            except Exception as e:
                log.error("Error en bucle principal: %s", e, exc_info=True)
                imprimir_estado(f"Error: {e}", "error")


async def run_app_from_argv(argv: list[str]) -> None:
    mode = "texto"
    if "--voz" in argv:
        mode = "voz"
    if "--espera" in argv:
        mode = "espera"
    
    # Escanear modelos de Ollama disponibles y permitir selección
    print(f"\n{imprimir_estado('Escaneando modelos de Ollama...', 'info')}")
    modelos_disponibles = _escanear_modelos_ollama()
    modelo_seleccionado = _seleccionar_modelo_interactivo(modelos_disponibles, MODELO)
    
    app = JarvisApp(AppConfig(mode=mode), modelo_ollama=modelo_seleccionado)
    await app.run()


def main(argv: list[str] | None = None) -> int:
    argv = argv or sys.argv
    asyncio.run(run_app_from_argv(list(argv)))
    return 0

