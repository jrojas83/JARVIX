# jarvis_core/dictation.py — Dictado continuo de voz a texto
# ================================================================================
# Permite al usuario hablar y JARVIX escribe el texto transcrito directamente
# en el campo activo de cualquier aplicación (editor, terminal, navegador, etc.)
#
# Características:
#   - Grabación continua con detección de silencio
#   - Transcripción con faster-whisper (comparte modelo con voz.py)
#   - Comando de voz para detener el dictado
#   - Uso de xdotool para escribir el texto transcrito

import subprocess
import threading
import time
from typing import Optional

from logger import log


# Variables globales de estado
_dictado_activo: bool = False
_hilo_dictado: Optional[threading.Thread] = None


def _get_whisper_model():
    """
    Obtiene el modelo Whisper global cargado desde voz.py.
    Evita cargar dos instancias del modelo.
    """
    try:
        from voz import get_modelo_whisper
        return get_modelo_whisper()
    except ImportError:
        # Fallback si no existe la función en voz.py
        pass
    
    # Intentar cargar directamente si no hay función shared
    try:
        from faster_whisper import WhisperModel
        model = WhisperModel("tiny", device="cpu", compute_type="int8")
        return model
    except Exception as e:
        log.warning("[DICTATION] Error cargando modelo Whisper: %s", e)
        return None


def _grabar_audio(timeout_seg: int = 3) -> Optional[str]:
    """
    Graba audio usando sox con detección de silencio.
    
    Args:
        timeout_seg: Segundos de silencio para cortar la grabación
    
    Returns:
        Ruta del archivo WAV grabado o None si falla
    """
    import tempfile
    
    try:
        # Crear archivo temporal
        fd, ruta = tempfile.mkstemp(suffix='.wav')
        
        # Comando sox con detección de silencio
        # silence: 1 = detectar inicio, 1% umbral inicio, 0.5s duración inicio
        #          1 = detectar fin, 1% umbral fin, timeout_seg duración fin
        cmd = [
            'sox', '-d',  # Desde micrófono default
            '-r', '16000',  # 16kHz sample rate
            '-c', '1',  # Mono
            '-b', '16',  # 16 bits
            ruta,
            'silence', '1', '0.5', '1%', '1', f'{timeout_seg}', '1%'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_seg + 5)
        
        if result.returncode == 0 and os.path.exists(ruta):
            return ruta
        else:
            log.warning("[DICTATION] sox falló: %s", result.stderr)
            return None
            
    except subprocess.TimeoutExpired:
        # Timeout es esperado cuando hay silencio prolongado
        return None
    except FileNotFoundError:
        log.warning("[DICTATION] sox no encontrado. Intentando alternativa.")
        return _grabar_audio_alternativo(timeout_seg)
    except Exception as e:
        log.warning("[DICTATION] Error grabando audio: %s", e)
        return None


def _grabar_audio_alternativo(timeout_seg: int = 3) -> Optional[str]:
    """
    Alternativa de grabación si sox no está disponible.
    Usa grabación por tiempo fijo.
    """
    import tempfile
    
    try:
        fd, ruta = tempfile.mkstemp(suffix='.wav')
        
        # Grabación simple por tiempo fijo (5 segundos máx)
        cmd = [
            'sox', '-d',
            '-r', '16000',
            '-c', '1',
            '-b', '16',
            ruta,
            'trim', '0', '5'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=8)
        
        if result.returncode == 0 and os.path.exists(ruta):
            return ruta
        return None
        
    except Exception as e:
        log.warning("[DICTATION] Error en grabación alternativa: %s", e)
        return None


def _transcribir_audio(ruta_wav: str) -> Optional[str]:
    """
    Transcribe un archivo de audio usando Whisper.
    
    Args:
        ruta_wav: Ruta al archivo WAV
    
    Returns:
        Texto transcrito o None
    """
    model = _get_whisper_model()
    
    if model is None:
        return None
    
    try:
        # Transcribir con lenguaje español
        segments, info = model.transcribe(
            ruta_wav,
            language="es",
            beam_size=5,
            vad_filter=True  # Usar VAD integrado de whisper
        )
        
        texto = " ".join([segment.text for segment in segments]).strip()
        return texto if texto else None
        
    except Exception as e:
        log.warning("[DICTATION] Error transcribiendo: %s", e)
        return None


def _escribir_texto(texto: str) -> bool:
    """
    Escribe el texto en la aplicación activa usando xdotool.
    
    Args:
        texto: Texto a escribir
    
    Returns:
        True si se escribió correctamente
    """
    if not texto:
        return False
    
    # Agregar espacio al final para separar de la siguiente frase
    texto_con_espacio = texto + " "
    
    try:
        # Usar xdotool para escribir el texto
        # --clearmodifiers evita interferencia con teclas modificadoras
        # --delay 0 hace que sea instantáneo
        result = subprocess.run(
            ['xdotool', 'type', '--clearmodifiers', '--delay', '0', texto_con_espacio],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0:
            log.info("[DICTATION] Texto escrito: %s", texto[:50])
            
            # Registrar en memoria episódica
            try:
                from jarvis_core.memory.episodic_memory import registrar
                registrar('dictado', descripcion=texto[:100])
            except Exception:
                pass
            
            return True
        else:
            log.warning("[DICTATION] xdotool falló: %s", result.stderr)
            return False
            
    except FileNotFoundError:
        log.warning("[DICTATION] xdotool no encontrado")
        return False
    except subprocess.TimeoutExpired:
        log.warning("[DICTATION] Timeout escribiendo texto")
        return False
    except Exception as e:
        log.warning("[DICTATION] Error escribiendo texto: %s", e)
        return False


def _contiene_comando_detener(texto: str) -> bool:
    """Verifica si el texto contiene comandos para detener el dictado."""
    if not texto:
        return False
    
    texto_lower = texto.lower()
    comandos = [
        'detener dictado',
        'parar dictado',
        'fin de dictado',
        'terminar dictado',
        'cierra dictado',
        'basta de dictado'
    ]
    
    return any(comando in texto_lower for comando in comandos)


def _bucle_dictado() -> None:
    """Bucle principal del dictado continuo."""
    global _dictado_activo
    
    log.info("[DICTATION] Bucle de dictado iniciado")
    
    while _dictado_activo:
        try:
            # 1. Grabar audio
            ruta_audio = _grabar_audio(timeout_seg=3)
            
            if ruta_audio is None:
                # No se capturó audio válido, continuar esperando
                time.sleep(0.5)
                continue
            
            # 2. Transcribir
            texto = _transcribir_audio(ruta_audio)
            
            # Limpiar archivo temporal
            try:
                import os
                os.unlink(ruta_audio)
            except Exception:
                pass
            
            if texto is None or texto.strip() == "":
                # No hubo transcripción válida
                time.sleep(0.5)
                continue
            
            # 3. Verificar comando de detener
            if _contiene_comando_detener(texto):
                log.info("[DICTATION] Comando de detener detectado: %s", texto)
                detener_dictado()
                break
            
            # 4. Escribir texto
            _escribir_texto(texto)
            
        except Exception as e:
            log.error("[DICTATION] Error en bucle: %s", e)
            time.sleep(1)
    
    log.info("[DICTATION] Bucle de dictado terminado")


def iniciar_dictado() -> str:
    """
    Inicia el modo dictado continuo.
    
    Returns:
        str: Confirmación
    """
    global _dictado_activo, _hilo_dictado
    
    if _dictado_activo:
        return "El dictado ya está activo"
    
    _dictado_activo = True
    
    # Anunciar por voz
    try:
        from voz import hablar
        hablar("Dictado activo, habla")
    except Exception as e:
        log.warning("[DICTATION] Error anunciando inicio: %s", e)
    
    # Iniciar hilo de dictado
    _hilo_dictado = threading.Thread(target=_bucle_dictado, daemon=True)
    _hilo_dictado.start()
    
    log.info("[DICTATION] Dictado iniciado")
    return "Dictado iniciado"


def detener_dictado() -> str:
    """
    Detiene el modo dictado continuo.
    
    Returns:
        str: Confirmación
    """
    global _dictado_activo
    
    if not _dictado_activo:
        return "El dictado no está activo"
    
    _dictado_activo = False
    
    # Esperar a que el hilo termine (con timeout)
    if _hilo_dictado and _hilo_dictado.is_alive():
        _hilo_dictado.join(timeout=2)
    
    # Anunciar por voz
    try:
        from voz import hablar
        hablar("Dictado detenido")
    except Exception as e:
        log.warning("[DICTATION] Error anunciando detención: %s", e)
    
    log.info("[DICTATION] Dictado detenido")
    return "Dictado detenido"


def estado_dictado() -> str:
    """
    Retorna el estado actual del dictado.
    
    Returns:
        str: Estado del dictado
    """
    if _dictado_activo:
        return "Dictado ACTIVO"
    else:
        return "Dictado INACTIVO"


def get_estado() -> bool:
    """Retorna si el dictado está activo."""
    return _dictado_activo
