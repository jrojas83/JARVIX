# jarvis_core/proactive_engine.py — Motor de sugerencias proactivas
# ================================================================================
# Observa la actividad del usuario y hace sugerencias oportunas sin ser intrusivo.
#
# Características:
#   - Hilo en background que no bloquea el bucle principal
#   - Sistema de créditos para limitar interrupciones (máx 3/hora, mín 10 min entre cada una)
#   - Detecta cumpleaños, actividad prolongada, recordatorios próximos
#   - Respeta horario de silencio configurable
#   - No interrumpe si el usuario está hablando activamente

import threading
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from logger import log
from voz import hablar


class ProactiveEngine:
    """
    Motor de sugerencias proactivas para JARVIX.
    Corre en un hilo separado y hace sugerencias cuando es apropiado.
    """
    
    def __init__(
        self,
        config_manager=None,
        memory_store=None,
        conversation_engine=None
    ):
        self.config = config_manager
        self.memory = memory_store
        self.conversation = conversation_engine
        
        # Estado del motor
        self._running = False
        self._thread: Optional[threading.Thread] = None
        
        # Sistema de créditos
        self._creditos_maximos = 3  # Máx interrupciones por hora
        self._creditos_usados = 0
        self._ultima_interrupcion: Optional[datetime] = None
        self._intervalo_minimo_seg = 600  # 10 minutos entre interrupciones
        
        # Registro de sugerencias ya hechas hoy
        self._sugerencias_hoy: Dict[str, datetime] = {}
        
        # Apps monitoreadas y tiempo de uso
        self._app_inicio: Dict[str, datetime] = {}
        
        # Recordatorios pendientes (se inyectan desde fuera)
        self._recordatorios_pendientes: List[Dict] = []
    
    def start(self) -> bool:
        """Inicia el hilo de observación."""
        if self._running:
            return True
        
        try:
            self._running = True
            self._thread = threading.Thread(target=self._bucle_observacion, daemon=True)
            self._thread.start()
            log.info("[PROACTIVE] Motor de sugerencias iniciado")
            return True
        except Exception as e:
            log.warning("[PROACTIVE] Error iniciando motor: %s", e)
            return False
    
    def stop(self) -> None:
        """Detiene el hilo de observación."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
            log.info("[PROACTIVE] Motor de sugerencias detenido")
    
    def _bucle_observacion(self) -> None:
        """Bucle principal del motor de sugerencias."""
        while self._running:
            try:
                # Dormir 60 segundos entre ciclos
                time.sleep(60)
                
                # Verificar si debe interrumpir
                if not self._puede_interrumpir():
                    continue
                
                # Verificar condiciones en orden de prioridad
                sugerencia = self._verificar_condiciones()
                
                if sugerencia:
                    self._emitir_sugerencia(sugerencia)
            
            except Exception as e:
                log.warning("[PROACTIVE] Error en bucle de observación: %s", e)
    
    def _puede_interrumpir(self) -> bool:
        """Verifica si puede interrumpir en este momento."""
        ahora = datetime.now()
        
        # Verificar horario de silencio
        if self._en_horario_silencio(ahora):
            return False
        
        # Verificar día de no molestar
        if self._es_dia_no_molestar(ahora):
            return False
        
        # Verificar créditos disponibles
        if self._creditos_usados >= self._creditos_maximos:
            # Resetear créditos si pasó una hora
            if self._ultima_interrupcion and (ahora - self._ultima_interrupcion).total_seconds() > 3600:
                self._creditos_usados = 0
            else:
                return False
        
        # Verificar intervalo mínimo desde última interrupción
        if self._ultima_interrupcion:
            segundos_desde_ultima = (ahora - self._ultima_interrupcion).total_seconds()
            if segundos_desde_ultima < self._intervalo_minimo_seg:
                return False
        
        # Verificar si el usuario está hablando activamente
        if self.conversation and self.conversation.usuario_activo_recientemente(minutos=2):
            return False
        
        return True
    
    def _en_horario_silencio(self, ahora: datetime) -> bool:
        """Verifica si está en horario de silencio."""
        if not self.config:
            return False
        
        horario = self.config.get("horario_silencio", {})
        inicio_str = horario.get("inicio")
        fin_str = horario.get("fin")
        
        if not inicio_str or not fin_str:
            return False
        
        try:
            inicio = datetime.strptime(inicio_str, "%H:%M").time()
            fin = datetime.strptime(fin_str, "%H:%M").time()
            ahora_time = ahora.time()
            
            # Manejar caso donde el horario cruza medianoche
            if inicio > fin:
                # Ej: 21:00 a 08:00
                return ahora_time >= inicio or ahora_time <= fin
            else:
                # Ej: 01:00 a 06:00
                return inicio <= ahora_time <= fin
        
        except Exception:
            return False
    
    def _es_dia_no_molestar(self, ahora: datetime) -> bool:
        """Verifica si hoy es un día de no molestar."""
        if not self.config:
            return False
        
        dias_no_molestar = self.config.get("dias_no_molestar", [])
        if not dias_no_molestar:
            return False
        
        dia_actual = ahora.strftime("%A").lower()
        return dia_actual in dias_no_molestar
    
    def _verificar_condiciones(self) -> Optional[str]:
        """
        Verifica todas las condiciones posibles y retorna la sugerencia de mayor prioridad.
        
        Orden de prioridad:
          1. Cumpleaños en próximas 24h
          2. Actividad continua ≥90 minutos sin pausa
          3. Recordatorios que vencen en ≤15 minutos
          4. App activa ≥30 minutos con contexto relevante
          5. Primera actividad del día (buenos días)
          6. Inactividad después de 22:00 (buenas noches)
        """
        ahora = datetime.now()
        
        # 1. Cumpleaños próximos
        cumpleanos_msg = self._verificar_cumpleanos_proximos()
        if cumpleanos_msg:
            return cumpleanos_msg
        
        # 2. Actividad continua prolongada
        descanso_msg = self._verificar_descanso_necesario()
        if descanso_msg:
            return descanso_msg
        
        # 3. Recordatorios próximos
        recordatorio_msg = self._verificar_recordatorios_proximos(ahora)
        if recordatorio_msg:
            return recordatorio_msg
        
        # 4. App activa por mucho tiempo
        app_msg = self._verificar_app_actividad_prolongada()
        if app_msg:
            return app_msg
        
        # 5. Buenos días (primera actividad)
        buenos_dias_msg = self._verificar_buenos_dias()
        if buenos_dias_msg:
            return buenos_dias_msg
        
        # 6. Buenas noches (inactividad tarde)
        buenas_noches_msg = self._verificar_buenas_noches(ahora)
        if buenas_noches_msg:
            return buenas_noches_msg
        
        return None
    
    def _verificar_cumpleanos_proximos(self) -> Optional[str]:
        """Verifica si hay cumpleaños en las próximas 24h."""
        try:
            from jarvis_core.memory.people_memory import proximos_cumpleanos
            
            cumplidos = proximos_cumpleanos(dias=1)
            
            for persona in cumplidos:
                nombre = persona.get("nombre")
                clave_registro = f"cumpleanos_{nombre}"
                
                # Verificar si ya se mencionó hoy
                if clave_registro in self._sugerencias_hoy:
                    continue
                
                relacion = persona.get("relacion", "contacto")
                return f"Oye Juan, te cuento que {nombre}, tu {relacion}, cumple años {'mañana' if 'tomorrow' in str(persona) else 'hoy'}. ¿Quieres que prepare algo especial?"
        
        except Exception as e:
            log.warning("[PROACTIVE] Error verificando cumpleaños: %s", e)
        
        return None
    
    def _verificar_descanso_necesario(self) -> Optional[str]:
        """Verifica si el usuario lleva ≥90 minutos de actividad continua."""
        try:
            from jarvis_core.memory.episodic_memory import obtener_actividad_reciente, hay_actividad_en_ventana
            
            # Verificar actividad en los últimos 90 minutos
            eventos = obtener_actividad_reciente(minutos=90)
            
            if len(eventos) >= 10:  # Al menos 10 eventos en 90 min = actividad sostenida
                clave_registro = "descanso_90min"
                
                if clave_registro not in self._sugerencias_hoy:
                    return "Juan, llevas más de 90 minutos trabajando seguido. ¿Te parece si tomamos un descanso de 5 minutos? Tu espalda te lo agradecerá."
        
        except Exception as e:
            log.warning("[PROACTIVE] Error verificando descanso: %s", e)
        
        return None
    
    def _verificar_recordatorios_proximos(self, ahora: datetime) -> Optional[str]:
        """Verifica si hay recordatorios que vencen en ≤15 minutos."""
        try:
            # Verificar recordatorios inyectados
            for recordatorio in self._recordatorios_pendientes:
                vencimiento = recordatorio.get("vencimiento")
                if vencimiento:
                    diff_minutos = (vencimiento - ahora).total_seconds() / 60
                    
                    if 0 < diff_minutos <= 15:
                        clave_registro = f"recordatorio_{recordatorio.get('id', '')}"
                        
                        if clave_registro not in self._sugerencias_hoy:
                            mensaje = recordatorio.get("mensaje", "Tienes un recordatorio")
                            return f"Juan, en {int(diff_minutos)} minutos: {mensaje}"
        
        except Exception as e:
            log.warning("[PROACTIVE] Error verificando recordatorios: %s", e)
        
        return None
    
    def _verificar_app_actividad_prolongada(self) -> Optional[str]:
        """Verifica si hay una app abierta por ≥30 minutos."""
        try:
            from jarvis_core.memory.episodic_memory import obtener_actividad_reciente
            
            eventos = obtener_actividad_reciente(minutos=30)
            
            # Contar eventos por app
            apps_contador: Dict[str, int] = {}
            for evento in eventos:
                app = evento.get("app")
                if app:
                    apps_contador[app] = apps_contador.get(app, 0) + 1
            
            # Buscar app con más actividad
            for app, cantidad in apps_contador.items():
                if cantidad >= 15:  # Aproximadamente 30 min de actividad
                    clave_registro = f"app_{app}_30min"
                    
                    if clave_registro not in self._sugerencias_hoy:
                        # Sugerencia contextual según app
                        if app.lower() in ["vscode", "codigo", "editor"]:
                            return "Veo que llevas un buen rato programando. ¿Necesitas que busque documentación sobre algo?"
                        elif app.lower() in ["chrome", "firefox", "navegador"]:
                            return "Llevas un rato navegando. ¿Encontraste lo que buscabas o necesitas ayuda?"
        
        except Exception as e:
            log.warning("[PROACTIVE] Error verificando actividad de app: %s", e)
        
        return None
    
    def _verificar_buenos_dias(self) -> Optional[str]:
        """Verifica si es la primera actividad del día para saludar."""
        try:
            from jarvis_core.memory.episodic_memory import obtener_actividad_reciente
            
            ahora = datetime.now()
            
            # Solo entre 6am y 11am
            if not (6 <= ahora.hour <= 11):
                return None
            
            # Verificar si hay actividad antes de las 6am hoy
            eventos_madrugada = obtener_actividad_reciente(minutos=now.hour * 60)
            
            if len(eventos_madrugada) <= 1:  # Muy poca actividad, es temprano
                clave_registro = "buenos_dias"
                
                if clave_registro not in self._sugerencias_hoy:
                    return f"Buenos días Juan. ¿Cómo amaneciste? ¿Qué planes tienes para hoy?"
        
        except Exception as e:
            log.warning("[PROACTIVE] Error verificando buenos días: %s", e)
        
        return None
    
    def _verificar_buenas_noches(self, ahora: datetime) -> Optional[str]:
        """Verifica si es tarde y el usuario debería ir a dormir."""
        # Solo después de las 22:00
        if ahora.hour < 22:
            return None
        
        try:
            from jarvis_core.memory.episodic_memory import hay_actividad_en_ventana
            
            # Verificar si hubo actividad en los últimos 30 min
            if hay_actividad_en_ventana(minutos=30):
                clave_registro = "buenas_noches"
                
                if clave_registro not in self._sugerencias_hoy:
                    return "Juan, ya es tarde. Mañana será otro día productivo. ¿No crees que es hora de descansar?"
        
        except Exception as e:
            log.warning("[PROACTIVE] Error verificando buenas noches: %s", e)
        
        return None
    
    def _emitir_sugerencia(self, mensaje: str) -> None:
        """Emite una sugerencia por voz."""
        try:
            self._ultima_interrupcion = datetime.now()
            self._creditos_usados += 1
            
            # Registrar sugerencia como emitida hoy
            clave = f"sug_{datetime.now().strftime('%Y%m%d')}_{len(self._sugerencias_hoy)}"
            self._sugerencias_hoy[clave] = self._ultima_interrupcion
            
            log.info("[PROACTIVE] Sugiriendo: %s", mensaje[:100])
            
            # Hablar usando el sistema de voz existente
            hablar(mensaje, usar_frase_transicion=False)
        
        except Exception as e:
            log.warning("[PROACTIVE] Error emitiendo sugerencia: %s", e)
    
    def resetear_creditos_diarios(self) -> None:
        """Resetea el registro de sugerencias diarias."""
        ahora = datetime.now()
        dia_hoy = ahora.strftime("%Y-%m-%d")
        
        # Eliminar sugerencias de días anteriores
        claves_a_eliminar = []
        for clave, fecha in self._sugerencias_hoy.items():
            if fecha.strftime("%Y-%m-%d") != dia_hoy:
                claves_a_eliminar.append(clave)
        
        for clave in claves_a_eliminar:
            del self._sugerencias_hoy[clave]
        
        # Resetear créditos
        self._creditos_usados = 0
        log.info("[PROACTIVE] Créditos diarios reseteados")
    
    def agregar_recordatorio(self, recordatorio: Dict) -> None:
        """Agrega un recordatorio pendiente de verificar."""
        self._recordatorios_pendientes.append(recordatorio)
    
    def eliminar_recordatorio(self, id_recordatorio: str) -> None:
        """Elimina un recordatorio de la lista de pendientes."""
        self._recordatorios_pendientes = [
            r for r in self._recordatorios_pendientes 
            if r.get("id") != id_recordatorio
        ]
    
    def usuario_dijo_ahora_no(self) -> None:
        """Registra que el usuario rechazó una interrupción."""
        # Silenciar por 30 minutos
        self._ultima_interrupcion = datetime.now()
        self._intervalo_minimo_seg = 1800  # 30 minutos
        log.info("[PROACTIVE] Usuario rechazó interrupción. Silenciado por 30 min")


# Instancia global para acceso desde otros módulos
_engine: Optional[ProactiveEngine] = None


def get_engine() -> ProactiveEngine:
    """Obtiene la instancia global del motor."""
    global _engine
    if _engine is None:
        _engine = ProactiveEngine()
    return _engine


def iniciar_motor(config_manager=None, memory_store=None, conversation_engine=None) -> bool:
    """Inicializa e inicia el motor de sugerencias."""
    global _engine
    _engine = ProactiveEngine(
        config_manager=config_manager,
        memory_store=memory_store,
        conversation_engine=conversation_engine
    )
    return _engine.start()


def detener_motor() -> None:
    """Detiene el motor de sugerencias."""
    global _engine
    if _engine:
        _engine.stop()
