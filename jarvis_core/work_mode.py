# jarvis_core/work_mode.py — Detector de modo trabajo automático
# ================================================================================
# Detecta el contexto del usuario y activa automáticamente el entorno de trabajo:
#   - Abre VS Code, terminales y las IAs en el navegador
#   - Puntuación basada en señales detectables (ventana activa, procesos, git, hora, CPU)
#   - Hilo de detección automática cada 2 minutos
#   - Configuración del umbral en ~/.jarvis_config.json

import os
import subprocess
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from logger import log

try:
    import psutil
except ImportError:
    psutil = None

try:
    import requests
except ImportError:
    requests = None


# Variables globales de estado
_modo_activo: bool = False
_hilo_detector: Optional[threading.Thread] = None
_umbral_defecto: int = 2


def _get_xdotool_window_title() -> str:
    """Obtiene el título de la ventana activa usando xdotool."""
    try:
        result = subprocess.run(
            ['xdotool', 'getactivewindow', 'getwindowname'],
            capture_output=True,
            text=True,
            timeout=2
        )
        if result.returncode == 0:
            return result.stdout.strip().lower()
    except Exception:
        pass
    return ""


def _get_process_signals() -> tuple[int, List[str]]:
    """
    Verifica procesos activos relacionados con desarrollo.
    Retorna (puntos, lista de señales encontradas).
    """
    if psutil is None:
        return 0, []
    
    target_processes = ['python', 'node', 'npm', 'git', 'gcc', 'make', 'docker']
    puntos = 0
    señales = []
    
    try:
        for proc in psutil.process_iter(['name', 'cmdline']):
            try:
                name = proc.info['name'] or ''
                cmdline = ' '.join(proc.info['cmdline'] or [])
                
                for target in target_processes:
                    if target in name.lower() or target in cmdline.lower():
                        if target not in [s.split(':')[0] for s in señales]:
                            señales.append(f"{target}:proceso")
                            puntos += 1
                            if puntos >= 2:
                                return puntos, señales
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
    except Exception as e:
        log.warning("[WORK_MODE] Error listando procesos: %s", e)
    
    return min(puntos, 2), señales


def _check_git_in_path() -> tuple[int, str]:
    """
    Verifica si hay un repositorio git en el directorio actual o sus padres.
    Retorna (puntos, señal).
    """
    try:
        # Obtener directorio desde la ventana activa o usar home
        current = Path.cwd()
        
        # Buscar hasta 3 niveles hacia arriba
        for _ in range(3):
            if (current / '.git').exists():
                return 2, "git:repo"
            parent = current.parent
            if parent == current:
                break
            current = parent
    except Exception:
        pass
    
    return 0, ""


def _check_time_window() -> tuple[int, str]:
    """
    Verifica si la hora actual está entre 8:00 y 22:00.
    Retorna (puntos, señal).
    """
    hour = datetime.now().hour
    if 8 <= hour < 22:
        return 1, "hora:laboral"
    return 0, ""


def _check_cpu_usage() -> tuple[int, str]:
    """
    Verifica si el CPU está por encima del 15%.
    Usa un historial circular de 5 lecturas.
    Retorna (puntos, señal).
    """
    if psutil is None:
        return 0, ""
    
    try:
        cpu = psutil.cpu_percent(interval=0.5)
        if cpu > 15:
            return 1, "cpu:activo"
    except Exception:
        pass
    
    return 0, ""


def evaluar_contexto() -> Dict:
    """
    Evalúa el contexto actual y retorna puntuación.
    
    Returns:
        dict: {'score': int, 'señales': list[str], 'modo_trabajo': bool}
    """
    global _umbral_defecto
    
    score = 0
    señales = []
    
    # 1. Ventana activa (2 puntos)
    window_title = _get_xdotool_window_title()
    dev_apps = ['code', 'vscode', 'vim', 'nvim', 'emacs', 'terminal', 'konsole', 
                'gnome-terminal', 'kitty', 'alacritty']
    for app in dev_apps:
        if app in window_title:
            señales.append(f"ventana:{app}")
            score += 2
            break
    
    # 2. Procesos activos (máx 2 puntos)
    pts_proc, sig_proc = _get_process_signals()
    score += pts_proc
    señales.extend(sig_proc)
    
    # 3. Repositorio git (2 puntos)
    pts_git, sig_git = _check_git_in_path()
    score += pts_git
    if sig_git:
        señales.append(sig_git)
    
    # 4. Hora laboral (1 punto)
    pts_time, sig_time = _check_time_window()
    score += pts_time
    if sig_time:
        señales.append(sig_time)
    
    # 5. Uso de CPU (1 punto)
    pts_cpu, sig_cpu = _check_cpu_usage()
    score += pts_cpu
    if sig_cpu:
        señales.append(sig_cpu)
    
    # Cargar umbral desde config si existe
    umbral = _umbral_defecto
    try:
        config_path = Path.home() / '.jarvis_config.json'
        if config_path.exists():
            import json
            with open(config_path, 'r') as f:
                config = json.load(f)
                umbral = config.get('work_mode_threshold', _umbral_defecto)
    except Exception:
        pass
    
    modo_trabajo = score >= umbral
    
    return {
        'score': score,
        'señales': señales,
        'modo_trabajo': modo_trabajo,
        'umbral': umbral
    }


def _abrir_vs_code(ruta: str = '.') -> bool:
    """Intenta abrir VS Code en la ruta especificada."""
    try:
        # Intentar con 'code .'
        result = subprocess.Popen(['code', ruta])
        time.sleep(1.5)
        return True
    except FileNotFoundError:
        try:
            # Intentar sin ruta
            result = subprocess.Popen(['code'])
            time.sleep(1.5)
            return True
        except FileNotFoundError:
            log.warning("[WORK_MODE] VS Code no encontrado")
            return False
    except Exception as e:
        log.warning("[WORK_MODE] Error abriendo VS Code: %s", e)
        return False


def _abrir_terminales(cantidad: int = 2) -> int:
    """Abre múltiples terminales. Retorna cuántas se abrieron."""
    terminals = ['gnome-terminal', 'xterm', 'kitty', 'xfce4-terminal', 'konsole']
    abiertas = 0
    
    for _ in range(cantidad):
        for term in terminals:
            try:
                subprocess.Popen([term])
                abiertas += 1
                time.sleep(0.5)
                break
            except FileNotFoundError:
                continue
            except Exception as e:
                log.warning("[WORK_MODE] Error abriendo terminal %s: %s", term, e)
                continue
    
    time.sleep(1)
    return abiertas


def _abrir_urls_ia(urls: List[str]) -> int:
    """Abre URLs de IAs en el navegador. Retorna cuántas se abrieron."""
    abiertas = 0
    
    for url in urls:
        try:
            subprocess.Popen(['xdg-open', url])
            abiertas += 1
            time.sleep(0.5)
        except Exception as e:
            log.warning("[WORK_MODE] Error abriendo URL %s: %s", url, e)
    
    return abiertas


def activar_modo_trabajo() -> str:
    """
    Activa el modo trabajo abriendo todas las herramientas necesarias.
    
    Returns:
        str: Confirmación de lo que se abrió
    """
    global _modo_activo
    
    if _modo_activo:
        return "El modo trabajo ya está activo"
    
    abierto = []
    
    # 1. Abrir VS Code
    if _abrir_vs_code():
        abierto.append("VS Code")
    
    # 2. Abrir terminales
    term_abiertas = _abrir_terminales(2)
    if term_abiertas > 0:
        abierto.append(f"{term_abiertas} terminal(es)")
    
    # 3. Abrir IAs en el navegador
    urls_ia = [
        'https://claude.ai',
        'https://chatgpt.com',
        'https://gemini.google.com'
    ]
    urls_abiertas = _abrir_urls_ia(urls_ia)
    if urls_abiertas > 0:
        abierto.append(f"{urls_abiertas} pestaña(s) de IA")
    
    # Marcar como activo
    _modo_activo = True
    
    # Registrar en memoria episódica
    try:
        from jarvis_core.memory.episodic_memory import registrar
        registrar('modo_activado', descripcion='modo trabajo', app='work_mode')
    except Exception as e:
        log.warning("[WORK_MODE] Error registrando evento: %s", e)
    
    if abierto:
        return f"Modo trabajo activado. Se abrió: {', '.join(abierto)}"
    else:
        return "Modo trabajo activado, pero no se pudo abrir ninguna aplicación"


def desactivar_modo_trabajo() -> str:
    """
    Desactiva el modo trabajo.
    
    Returns:
        str: Confirmación
    """
    global _modo_activo
    _modo_activo = False
    return "Modo trabajo desactivado"


def estado_modo() -> str:
    """
    Retorna el estado actual del modo trabajo.
    
    Returns:
        str: Estado del modo
    """
    contexto = evaluar_contexto()
    if _modo_activo:
        return f"Modo trabajo ACTIVO. Puntuación actual: {contexto['score']}, Umbral: {contexto['umbral']}"
    else:
        return f"Modo trabajo INACTIVO. Puntuación actual: {contexto['score']}, Umbral: {contexto['umbral']} (necesitas {contexto['umbral']} para activar)"


def _preguntar_al_usuario() -> bool:
    """
    Pregunta al usuario si desea activar el modo trabajo.
    Espera 15 segundos por respuesta.
    
    Returns:
        bool: True si el usuario confirmó
    """
    from voz import hablar, escuchar
    
    try:
        hablar("Detecté que vas a trabajar, ¿activo el modo trabajo?")
        
        # Escuchar con timeout implícito
        respuesta = escuchar()
        
        if respuesta:
            respuesta_lower = respuesta.lower()
            afirmaciones = ['sí', 'si', 'yes', 'claro', 'por supuesto', 'ok', 'vale', 'activa', 'activar']
            return any(afirm in respuesta_lower for afirm in afirmaciones)
    except Exception as e:
        log.warning("[WORK_MODE] Error preguntando al usuario: %s", e)
    
    return False


def _bucle_detector() -> None:
    """Hilo de detección automática que corre cada 2 minutos."""
    global _modo_activo
    
    while True:
        try:
            time.sleep(120)  # 2 minutos
            
            contexto = evaluar_contexto()
            
            if contexto['modo_trabajo'] and not _modo_activo:
                # Preguntar al usuario
                if _preguntar_al_usuario():
                    activar_modo_trabajo()
                    
        except Exception as e:
            log.warning("[WORK_MODE] Error en bucle detector: %s", e)


def iniciar_detector_automatico() -> None:
    """Inicia el hilo de detección automática."""
    global _hilo_detector
    
    if _hilo_detector and _hilo_detector.is_alive():
        log.info("[WORK_MODE] El detector ya está corriendo")
        return
    
    _hilo_detector = threading.Thread(target=_bucle_detector, daemon=True)
    _hilo_detector.start()
    log.info("[WORK_MODE] Detector automático iniciado")


def get_estado() -> bool:
    """Retorna si el modo trabajo está activo."""
    return _modo_activo
