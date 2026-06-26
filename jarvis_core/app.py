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
from jarvis_core.config_manager import ConfigManager
from jarvis_core.memory.episodic_memory import inicializar_tabla as inicializar_episodica, registrar as registrar_evento
from jarvis_core.memory.people_memory import (
    inicializar_tabla as inicializar_personas,
    obtener_contexto_personas,
    detectar_patron_persona,
    guardar_persona,
    proximos_cumpleanos
)
from jarvis_core.proactive_engine import iniciar_motor as iniciar_proactive, get_engine as get_proactive_engine
from jarvis_core.web_search import get_search_engine, WebSearchEngine


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
        # Gestor de configuración dinámica
        self.config = ConfigManager()
        self.config.load()
        # Procesador semántico (cache + intent matcher + IA clasificadora)
        self._procesador: ProcesadorSemantico | None = None
        # Motor de búsqueda web
        self.web_search: WebSearchEngine | None = None
        # Estado para persona pendiente de confirmación
        self._persona_pendiente: Optional[Dict] = None
        
        # Inicializar memorias
        try:
            inicializar_episodica()
            log.info("[APP] Memoria episódica inicializada")
        except Exception as e:
            log.warning("[APP] Error inicializando memoria episódica: %s", e)
        
        try:
            inicializar_personas()
            log.info("[APP] Memoria de personas inicializada")
            
            # Anunciar cumpleaños próximos al iniciar
            self._anunciar_cumpleanos_proximos()
        except Exception as e:
            log.warning("[APP] Error inicializando memoria de personas: %s", e)
        
        # Iniciar motor de sugerencias proactivas
        try:
            iniciar_proactive(
                config_manager=self.config,
                memory_store=self.memory,
                conversation_engine=self.conversation
            )
            log.info("[APP] Motor de sugerencias iniciado")
        except Exception as e:
            log.warning("[APP] Error iniciando motor de sugerencias: %s", e)

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
        
        # Inicializar motor de búsqueda web
        try:
            self.web_search = get_search_engine(ollama_caller=llamar_ia_ollama)
            log.info("[APP] Motor de búsqueda web inicializado")
        except Exception as e:
            log.warning("[APP] Error inicializando búsqueda web: %s", e)
        
        return self._procesador
    
    def _anunciar_cumpleanos_proximos(self) -> None:
        """Anuncia cumpleaños próximos al iniciar."""
        try:
            cumplidos = proximos_cumpleanos(dias=3)
            if cumplidos:
                mensajes = []
                for persona in cumplidos:
                    nombre = persona.get("nombre")
                    relacion = persona.get("relacion", "contacto")
                    mensajes.append(f"{nombre}, tu {relacion}")
                
                if len(mensajes) == 1:
                    saludo = f"Te recuerdo que {mensajes[0]} cumple años pronto."
                else:
                    saludo = f"Tienes cumpleaños próximos: {', '.join(mensajes)}."
                
                log.info("[CUMPLEAÑOS] %s", saludo)
        except Exception as e:
            log.warning("[APP] Error anunciando cumpleaños: %s", e)
    
    def _construir_contexto_enriquecido(self, orden: str) -> str:
        """Construye contexto enriquecido con personas y configuración para la IA."""
        partes = []
        
        # Extraer nombres mencionados en la orden
        palabras = orden.split()
        nombres_posibles = [p.strip(".,!?¿¡") for p in palabras if p[0].isupper()]
        
        if nombres_posibles:
            contexto_personas = obtener_contexto_personas(nombres_posibles)
            if contexto_personas:
                partes.append(contexto_personas)
        
        # Agregar reglas de configuración
        reglas = self.config.get("reglas_generales", [])
        if reglas:
            partes.append("Reglas del usuario: " + "; ".join(reglas[:5]))
        
        # Agregar preferencias de comportamiento
        if self.config.get("brevedad"):
            partes.append("Preferencia: sé breve en tus respuestas.")
        
        if self.config.get("solo_cuando_pregunte"):
            partes.append("Preferencia: solo responde cuando te pregunten algo.")
        
        return " | ".join(partes) if partes else ""

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

        self.plugins.load()

        await self.bus.start(workers=2)
        
        # Iniciar motor de conversación proactiva
        self.conversation.start()

        imprimir_banner(version="8", modo=self.cfg.mode, ia_local=True, nombre_usuario=NOMBRE_USUARIO)
        saludo = saludo_contextual()
        await asyncio.to_thread(hablar, saludo)

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

                o = orden.lower().strip()
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
                
                # Registrar evento en memoria episódica
                try:
                    registrar_evento("orden_recibida", orden[:200])
                except Exception:
                    pass
                
                historial.append({"role": "user", "content": orden})

                # ── Verificar patrón de persona ───────────────
                patron_persona = detectar_patron_persona(orden)
                if patron_persona and not self._persona_pendiente:
                    # Guardar para confirmación
                    self._persona_pendiente = patron_persona
                    pregunta_confirmacion = patron_persona.get("mensaje_confirmacion")
                    imprimir_respuesta(pregunta_confirmacion, fuente="personas")
                    await asyncio.to_thread(hablar, pregunta_confirmacion)
                    continue
                
                # ── Confirmar guardado de persona ───────────────
                if self._persona_pendiente:
                    respuesta_lower = orden.lower().strip()
                    confirmado = any(p in respuesta_lower for p in [
                        "sí", "si", "yes", "claro", "por supuesto",
                        "confirma", "aplica", "guarda", "ok", "vale"
                    ])
                    rechazado = any(p in respuesta_lower for p in [
                        "no", "cancela", "descarta", "olvida",
                        "mejor no", "no quiero"
                    ])
                    
                    if confirmado or rechazado:
                        tipo = self._persona_pendiente.get("tipo")
                        
                        if confirmado:
                            if tipo == "relacion":
                                exito, msg = guardar_persona(
                                    self._persona_pendiente["nombre"],
                                    relacion=self._persona_pendiente["relacion"]
                                )
                            elif tipo == "cumpleanos":
                                exito, msg = guardar_persona(
                                    self._persona_pendiente["nombre"],
                                    cumpleanos=self._persona_pendiente["cumpleanos"]
                                )
                            elif tipo == "gusto":
                                exito, msg = guardar_persona(
                                    self._persona_pendiente["nombre"],
                                    gustos=[self._persona_pendiente["gusto"]]
                                )
                            else:
                                exito, msg = True, "Información guardada"
                            
                            imprimir_respuesta(msg, fuente="personas")
                            await asyncio.to_thread(hablar, msg)
                        else:
                            msg = "Entendido, no guardaré esa información."
                            imprimir_respuesta(msg, fuente="personas")
                            await asyncio.to_thread(hablar, msg)
                        
                        self._persona_pendiente = None
                        continue
                
                # ── Verificar si es instrucción de configuración ───────────────
                resultado_config = self.config.detectar_instruccion(orden)
                if resultado_config["es_configuracion"]:
                    if resultado_config["accion"] == "consult":
                        # Consulta directa - mostrar resumen sin confirmación
                        resumen = self.config._generar_resumen_configuracion()
                        imprimir_respuesta(resumen, fuente="config")
                        await asyncio.to_thread(hablar, resumen)
                        historial.append({"role": "assistant", "content": resumen})
                        _guardar_memoria(historial)
                        continue
                    
                    # Preparar cambio y pedir confirmación
                    pregunta_confirmacion = self.config.preparar_cambio(resultado_config)
                    imprimir_respuesta(pregunta_confirmacion, fuente="config")
                    await asyncio.to_thread(hablar, pregunta_confirmacion)
                    
                    # Esperar respuesta del usuario (sí/no)
                    try:
                        respuesta = await self._get_order()
                        if respuesta:
                            self.conversation.registrar_interaccion(respuesta)
                            respuesta_lower = respuesta.lower().strip()
                            
                            # Detectar confirmación o rechazo
                            confirmado = any(p in respuesta_lower for p in [
                                "sí", "si", "yes", "claro", "por supuesto",
                                "confirma", "aplica", "guarda", "ok", "vale"
                            ])
                            rechazado = any(p in respuesta_lower for p in [
                                "no", "cancela", "descarta", "olvida",
                                "mejor no", "no quiero"
                            ])
                            
                            if confirmado:
                                exito, mensaje = self.config.confirmar_y_aplicar(True)
                            elif rechazado:
                                exito, mensaje = self.config.confirmar_y_aplicar(False)
                            else:
                                # Timeout implícito o respuesta ambigua - descartar
                                self.config._pending_change = None
                                mensaje = "No entendí tu respuesta. El cambio fue descartado."
                            
                            imprimir_respuesta(mensaje, fuente="config")
                            await asyncio.to_thread(hablar, mensaje)
                            historial.append({"role": "assistant", "content": mensaje})
                            _guardar_memoria(historial)
                            continue
                    except Exception as e:
                        log.warning("Error esperando confirmación: %s", e)
                        self.config._pending_change = None
                        continue

                # v8: Agent mode quick trigger (sintaxis: "agente: ...")
                if o.startswith("agente:"):
                    objective = orden.split(":", 1)[1].strip()
                    plan = await self.agent.plan(objective, historial)
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

                # 4) Búsqueda web si es necesario
                respuesta_web = None
                if self.web_search:
                    try:
                        resultados_busqueda = self.web_search.buscar(orden, forzar=False)
                        if resultados_busqueda:
                            # Formatear para la IA
                            contexto_web = self.web_search.formatear_para_ia(resultados_busqueda, orden)
                            
                            # Agregar contexto web al historial temporalmente
                            historial_temp = historial + [{"role": "system", "content": contexto_web}]
                            
                            with cronometro("ai") as c:
                                resp = await self.ai.ask(orden, historial_temp, mode="ollama")
                            
                            if resp and resp.text:
                                imprimir_respuesta(resp.text, fuente=resp.provider, ms=c.ms)
                                await asyncio.to_thread(hablar, resp.text)
                                historial.append({"role": "assistant", "content": resp.text})
                                _guardar_memoria(historial)
                                cache.set(orden, resp.text, ttl=TTL_IA)
                                self.conversation.registrar_respuesta_jarvis(resp.text)
                                continue
                    except Exception as e:
                        log.warning("[WEBSEARCH] Error en búsqueda: %s", e)
                        # Continuar con IA normal si falla búsqueda
                
                # 5) IA local (Ollama) sin búsqueda web
                with cronometro("ai") as c:
                    # Construir contexto enriquecido
                    contexto_extra = self._construir_contexto_enriquecido(orden)
                    
                    # Si hay contexto extra, agregarlo como sistema
                    if contexto_extra:
                        historial_con_contexto = [{"role": "system", "content": contexto_extra}] + historial
                        resp = await self.ai.ask(orden, historial_con_contexto, mode="ollama")
                    else:
                        resp = await self.ai.ask(orden, historial, mode="ollama")

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

