"""
jarvis_core/conversation.py — Motor de conversación proactiva para JARVIS
===========================================================================
100% OFFLINE. Sin APIs externas.

Características:
  - Inicia conversaciones después de períodos de inactividad
  - Hace preguntas contextuales basadas en la hora y actividad previa
  - Mantiene engagement con el usuario de manera natural
  - Se integra con el sistema de autonomía existente

Integración:
  from jarvis_core.conversation import ConversationEngine, cola_conversacion
  
  # En el bucle principal de jarvis.py:
  while not cola_conversacion.empty():
      msg = cola_conversacion.get_nowait()
      hablar(msg)
"""

import json
import logging
import queue
import random
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path

log = logging.getLogger("jarvis.conversation")

# Cola compartida con jarvis.py
cola_conversacion: queue.Queue = queue.Queue()

MEMORIA_FILE = Path.home() / ".jarvis_memory.json"

# Frases para iniciar conversación organizadas por contexto
CONVERSACIONES_MATUTINAS = [
    "¿Qué planes tienes para hoy?",
    "¿Dormiste bien anoche?",
    "¿Ya tomaste café esta mañana?",
    "¿Listo para productivo hoy?",
    "¿Hay algo importante que debas hacer hoy?",
]

CONVERSACIONES_TARDE = [
    "¿Cómo va tu día hasta ahora?",
    "¿Ya comiste algo?",
    "¿Necesitas un descanso?",
    "¿Vas a salir esta tarde?",
    "¿Todo bien con tus tareas?",
]

CONVERSACIONES_NOCHE = [
    "¿Qué tal te fue hoy?",
    "¿Lograste completar lo que tenías planeado?",
    "¿Ya cenaste?",
    "¿Algún plan para esta noche?",
    "¿Te gustaría relajarte un poco?",
]

CONVERSACIONES_FIN_DE_SEMANA = [
    "¿Qué planes tienes para el fin de semana?",
    "¿Vas a salir o te quedas en casa?",
    "¿Alguna película interesante que ver?",
    "¿Tiempo libre finalmente?",
    "¿Algo divertido planeado?",
]

PREGUNTAS_FOLLOWUP = [
    "Cuéntame más sobre eso.",
    "¿Y cómo te hizo sentir?",
    "¿Qué piensas hacer al respecto?",
    "Interesante, ¿por qué?",
    "¿Eso es bueno o malo?",
    "¿Necesitas ayuda con algo relacionado?",
]

RESPUESTAS_EMPATICAS = [
    "Entiendo perfectamente.",
    "Suena bien.",
    "Me alegra escuchar eso.",
    "Espero que todo salga bien.",
    "Cuenta conmigo para lo que necesites.",
    "Tiene sentido.",
]


class ConversationEngine:
    """
    Motor de conversación proactiva. Inicia diálogos con el usuario
    después de períodos de inactividad o en momentos apropiados.

    Parámetros
    ----------
    inactividad_min : minutos sin interacción para iniciar conversación (default 30)
    check_seg : frecuencia de revisión en segundos (default 60)
    max_conversaciones_dia : máximo de conversaciones iniciadas por día (default 5)
    """

    def __init__(self, inactividad_min: int = 30, check_seg: int = 60,
                 max_conversaciones_dia: int = 5):
        self.inactividad_min = inactividad_min
        self.check_seg = check_seg
        self.max_conversaciones_dia = max_conversaciones_dia

        self._ultimo_usuario: float = time.time()
        self._ultima_conversacion: float = 0
        self._conversaciones_hoy: int = 0
        self._dia_actual: str = datetime.now().strftime("%Y-%m-%d")
        self._activo: bool = False
        self._historial_conversacion: list = []

    def start(self):
        """Inicia el motor en un hilo daemon."""
        self._activo = True
        t = threading.Thread(target=self._loop, name="jarvis-conversation", daemon=True)
        t.start()
        log.info("[CONVERSATION] Motor iniciado — inactividad=%dmin", self.inactividad_min)

    def stop(self):
        self._activo = False

    def registrar_interaccion(self, texto: str = ""):
        """Llamar cada vez que el usuario envía un mensaje."""
        self._ultimo_usuario = time.time()
        
        # Guardar en historial para contexto futuro
        if texto:
            self._historial_conversacion.append({
                "role": "user",
                "content": texto,
                "timestamp": time.time()
            })
            # Limitar historial a últimas 20 interacciones
            self._historial_conversacion = self._historial_conversacion[-20:]

    def registrar_respuesta_jarvis(self, texto: str):
        """Registrar respuesta de Jarvis en el historial."""
        self._historial_conversacion.append({
            "role": "assistant",
            "content": texto,
            "timestamp": time.time()
        })
        self._historial_conversacion = self._historial_conversacion[-20:]

    def _loop(self):
        while self._activo:
            try:
                self._check_reset_diario()
                self._check_iniciar_conversacion()
            except Exception as e:
                log.error("[CONVERSATION] Error: %s", e, exc_info=True)
            time.sleep(self.check_seg)

    def _check_reset_diario(self):
        """Resetea el contador de conversaciones si es un nuevo día."""
        hoy = datetime.now().strftime("%Y-%m-%d")
        if hoy != self._dia_actual:
            self._dia_actual = hoy
            self._conversaciones_hoy = 0
            log.info("[CONVERSATION] Nuevo día, reseteando contador")

    def _check_iniciar_conversacion(self):
        """Verifica si es momento de iniciar una conversación."""
        # Verificar límite diario
        if self._conversaciones_hoy >= self.max_conversaciones_dia:
            return

        # Verificar tiempo desde última conversación (mínimo 15 min entre conversaciones)
        if time.time() - self._ultima_conversacion < 900:  # 15 minutos
            return

        # Verificar inactividad del usuario
        mins_inactivo = int((time.time() - self._ultimo_usuario) / 60)
        if mins_inactivo < self.inactividad_min:
            return

        # Es momento de iniciar conversación
        self._ultima_conversacion = time.time()
        self._conversaciones_hoy += 1

        mensaje = self._generar_mensaje_contextual()
        if mensaje:
            log.info("[CONVERSATION] Iniciando conversación: %s", mensaje)
            self._emitir(mensaje)

    def _generar_mensaje_contextual(self) -> str:
        """Genera un mensaje contextual basado en hora y día."""
        now = datetime.now()
        hora = now.hour
        dia_semana = now.strftime("%A").lower()

        # Determinar tipo de día
        es_fin_de_semana = dia_semana in ["saturday", "sunday"]

        # Seleccionar conjunto de frases según contexto
        if es_fin_de_semana:
            frases = CONVERSACIONES_FIN_DE_SEMANA
        elif 5 <= hora < 12:
            frases = CONVERSACIONES_MATUTINAS
        elif 12 <= hora < 19:
            frases = CONVERSACIONES_TARDE
        else:
            frases = CONVERSACIONES_NOCHE

        # Seleccionar frase aleatoria
        mensaje = random.choice(frases)

        # Opcionalmente añadir followup si hay historial reciente
        if self._historial_conversacion and random.random() < 0.3:
            # 30% de probabilidad de hacer followup
            ultimo_user = None
            for msg in reversed(self._historial_conversacion):
                if msg["role"] == "user":
                    ultimo_user = msg["content"]
                    break
            
            if ultimo_user and len(ultimo_user) > 20:
                followup = random.choice(PREGUNTAS_FOLLOWUP)
                mensaje = f"{mensaje} {followup}"

        return mensaje

    def _emitir(self, msg: str):
        """Emite un mensaje a la cola de conversación."""
        cola_conversacion.put(msg)

    def obtener_estado(self) -> dict:
        """Obtiene el estado actual del motor de conversación."""
        return {
            "activo": self._activo,
            "inactividad_min": self.inactividad_min,
            "conversaciones_hoy": self._conversaciones_hoy,
            "max_conversaciones_dia": self.max_conversaciones_dia,
            "ultima_actividad": datetime.fromtimestamp(self._ultimo_usuario).strftime("%H:%M:%S"),
        }

    def configurar(self, inactividad_min: int = None, max_conversaciones_dia: int = None):
        """Configura parámetros del motor."""
        if inactividad_min is not None:
            self.inactividad_min = inactividad_min
        if max_conversaciones_dia is not None:
            self.max_conversaciones_dia = max_conversaciones_dia
        log.info("[CONVERSATION] Configuración actualizada")
