# voz.py — Jarvis v8
# Sistema de voz offline con faster-whisper
# Grabación con sox + detección de silencio, VAD con webrtcvad

import subprocess
import tempfile
import os
import time
from config import IDIOMA_VOZ, TIMEOUT_ESCUCHA, PALABRA_ACTIVACION

# Lazy loading estricto: el modelo Whisper se carga solo la primera vez
_whisper_model = None

def _get_whisper_model(modelo="tiny"):
    """
    Carga el modelo Whisper bajo demanda (lazy loading).
    Modelo por defecto: tiny para español (rápido, ~75MB)
    Si hay más de 4GB RAM libre, permite usar 'base' como alternativa.
    """
    global _whisper_model
    if _whisper_model is None:
        from faster_whisper import WhisperModel
        # Verificar RAM disponible para decidir modelo
        try:
            import psutil
            ram_libre_gb = psutil.virtual_memory().available / (1024**3)
            if ram_libre_gb > 4 and modelo == "tiny":
                modelo = "base"  # Usar base si hay RAM suficiente
        except ImportError:
            pass  # Si no hay psutil, usar el modelo especificado
        
        _whisper_model = WhisperModel(modelo, device="cpu", compute_type="int8")
    return _whisper_model


def _vad_contiene_voz(audio_bytes, sample_rate=16000):
    """
    Usa webrtcvad para validar que el audio contiene voz real.
    Retorna True si detecta voz, False si es silencio o ruido.
    """
    try:
        import webrtcvad
        vad = webrtcvad.Vad(2)  # Agresividad media (0-3)
        
        # WebRTC VAD requiere frames de 10, 20 o 30 ms
        # A 16kHz: 10ms = 160 samples, 20ms = 320 samples, 30ms = 480 samples
        frame_duration = 30  # ms
        frame_size = int(sample_rate * frame_duration / 1000)
        
        # Dividir audio en frames
        frames = []
        for i in range(0, len(audio_bytes) - (frame_size * 2), frame_size * 2):
            frame = audio_bytes[i:i + frame_size * 2]
            if len(frame) == frame_size * 2:
                frames.append(frame)
        
        if not frames:
            return False
        
        # Contar frames con voz
        voces = sum(1 for f in frames if vad.is_voice(f, sample_rate))
        ratio_voz = voces / len(frames)
        
        # Considerar voz si más del 30% de frames tienen voz
        return ratio_voz > 0.3
    except Exception as e:
        # Si falla VAD, asumir que hay voz para no perder comandos
        return True


def _grabar_con_sox(timeout_segundos):
    """
    Graba audio usando sox con detección de silencio.
    Solo captura cuando hay audio real, descarta silencio.
    Retorna ruta del archivo WAV grabado o None si falla.
    """
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        temp_audio = f.name
    
    try:
        # Comando sox con detección de silencio:
        # -c 1: mono
        # -r 16000: sample rate para Whisper
        # silence: efecto que detecta silencio
        # 1 0.5% 0.5: parar después de 0.5s de silencio por debajo de 0.5%
        # reverse : reverse para detectar silencio al inicio también
        # 1 0.5% 0.5: igual al principio
        # reverse: volver a normal
        cmd = [
            "rec",
            "-c", "1",
            "-r", "16000",
            temp_audio,
            "silence",
            "1", "0.5", "0.5%",  # Iniciar grabación cuando hay audio
            "1", "2.0", "0.5%",  # Parar después de 2s de silencio
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            timeout=timeout_segundos
        )
        
        # Verificar que se grabó algo
        if os.path.getsize(temp_audio) < 1024:  # Menos de 1KB = demasiado corto
            os.unlink(temp_audio)
            return None
        
        return temp_audio
    except subprocess.TimeoutExpired:
        # Timeout - limpiar y retornar None
        if os.path.exists(temp_audio):
            os.unlink(temp_audio)
        return None
    except Exception as e:
        if os.path.exists(temp_audio):
            os.unlink(temp_audio)
        raise e


def escuchar(timeout=None):
    """
    Escucha el micrófono y devuelve texto transcrito en español.
    Usa faster-whisper para reconocimiento offline.
    Implementa VAD para validar voz real antes de transcribir.
    Backoff exponencial para reconexión del micrófono.
    
    Retorna:
        str: texto transcrito o None si no hubo voz detectada
    """
    if timeout is None:
        timeout = TIMEOUT_ESCUCHA
    
    model = _get_whisper_model("tiny")
    
    # Backoff exponencial parameters
    intentos = 0
    max_intentos = 5
    max_backoff = 30
    
    while intentos < max_intentos:
        try:
            print("🎤 Escuchando...")
            
            # Grabar audio con detección de silencio
            temp_audio = _grabar_con_sox(timeout)
            
            if temp_audio is None:
                # No se grabó audio válido
                return None
            
            # Leer audio para VAD
            with open(temp_audio, "rb") as f:
                audio_bytes = f.read()
            
            # Validar con VAD antes de transcribir
            if not _vad_contiene_voz(audio_bytes):
                os.unlink(temp_audio)
                print("   (Solo ruido/silencio detectado, ignorando)")
                return None
            
            # Transcribir con Whisper
            segments, info = model.transcribe(temp_audio, language="es")
            texto = " ".join([segment.text for segment in segments]).strip()
            
            # Limpiar archivo temporal
            os.unlink(temp_audio)
            
            if texto:
                print(f"   Dijiste: {texto}")
                return texto.lower()
            else:
                return None
                
        except OSError as e:
            # Error de micrófono - aplicar backoff
            intentos += 1
            if intentos >= max_intentos:
                print(f"   ⚠️  Micrófono no disponible después de {intentos} intentos")
                return None
            
            espera = min(2 ** intentos, max_backoff)
            print(f"   ⚠️  Error de micrófono (intento {intentos}/{max_intentos}): {e}")
            print(f"   Reintentando en {espera}s...")
            time.sleep(espera)
            
        except subprocess.TimeoutExpired:
            # Timeout normal - no hay voz
            return None
            
        except Exception as e:
            intentos += 1
            if intentos >= max_intentos:
                print(f"   ⚠️  Error inesperado después de {intentos} intentos: {e}")
                return None
            
            espera = min(2 ** intentos, max_backoff)
            print(f"   ⚠️  Error (intento {intentos}): {e}")
            time.sleep(espera)
    
    return None


def detectar_palabra_activacion(palabra_activacion, model):
    """
    Detecta si una grabación contiene la palabra de activación.
    Usa Whisper para transcripción offline.
    """
    import tempfile
    import subprocess
    import os
    
    try:
        # Crear archivo temporal
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            temp_audio = f.name
        
        # Grabar audio corto (3 segundos)
        subprocess.run(
            ["rec", "-c", "1", "-r", "16000", temp_audio],
            input=b"",
            capture_output=True,
            timeout=3
        )
        
        # Transcribir
        segments, info = model.transcribe(temp_audio, language="es")
        texto = " ".join([segment.text for segment in segments]).strip().lower()
        
        # Limpiar
        os.unlink(temp_audio)
        
        return palabra_activacion in texto, texto
        
    except Exception:
        if 'temp_audio' in locals() and os.path.exists(temp_audio):
            os.unlink(temp_audio)
        return False, ""


def escuchar_con_activacion():
    """
    Modo espera robusto: escucha indefinidamente hasta detectar la palabra de
    activación usando Whisper offline. Si el micrófono falla, reintenta con 
    backoff exponencial. Jamás cae silenciosamente: siempre muestra qué está pasando.
    """
    import time
    from config import PALABRA_ACTIVACION
    
    model = _get_whisper_model("tiny")  # tiny es más rápido para detección continua

    intentos_error = 0
    MAX_BACKOFF    = 30   # segundos máximos de espera entre reintentos

    print(f"⏳ En espera... (di '{PALABRA_ACTIVACION}' para activar)")

    while True:
        try:
            # Detectar palabra de activación
            detectado, texto = detectar_palabra_activacion(PALABRA_ACTIVACION, model)

            if detectado:
                print(f"✅ Activado por '{PALABRA_ACTIVACION}'")
                hablar("Dime")
                
                # Escuchar orden completa
                orden = escuchar(timeout=TIMEOUT_ESCUCHA)
                if orden:
                    print(f"   Dijiste: {orden}")
                    return orden

        except subprocess.TimeoutExpired:
            # Normal — timeout de grabación
            continue

        except OSError as e:
            # Micrófono desconectado o no disponible
            intentos_error += 1
            espera = min(2 ** intentos_error, MAX_BACKOFF)
            print(f"   ⚠️  Micrófono no disponible (intento {intentos_error}): {e}")
            print(f"   Reintentando en {espera}s... (reconecta el micro si es necesario)")
            time.sleep(espera)
            continue

        except KeyboardInterrupt:
            raise

        except Exception as e:
            intentos_error += 1
            espera = min(2 ** intentos_error, MAX_BACKOFF)
            print(f"   ⚠️  Error inesperado en modo espera (intento {intentos_error}): {e}")
            time.sleep(espera)
            continue


def hablar(texto, usar_frase_transicion=False):
    """
    Convierte texto a voz con configuración mejorada.
    Intenta espeak primero (más rápido), luego pyttsx3 si falla.
    
    Parámetros:
    - texto: el texto a convertir a voz
    - usar_frase_transicion: si True, añade una frase de transición aleatoria antes del texto
    """
    import random
    
    # Opcionalmente añadir frase de transición para sonar más natural
    if usar_frase_transicion and FRASES_TRANSICION:
        frase = random.choice(FRASES_TRANSICION)
        texto = f"{frase}. {texto}"
    
    print(f"🔊 Jarvis: {texto}")
    
    cfg = CONFIGURACION_VOS["espeak"]
    try:
        subprocess.run(
            ["espeak", "-v", cfg["voz"], "-s", str(cfg["velocidad"]), 
             "-a", str(cfg["volumen"]), "--pitch=", str(cfg["pitch"]), texto],
            capture_output=True,
            timeout=10
        )
    except FileNotFoundError:
        # Fallback a pyttsx3
        try:
            import pyttsx3
            engine = pyttsx3.init()
            cfg_py = CONFIGURACION_VOS["pyttsx3"]
            engine.setProperty("rate", cfg_py["rate"])
            engine.setProperty("volume", cfg_py["volume"])
            voices = engine.getProperty("voices")
            # Buscar voz en español
            for v in voices:
                if "es" in v.id.lower() or "spanish" in v.name.lower():
                    engine.setProperty("voice", v.id)
                    break
            engine.say(texto)
            engine.runAndWait()
        except Exception as e:
            print(f"   (Sin audio: {e})")
    except subprocess.TimeoutExpired:
        print("   (TTS tardó demasiado, continuando...)")
    except Exception as e:
        print(f"   Error TTS: {e}")


def hablar_con_emocion(texto, emocion="neutral"):
    """
    Versión mejorada de hablar que ajusta parámetros según la emoción.
    
    Emociones soportadas:
    - neutral: configuración normal
    - alegre: más rápido y tono más alto
    - serio: más lento y tono más bajo
    - urgente: muy rápido y volumen alto
    """
    emociones = {
        "neutral": {"rate": 150, "pitch": 50, "volume": 160},
        "alegre": {"rate": 170, "pitch": 60, "volume": 170},
        "serio": {"rate": 130, "pitch": 40, "volume": 150},
        "urgente": {"rate": 180, "pitch": 55, "volume": 200},
    }
    
    cfg = emociones.get(emocion, emociones["neutral"])
    print(f"🔊 Jarvis [{emocion}]: {texto}")
    
    try:
        subprocess.run(
            ["espeak", "-v", CONFIGURACION_VOS["espeak"]["voz"], 
             "-s", str(cfg["rate"]), "-a", str(cfg["volume"]), 
             f"--pitch={cfg['pitch']}", texto],
            capture_output=True,
            timeout=10
        )
    except Exception as e:
        # Fallback simplificado
        hablar(texto)
