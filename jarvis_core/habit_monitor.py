# jarvis_core/habit_monitor.py — Monitor de hábitos basado en memoria episódica
# ================================================================================
# Detecta patrones de comportamiento usando la memoria episódica y recuerda
# hábitos saludables sin necesidad de configuración manual.
#
# Características:
#   - Reglas configurables de hábitos (agua, descanso visual, pausa activa, noche)
#   - Detección automática basada en actividad del usuario
#   - Integración con el motor de sugerencias proactivas
#   - Persistencia de reglas personalizadas en ~/.jarvis_config.json

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any

from logger import log


# Reglas por defecto
REGLAS_DEFAULT = [
    {
        'nombre': 'agua',
        'descripcion': 'Agua cada 90 minutos',
        'intervalo_min': 90,
        'mensaje': 'Llevas más de 90 minutos sin tomar agua',
        'tipo_evento': 'habito_agua',
        'activo': True,
        'frecuencia_minima': 90
    },
    {
        'nombre': 'descanso_visual',
        'descripcion': 'Descanso visual cada 60 minutos',
        'intervalo_min': 60,
        'mensaje': 'Regla 20-20-20: mira algo a 6 metros por 20 segundos',
        'tipo_evento': 'habito_descanso',
        'activo': True,
        'frecuencia_minima': 60
    },
    {
        'nombre': 'pausa_activa',
        'descripcion': 'Pausa activa cada 2 horas',
        'intervalo_min': 120,
        'mensaje': 'Llevas 2 horas seguidas trabajando, considera levantarte 5 minutos',
        'tipo_evento': 'habito_pausa',
        'activo': True,
        'frecuencia_minima': 120
    },
    {
        'nombre': 'noche',
        'descripcion': 'Sin actividad nocturna',
        'intervalo_min': None,  # Se basa en la hora, no en actividad continua
        'mensaje': 'Son más de las 11pm, ¿no deberías descansar?',
        'tipo_evento': 'habito_noche',
        'activo': True,
        'frecuencia_minima': 1440,  # Una vez por día (24h)
        'hora_limite': 23  # Hora a partir de la cual se activa
    }
]


# Estado global
_ultimos_disparos: Dict[str, datetime] = {}
_reglas_cargadas: Optional[List[Dict]] = None


def _default_config_path() -> str:
    """Ruta por defecto del archivo de configuración."""
    return str(Path.home() / ".jarvis_config.json")


def _cargar_reglas() -> List[Dict]:
    """Carga las reglas desde configuración o usa las por defecto."""
    global _reglas_cargadas
    
    if _reglas_cargadas is not None:
        return _reglas_cargadas
    
    try:
        config_path = Path(_default_config_path())
        if config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            reglas_personalizadas = config.get('habit_rules', [])
            
            if reglas_personalizadas:
                # Fusionar con defaults
                _reglas_cargadas = []
                nombres_defaults = {r['nombre'] for r in REGLAS_DEFAULT}
                
                # Agregar reglas personalizadas
                for regla in reglas_personalizadas:
                    _reglas_cargadas.append(regla)
                    if regla.get('nombre') in nombres_defaults:
                        nombres_defaults.remove(regla['nombre'])
                
                # Agregar defaults no reemplazados
                for regla in REGLAS_DEFAULT:
                    if regla['nombre'] in nombres_defaults:
                        _reglas_cargadas.append(regla)
                
                return _reglas_cargadas
        
        # Usar defaults
        _reglas_cargadas = [dict(r) for r in REGLAS_DEFAULT]
        return _reglas_cargadas
        
    except Exception as e:
        log.warning("[HABIT_MONITOR] Error cargando reglas: %s", e)
        _reglas_cargadas = [dict(r) for r in REGLAS_DEFAULT]
        return _reglas_cargadas


def _guardar_reglas() -> bool:
    """Guarda las reglas actuales en la configuración."""
    try:
        config_path = Path(_default_config_path())
        
        # Cargar configuración existente
        config = {}
        if config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
        
        # Actualizar reglas
        config['habit_rules'] = _reglas_cargadas or REGLAS_DEFAULT
        
        # Guardar
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        log.info("[HABIT_MONITOR] Reglas guardadas en configuración")
        return True
        
    except Exception as e:
        log.warning("[HABIT_MONITOR] Error guardando reglas: %s", e)
        return False


def _hay_actividad_reciente(minutos: int = 15) -> bool:
    """Verifica si hubo actividad en los últimos N minutos."""
    try:
        from jarvis_core.memory.episodic_memory import hay_actividad_en_ventana
        return hay_actividad_en_ventana(minutos)
    except Exception as e:
        log.warning("[HABIT_MONITOR] Error verificando actividad: %s", e)
        return False


def _ultimo_evento_habito(tipo_evento: str) -> Optional[datetime]:
    """Obtiene la fecha del último evento de un tipo de hábito."""
    try:
        from jarvis_core.memory.episodic_memory import obtener_actividad_reciente
        
        # Obtener eventos recientes (últimas 24 horas para estar seguros)
        eventos = obtener_actividad_reciente(1440)
        
        for evento in eventos:
            if evento.get('tipo') == tipo_evento:
                timestamp_str = evento.get('timestamp', '')
                try:
                    return datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
                except ValueError:
                    continue
        
        return None
        
    except Exception as e:
        log.warning("[HABIT_MONITOR] Error obteniendo último evento: %s", e)
        return None


def _debe_disparar_habito(regla: Dict) -> bool:
    """
    Verifica si una regla de hábito debe dispararse.
    
    Args:
        regla: Diccionario con la definición de la regla
    
    Returns:
        bool: True si debe dispararse
    """
    nombre = regla.get('nombre', '')
    
    # Verificar si está activa
    if not regla.get('activo', True):
        return False
    
    # Verificar frecuencia mínima desde último disparo
    if nombre in _ultimos_disparos:
        ultimo_disparo = _ultimos_disparos[nombre]
        frecuencia_min = regla.get('frecuencia_minima', 60)
        
        if datetime.now() - ultimo_disparo < timedelta(minutes=frecuencia_min):
            return False
    
    # Verificar según el tipo de regla
    tipo_evento = regla.get('tipo_evento', '')
    intervalo_min = regla.get('intervalo_min')
    
    # Regla especial: noche (basada en hora)
    if nombre == 'noche':
        hora_actual = datetime.now().hour
        hora_limite = regla.get('hora_limite', 23)
        
        if hora_actual >= hora_limite:
            # Verificar si hubo actividad reciente
            if _hay_actividad_reciente(30):
                return True
        return False
    
    # Reglas basadas en intervalo de tiempo
    if intervalo_min:
        # Verificar si hubo actividad reciente (para saber si el usuario está activo)
        if not _hay_actividad_reciente(15):
            return False
        
        # Verificar último evento de este hábito
        ultimo_evento = _ultimo_evento_habito(tipo_evento)
        
        if ultimo_evento is None:
            # Nunca se ha registrado este hábito, verificar si hay actividad general
            if _hay_actividad_reciente(intervalo_min):
                return True
        else:
            # Verificar si pasó el intervalo
            if datetime.now() - ultimo_evento >= timedelta(minutes=intervalo_min):
                return True
    
    return False


def verificar_habitos() -> List[str]:
    """
    Verifica todos los hábitos y retorna mensajes pendientes.
    
    Returns:
        list[str]: Lista de mensajes de hábitos que deben dispararse
    """
    mensajes = []
    reglas = _cargar_reglas()
    
    for regla in reglas:
        if _debe_disparar_habito(regla):
            mensaje = regla.get('mensaje', '')
            if mensaje:
                mensajes.append(mensaje)
    
    return mensajes


def registrar_habito(tipo: str) -> bool:
    """
    Registra un hábito completado en la memoria episódica.
    
    Args:
        tipo: Tipo de hábito ('agua', 'descanso', 'pausa')
    
    Returns:
        bool: True si se registró correctamente
    """
    try:
        from jarvis_core.memory.episodic_memory import registrar
        
        tipo_evento = f'habito_{tipo}'
        descripcion = f'Usuario confirmó hábito: {tipo}'
        
        exito = registrar(tipo_evento, descripcion)
        
        if exito:
            # Actualizar último disparo
            _ultimos_disparos[tipo_evento] = datetime.now()
            log.info("[HABIT_MONITOR] Hábito registrado: %s", tipo)
        
        return exito
        
    except Exception as e:
        log.warning("[HABIT_MONITOR] Error registrando hábito: %s", e)
        return False


def agregar_regla(nombre: str, descripcion: str, intervalo_min: int, 
                  mensaje: str = '', tipo_evento: str = '') -> str:
    """
    Agrega una nueva regla de hábito.
    
    Args:
        nombre: Nombre identificador de la regla
        descripcion: Descripción de la regla
        intervalo_min: Intervalo en minutos
        mensaje: Mensaje de recordatorio
        tipo_evento: Tipo de evento para memoria episódica
    
    Returns:
        str: Confirmación
    """
    global _reglas_cargadas
    
    reglas = _cargar_reglas()
    
    # Verificar si ya existe
    for regla in reglas:
        if regla.get('nombre') == nombre:
            return f"Ya existe una regla llamada '{nombre}'"
    
    # Crear nueva regla
    nueva_regla = {
        'nombre': nombre,
        'descripcion': descripcion,
        'intervalo_min': intervalo_min,
        'mensaje': mensaje or f'Recordatorio: {descripcion}',
        'tipo_evento': tipo_evento or f'habito_{nombre}',
        'activo': True,
        'frecuencia_minima': intervalo_min
    }
    
    reglas.append(nueva_regla)
    _reglas_cargadas = reglas
    
    # Guardar en configuración
    if _guardar_reglas():
        return f"Regla '{nombre}' agregada correctamente"
    else:
        return "Regla agregada pero no se pudo guardar en configuración"


def listar_reglas() -> str:
    """
    Lista todas las reglas activas.
    
    Returns:
        str: Lista formateada de reglas
    """
    reglas = _cargar_reglas()
    
    lineas = []
    for regla in reglas:
        estado = "✓" if regla.get('activo', True) else "✗"
        nombre = regla.get('nombre', 'desconocido')
        descripcion = regla.get('descripcion', '')
        intervalo = regla.get('intervalo_min', 'N/A')
        
        if intervalo:
            lineas.append(f"{estado} {nombre}: {descripcion} (cada {intervalo} min)")
        else:
            lineas.append(f"{estado} {nombre}: {descripcion}")
    
    if lineas:
        return "Reglas de hábitos:\n" + "\n".join(lineas)
    else:
        return "No hay reglas configuradas"


def pausar_regla(nombre: str) -> str:
    """
    Pausa una regla de hábito.
    
    Args:
        nombre: Nombre de la regla
    
    Returns:
        str: Confirmación
    """
    reglas = _cargar_reglas()
    
    for regla in reglas:
        if regla.get('nombre') == nombre:
            regla['activo'] = False
            
            global _reglas_cargadas
            _reglas_cargadas = reglas
            
            if _guardar_reglas():
                return f"Regla '{nombre}' pausada"
            else:
                return f"Regla '{nombre}' pausada (temporalmente)"
    
    return f"No se encontró la regla '{nombre}'"


def activar_regla(nombre: str) -> str:
    """
    Activa una regla de hábito pausada.
    
    Args:
        nombre: Nombre de la regla
    
    Returns:
        str: Confirmación
    """
    reglas = _cargar_reglas()
    
    for regla in reglas:
        if regla.get('nombre') == nombre:
            regla['activo'] = True
            
            global _reglas_cargadas
            _reglas_cargadas = reglas
            
            if _guardar_reglas():
                return f"Regla '{nombre}' activada"
            else:
                return f"Regla '{nombre}' activada (temporalmente)"
    
    return f"No se encontró la regla '{nombre}'"


def get_estado() -> Dict[str, Any]:
    """Retorna el estado actual del monitor de hábitos."""
    reglas = _cargar_reglas()
    activos = sum(1 for r in reglas if r.get('activo', True))
    
    return {
        'total_reglas': len(reglas),
        'reglas_activas': activos,
        'ultimos_disparos': {k: v.isoformat() for k, v in _ultimos_disparos.items()}
    }
