# jarvis_core/config_manager.py — Gestión de configuración dinámica por conversación
# ================================================================================
# Permite que JARVIX se autoconfigure mediante conversación sin reiniciarse.
#
# Características:
#   - Archivo ~/.jarvis_config.json separado del código
#   - Detección de instrucciones de configuración en conversación
#   - Confirmación antes de aplicar cambios
#   - Aplicación en caliente (sin reiniciar)
#   - Consultar y borrar configuraciones existentes
#
# Uso:
#   from jarvis_core.config_manager import ConfigManager
#   config = ConfigManager()
#   config.load()  # Lee el archivo al iniciar
#   
#   # Detectar si es instrucción de configuración
#   resultado = config.detectar_instruccion("no me llames Juan, llámame Juancho")
#   if resultado["es_configuracion"]:
#       # Pedir confirmación al usuario
#       if usuario_confirma:
#           config.aplicar_cambio(resultado["tipo"], resultado["valor"])
#           config.save()

import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from logger import log


def _default_path() -> str:
    """Ruta por defecto del archivo de configuración."""
    return os.path.join(os.path.expanduser("~"), ".jarvis_config.json")


# Estructura default de configuración
DEFAULT_CONFIG = {
    # Preferencias básicas
    "nombre_usuario": "Juan",  # Cómo JARVIX llama al usuario
    "idioma": "es",            # Idioma preferido (es, en)
    
    # Horarios
    "horario_silencio": {      # Horarios donde no debe interrumpir
        "inicio": None,        # Hora inicio (ej: "21:00")
        "fin": None,           # Hora fin (ej: "08:00")
        "dias_excluidos": []   # Días donde no aplica (ej: ["sabado", "domingo"])
    },
    "dias_no_molestar": [],    # Días completos sin interrupciones
    
    # Comportamiento
    "frecuencia_interrupciones": 2,  # Máx interrupciones por hora
    "brevedad": False,               # Respuestas más cortas
    "saludos_matutinos": True,       # Saludar en las mañanas
    "solo_cuando_pregunte": False,   # Solo hablar cuando le pregunten
    
    # Apps que debe ignorar/silenciar
    "apps_silenciosas": [],    # Lista de apps donde no interrumpir
    
    # Velocidad de habla (si aplica)
    "velocidad_habla": 1.0,    # 0.5=lento, 1.0=normal, 2.0=rápido
    
    # Reglas personalizadas (texto libre)
    "reglas_generales": [],
    
    # Metadata
    "_ultima_modificacion": None,
}


class ConfigManager:
    """
    Gestor de configuración dinámica para JARVIX.
    Permite modificar preferencias mediante conversación.
    """
    
    def __init__(self, path: Optional[str] = None):
        self.path = path or _default_path()
        self.config = dict(DEFAULT_CONFIG)
        self._pending_change: Optional[Dict] = None  # Cambio pendiente de confirmación
    
    def load(self) -> bool:
        """Carga la configuración desde el archivo."""
        if not os.path.exists(self.path):
            log.info("[CONFIG] No existe archivo de configuración, usando defaults")
            self.config = dict(DEFAULT_CONFIG)
            return True
        
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            
            # Fusionar con defaults para asegurar todas las claves
            self.config = dict(DEFAULT_CONFIG)
            self._deep_update(self.config, loaded)
            
            log.info("[CONFIG] Configuración cargada desde %s", self.path)
            return True
        except Exception as e:
            log.warning("[CONFIG] Error cargando configuración: %s", e)
            self.config = dict(DEFAULT_CONFIG)
            return False
    
    def save(self) -> bool:
        """Guarda la configuración actual en el archivo."""
        try:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
        except Exception:
            pass
        
        try:
            self.config["_ultima_modificacion"] = datetime.now().isoformat()
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            log.info("[CONFIG] Configuración guardada en %s", self.path)
            return True
        except Exception as e:
            log.warning("[CONFIG] Error guardando configuración: %s", e)
            return False
    
    def _deep_update(self, base: dict, update: dict):
        """Actualiza recursivamente un diccionario."""
        for key, value in update.items():
            if key.startswith("_"):
                continue  # Ignorar metadata interna
            if isinstance(value, dict) and key in base and isinstance(base[key], dict):
                self._deep_update(base[key], value)
            else:
                base[key] = value
    
    def get(self, key: str, default: Any = None) -> Any:
        """Obtiene un valor de configuración."""
        keys = key.split(".")
        current = self.config
        for k in keys:
            if isinstance(current, dict) and k in current:
                current = current[k]
            else:
                return default
        return current
    
    def set(self, key: str, value: Any) -> bool:
        """Establece un valor de configuración directamente."""
        keys = key.split(".")
        current = self.config
        for k in keys[:-1]:
            if k not in current:
                current[k] = {}
            current = current[k]
        current[keys[-1]] = value
        return True
    
    # ── Detección de instrucciones de configuración ───────────────────────
    
    def detectar_instruccion(self, texto: str) -> Dict[str, Any]:
        """
        Analiza el texto para detectar si es una instrucción de configuración.
        
        Returns:
            dict con:
                - es_configuracion: bool
                - tipo: str (nombre_usuario, horario, app_silenciosa, etc.)
                - valor: any (el valor a configurar)
                - confirmacion_requerida: str (mensaje para confirmar)
                - accion: str ('set', 'delete', 'consult')
        """
        texto_lower = texto.lower().strip()
        
        # ── Consulta de configuración actual ─────────────────────────
        if any(p in texto_lower for p in [
            "cómo estás configurado", "como estas configurado",
            "qué reglas tienes", "que reglas tienes",
            "cuál es tu configuración", "cual es tu configuracion",
            "dime tu configuración", "configuracion actual"
        ]):
            return {
                "es_configuracion": True,
                "tipo": "consultar",
                "accion": "consult",
                "confirmacion_requerida": None
            }
        
        # ── Borrar/olvidar regla ─────────────────────────────────────
        patrones_borrar = [
            r"olvida(?: que)?(?: que te dije)?(?: que)?(.+)",
            r"borra(?:r)?(?: la)?(?: regla)?(?: de)?(.+)",
            r"elimina(?:r)?(?: la)?(?: regla)?(?: de)?(.+)",
            r"quita(?:r)?(?: la)?(?: regla)?(?: de)?(.+)",
            r"no recuerdes(?: más)?(?: que)?(.+)",
        ]
        
        for patron in patrones_borrar:
            match = re.search(patron, texto_lower)
            if match:
                contenido = match.group(1).strip() if match.lastindex else ""
                return {
                    "es_configuracion": True,
                    "tipo": "borrar",
                    "accion": "delete",
                    "contenido_borrar": contenido,
                    "confirmacion_requerida": f"¿Quieres que olvide la regla relacionada con '{contenido}'?"
                }
        
        # ── Cambiar nombre del usuario ───────────────────────────────
        # Patrones: "llámame X", "no me llames X, llámame Y", "me puedes llamar X"
        match_nombre = re.search(
            r"llámame\s+([a-zA-ZÁÉÍÓÚÑáéíóúñ]+)",
            texto_lower
        )
        if not match_nombre:
            match_nombre = re.search(
                r"me puedes llamar\s+([a-zA-ZÁÉÍÓÚÑáéíóúñ]+)",
                texto_lower
            )
        if not match_nombre:
            match_nombre = re.search(
                r"mi nombre es\s+([a-zA-ZÁÉÍÓÚÑáéíóúñ]+)",
                texto_lower
            )
        
        if match_nombre:
            nuevo_nombre = match_nombre.group(1).strip().title()
            return {
                "es_configuracion": True,
                "tipo": "nombre_usuario",
                "valor": nuevo_nombre,
                "accion": "set",
                "confirmacion_requerida": f"¿Quieres que te llame '{nuevo_nombre}' en lugar de '{self.get('nombre_usuario')}'?"
            }
        
        # ── Horario de silencio ──────────────────────────────────────
        # "no me molestes después de las 9pm"
        match_horario_fin = re.search(
            r"(?:no me moleste?s?|no interrumpas|silencio)(?:\s+(?:más|después|a partir))?\.?\s*(?:de)?\s*(?:las?|las)\s*(\d{1,2})(?::(\d{2}))?\s*(am|pm|a\.m\.|p\.m\.|horas)?",
            texto_lower
        )
        if match_horario_fin:
            hora = int(match_horario_fin.group(1))
            minuto = int(match_horario_fin.group(2)) if match_horario_fin.group(2) else 0
            periodo = match_horario_fin.group(3) or ""
            
            if "pm" in periodo or "p.m." in periodo:
                if hora < 12:
                    hora += 12
            elif "am" in periodo or "a.m." in periodo:
                if hora == 12:
                    hora = 0
            
            hora_str = f"{hora:02d}:{minuto:02d}"
            return {
                "es_configuracion": True,
                "tipo": "horario_silencio.fin",
                "valor": hora_str,
                "accion": "set",
                "confirmacion_requerida": f"¿Quieres que no te moleste después de las {hora_str}?"
            }
        
        # "no me molestes antes de las 8am"
        match_horario_inicio = re.search(
            r"(?:no me moleste?s?|no interrumpas)(?:\s+(?:antes|hasta))?\.?\s*(?:de)?\s*(?:las?|las)\s*(\d{1,2})(?::(\d{2}))?\s*(am|pm|a\.m\.|p\.m\.|horas)?",
            texto_lower
        )
        if match_horario_inicio and "antes" in texto_lower:
            hora = int(match_horario_inicio.group(1))
            minuto = int(match_horario_inicio.group(2)) if match_horario_inicio.group(2) else 0
            periodo = match_horario_inicio.group(3) or ""
            
            if "pm" in periodo or "p.m." in periodo:
                if hora < 12:
                    hora += 12
            elif "am" in periodo or "a.m." in periodo:
                if hora == 12:
                    hora = 0
            
            hora_str = f"{hora:02d}:{minuto:02d}"
            return {
                "es_configuracion": True,
                "tipo": "horario_silencio.inicio",
                "valor": hora_str,
                "accion": "set",
                "confirmacion_requerida": f"¿Quieres que no te moleste antes de las {hora_str}?"
            }
        
        # "los domingos no me hables" / "los sábados no trabajo"
        dias_semana = {
            "lunes": "monday", "martes": "tuesday", "miércoles": "wednesday",
            "miercoles": "wednesday", "jueves": "thursday", "viernes": "friday",
            "sábado": "saturday", "sabado": "saturday",
            "domingo": "sunday"
        }
        
        for dia_es, dia_en in dias_semana.items():
            if f"{dia_es}" in texto_lower or f"los {dia_es}" in texto_lower:
                if any(p in texto_lower for p in ["no me hables", "no me molestes", "no trabajo", "no interrumpas"]):
                    return {
                        "es_configuracion": True,
                        "tipo": "dias_no_molestar",
                        "valor": dia_en,
                        "accion": "add_to_list",
                        "confirmacion_requerida": f"¿Quieres que no te moleste los {dia_es}?"
                    }
        
        # ── Apps silenciosas ─────────────────────────────────────────
        # "cuando tenga Chrome abierto no interrumpas"
        # "si abro Netflix silénciate"
        # "cuando abra VSCode no digas nada"
        
        apps_conocidas = [
            "chrome", "firefox", "navegador", "chromium",
            "vscode", "codigo", "visual studio", "editor",
            "netflix", "spotify", "youtube",
            "discord", "telegram", "whatsapp",
            "libreoffice", "word", "excel",
            "terminal", "bash", "consola"
        ]
        
        for app in apps_conocidas:
            if app in texto_lower:
                if any(p in texto_lower for p in [
                    "no interrumpas", "no digas nada", "silenciate", "silénciate",
                    "no me molestes", "no hables", "cállate", "callate"
                ]):
                    app_normalizada = self._normalizar_app(app)
                    return {
                        "es_configuracion": True,
                        "tipo": "apps_silenciosas",
                        "valor": app_normalizada,
                        "accion": "add_to_list",
                        "confirmacion_requerida": f"¿Quieres que no te interrumpa cuando tengas {app_normalizada} abierto?"
                    }
        
        # ── Frecuencia de interrupciones ─────────────────────────────
        match_frecuencia = re.search(
            r"no me interrumpas(?: más)?(?: de)?\s*(\d+)\s*(?:vez|veces|interrupciones?)\s*(?:por)?\s*(?:cada)?\s*(hora|horas|minuto|minutos)?",
            texto_lower
        )
        if match_frecuencia:
            cantidad = int(match_frecuencia.group(1))
            unidad = match_frecuencia.group(2) or "hora"
            return {
                "es_configuracion": True,
                "tipo": "frecuencia_interrupciones",
                "valor": cantidad,
                "accion": "set",
                "confirmacion_requerida": f"¿Quieres que no te interrumpa más de {cantidad} veces por {unidad}?"
            }
        
        # ── Comportamiento: brevedad ─────────────────────────────────
        if any(p in texto_lower for p in [
            "sé más breve", "se más breve", "respuestas cortas",
            "habla menos", "sé conciso", "se conciso"
        ]):
            return {
                "es_configuracion": True,
                "tipo": "brevedad",
                "valor": True,
                "accion": "set",
                "confirmacion_requerida": "¿Quieres que sea más breve en mis respuestas?"
            }
        
        # ── Comportamiento: saludos matutinos ────────────────────────
        if any(p in texto_lower for p in [
            "no me saludes en las mañanas", "no me saludes por la mañana",
            "no saludes en la mañana", "quítame los saludos"
        ]):
            return {
                "es_configuracion": True,
                "tipo": "saludos_matutinos",
                "valor": False,
                "accion": "set",
                "confirmacion_requerida": "¿Quieres que no te salute en las mañanas?"
            }
        
        # ── Comportamiento: solo cuando pregunte ─────────────────────
        if any(p in texto_lower for p in [
            "habla solo cuando te pregunte", "no hables si no te pregunto",
            "solo responde preguntas", "sé reactivo"
        ]):
            return {
                "es_configuracion": True,
                "tipo": "solo_cuando_pregunte",
                "valor": True,
                "accion": "set",
                "confirmacion_requerida": "¿Quieres que solo hable cuando me preguntes algo?"
            }
        
        # ── Velocidad de habla ───────────────────────────────────────
        if any(p in texto_lower for p in [
            "habla más rápido", "habla mas rápido", "más rápido", "mas rapido"
        ]):
            return {
                "es_configuracion": True,
                "tipo": "velocidad_habla",
                "valor": 1.5,
                "accion": "set",
                "confirmacion_requerida": "¿Quieres que hable más rápido?"
            }
        
        if any(p in texto_lower for p in [
            "habla más lento", "habla mas lento", "más lento", "mas lento",
            "habla despacio"
        ]):
            return {
                "es_configuracion": True,
                "tipo": "velocidad_habla",
                "valor": 0.7,
                "accion": "set",
                "confirmacion_requerida": "¿Quieres que hable más lento?"
            }
        
        # ── Regla general (catch-all para preferencias no clasificadas) ─
        # Detectar frases que parecen preferencias pero no encajan en categorías específicas
        if any(p in texto_lower for p in [
            "quiero que", "prefiero que", "me gustaría que",
            "recuerda que", "ten en cuenta que", "considera que"
        ]):
            # Extraer la regla completa
            regla = texto.strip()
            return {
                "es_configuracion": True,
                "tipo": "reglas_generales",
                "valor": regla,
                "accion": "add_to_list",
                "confirmacion_requerida": f"¿Quieres que recuerde esta preferencia: '{regla}'?"
            }
        
        # No es una instrucción de configuración
        return {
            "es_configuracion": False,
            "tipo": None,
            "valor": None,
            "accion": None,
            "confirmacion_requerida": None
        }
    
    def _normalizar_app(self, app: str) -> str:
        """Normaliza el nombre de una app a su forma canónica."""
        app_lower = app.lower().strip()
        
        mapeo_apps = {
            "chrome": "Chrome",
            "firefox": "Firefox",
            "navegador": "Navegador",
            "chromium": "Chromium",
            "vscode": "VSCode",
            "codigo": "VSCode",
            "visual studio": "VSCode",
            "editor": "Editor",
            "netflix": "Netflix",
            "spotify": "Spotify",
            "youtube": "YouTube",
            "discord": "Discord",
            "telegram": "Telegram",
            "whatsapp": "WhatsApp",
            "libreoffice": "LibreOffice",
            "word": "Word",
            "excel": "Excel",
            "terminal": "Terminal",
            "bash": "Terminal",
            "consola": "Terminal"
        }
        
        return mapeo_apps.get(app_lower, app.title())
    
    # ── Aplicación de cambios ────────────────────────────────────────
    
    def preparar_cambio(self, instruccion: Dict[str, Any]) -> str:
        """Prepara un cambio pendiente de confirmación."""
        self._pending_change = instruccion
        return instruccion.get("confirmacion_requerida", "¿Confirmas este cambio?")
    
    def confirmar_y_aplicar(self, confirmado: bool) -> Tuple[bool, str]:
        """
        Aplica o descarta el cambio pendiente según confirmación.
        
        Returns:
            (exitoso, mensaje)
        """
        if not self._pending_change:
            return False, "No hay ningún cambio pendiente."
        
        if not confirmado:
            msg = "Entendido, no guardaré ese cambio."
            self._pending_change = None
            return True, msg
        
        instruccion = self._pending_change
        self._pending_change = None
        
        tipo = instruccion.get("tipo")
        valor = instruccion.get("valor")
        accion = instruccion.get("accion")
        
        if accion == "set":
            self.set(tipo, valor)
            self.save()
            return True, f"Configuración actualizada: {tipo} = {valor}"
        
        elif accion == "add_to_list":
            lista = self.get(tipo, [])
            if not isinstance(lista, list):
                lista = []
            if valor not in lista:
                lista.append(valor)
                self.set(tipo, lista)
                self.save()
                return True, f"Agregado a {tipo}: {valor}"
            else:
                return True, f"{valor} ya estaba en {tipo}"
        
        elif accion == "delete":
            return self._procesar_borrado(instruccion.get("contenido_borrar", ""))
        
        elif accion == "consult":
            return True, self._generar_resumen_configuracion()
        
        return False, "Tipo de acción no reconocido"
    
    def _procesar_borrado(self, contenido: str) -> Tuple[bool, str]:
        """Procesa la solicitud de borrar una regla."""
        eliminados = []
        contenido_lower = contenido.lower()
        
        # Extraer palabras clave del contenido (apps, días, etc.)
        apps_conocidas = ["chrome", "firefox", "vscode", "codigo", "netflix", "spotify", 
                          "youtube", "discord", "telegram", "whatsapp", "terminal", "bash"]
        dias_conocidos = ["lunes", "martes", "miércoles", "miercoles", "jueves", 
                          "viernes", "sábado", "sabado", "domingo"]
        
        # Buscar app mencionada en el contenido
        app_encontrada = None
        for app in apps_conocidas:
            if app in contenido_lower:
                app_encontrada = self._normalizar_app(app)
                break
        
        # Buscar día mencionado en el contenido
        dia_encontrado = None
        for dia_es, dia_en in [("lunes", "monday"), ("martes", "tuesday"), 
                                ("miércoles", "wednesday"), ("miercoles", "wednesday"),
                                ("jueves", "thursday"), ("viernes", "friday"),
                                ("sábado", "saturday"), ("sabado", "saturday"),
                                ("domingo", "sunday")]:
            if dia_es in contenido_lower:
                dia_encontrado = dia_en
                break
        
        # Buscar en reglas generales
        reglas = self.get("reglas_generales", [])
        nuevas_reglas = []
        for regla in reglas:
            if contenido_lower in regla.lower() or (app_encontrada and app_encontrada.lower() in regla.lower()):
                eliminados.append(f"regla: '{regla}'")
            else:
                nuevas_reglas.append(regla)
        
        if eliminados:
            self.set("reglas_generales", nuevas_reglas)
        
        # Buscar en apps silenciosas
        apps = self.get("apps_silenciosas", [])
        nuevas_apps = []
        for app in apps:
            if app_encontrada and app.lower() == app_encontrada.lower():
                eliminados.append(f"app: {app}")
            elif contenido_lower in app.lower():
                eliminados.append(f"app: {app}")
            else:
                nuevas_apps.append(app)
        
        if nuevas_apps != apps:
            self.set("apps_silenciosas", nuevas_apps)
        
        # Buscar en días no molestar
        dias = self.get("dias_no_molestar", [])
        nuevos_dias = []
        for dia in dias:
            if dia_encontrado and dia == dia_encontrado:
                eliminados.append(f"día: {dia}")
            elif contenido_lower in dia.lower():
                eliminados.append(f"día: {dia}")
            else:
                nuevos_dias.append(dia)
        
        if nuevos_dias != dias:
            self.set("dias_no_molestar", nuevos_dias)
        
        if eliminados:
            self.save()
            return True, f"Eliminado: {', '.join(eliminados)}"
        else:
            return True, f"No encontré reglas relacionadas con '{contenido}'"
    
    def _generar_resumen_configuracion(self) -> str:
        """Genera un resumen en lenguaje natural de la configuración actual."""
        lineas = ["Así estoy configurado actualmente:"]
        
        # Nombre
        nombre = self.get("nombre_usuario")
        if nombre:
            lineas.append(f"  • Te llamo: {nombre}")
        
        # Horario silencio
        horario = self.get("horario_silencio", {})
        if horario.get("inicio") or horario.get("fin"):
            partes = []
            if horario.get("inicio"):
                partes.append(f"desde las {horario['inicio']}")
            if horario.get("fin"):
                partes.append(f"hasta las {horario['fin']}")
            lineas.append(f"  • Horario de silencio: {' '.join(partes)}")
        
        # Días no molestar
        dias = self.get("dias_no_molestar", [])
        if dias:
            dias_es = []
            traductor = {
                "monday": "lunes", "tuesday": "martes", "wednesday": "miércoles",
                "thursday": "jueves", "friday": "viernes",
                "saturday": "sábado", "sunday": "domingo"
            }
            for dia in dias:
                dias_es.append(traductor.get(dia, dia))
            lineas.append(f"  • Días sin interrupciones: {', '.join(dias_es)}")
        
        # Frecuencia interrupciones
        freq = self.get("frecuencia_interrupciones")
        if freq:
            lineas.append(f"  • Máximo {freq} interrupciones por hora")
        
        # Apps silenciosas
        apps = self.get("apps_silenciosas", [])
        if apps:
            lineas.append(f"  • No interrumpo cuando usas: {', '.join(apps)}")
        
        # Comportamiento
        if self.get("brevedad"):
            lineas.append("  • Modo breve activado")
        
        if not self.get("saludos_matutinos", True):
            lineas.append("  • Sin saludos matutinos")
        
        if self.get("solo_cuando_pregunte"):
            lineas.append("  • Solo hablo cuando me preguntas")
        
        # Velocidad
        velocidad = self.get("velocidad_habla", 1.0)
        if velocidad != 1.0:
            if velocidad > 1.0:
                lineas.append("  • Hablo más rápido de lo normal")
            else:
                lineas.append("  • Hablo más lento de lo normal")
        
        # Reglas generales
        reglas = self.get("reglas_generales", [])
        if reglas:
            lineas.append("  • Reglas personalizadas:")
            for regla in reglas[:5]:  # Mostrar máximo 5
                lineas.append(f"    - {regla}")
            if len(reglas) > 5:
                lineas.append(f"    ... y {len(reglas) - 5} más")
        
        if len(lineas) == 1:
            return "No tienes configuraciones personalizadas aún. ¿Quieres cambiar algo?"
        
        return "\n".join(lineas)
    
    def reset_to_defaults(self) -> bool:
        """Resetea la configuración a los valores por defecto."""
        self.config = dict(DEFAULT_CONFIG)
        return self.save()
