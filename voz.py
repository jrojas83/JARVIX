# voz.py — Jarvis v8
# Sistema de voz mejorado con soporte para múltiples motores TTS
# Reconocimiento de voz offline con faster-whisper (reemplaza SpeechRecognition + PyAudio)

# Lazy loading: faster_whisper solo se importa cuando se usa
_whisper_model = None

def _get_whisper_model(modelo="base"):
    """
    Carga el modelo Whisper bajo demanda (lazy loading).
    Modelos disponibles: tiny, base, small, medium, large-v2, large-v3
    - tiny/base: rápidos, menos precisos
    - small/medium: equilibrio velocidad/precisión
    - large: máxima precisión, más lento
    """
    global _whisper_model
    if _whisper_model is None:
        from faster_whisper import WhisperModel
        # Usar CPU por defecto para compatibilidad universal
        # Si tienes GPU NVIDIA, cambiar a "cuda" para mayor velocidad
        _whisper_model = WhisperModel(modelo, device="cpu", compute_type="int8")
    return _whisper_model

# Configuración de voz mejorada
CONFIGURACION_VOS = {
    "espeak": {
        "voz": "es+m3",
        "velocidad": 150,  # ligeramente más rápido para sonar más natural
        "volumen": 160,    # más alto para mejor claridad
        "pitch": 50,       # tono medio
    },
    "pyttsx3": {
        "rate": 160,       # velocidad optimizada
        "volume": 0.9,     # volumen alto pero no máximo
    }
}

# Frases de transición para hacer la conversación más natural
FRASES_TRANSICION = [
    "¡Claro!", 
    "Entendido", 
    "Perfecto", 
    "De acuerdo",
    "Vale",
    "Ahí vamos",
]

def escuchar(timeout=None):
    """
    Escucha el micrófono y devuelve texto en minúsculas.
    Usa faster-whisper para reconocimiento offline de alta precisión.
    Devuelve cadena vacía si no escucha nada o hay error.
    """
    import subprocess
    import tempfile
    import os
    from config import IDIOMA_VOZ, TIMEOUT_ESCUCHA
    
    model = _get_whisper_model("base")
    
    if timeout is None:
        timeout = TIMEOUT_ESCUCHA

    # Grabar audio con sox (más eficiente que PyAudio)
    try:
        print("🎤 Escuchando...")
        
        # Crear archivo temporal para guardar el audio
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            temp_audio = f.name
        
        # Grabar audio del micrófono usando sox
        # -d: dispositivo default, -c 1: mono, -r 16000: sample rate para Whisper
        grabacion = subprocess.run(
            ["rec", "-c", "1", "-r", "16000", temp_audio],
            input=b"",
            capture_output=True,
            timeout=timeout
        )
        
        # Transcribir con Whisper
        segments, info = model.transcribe(temp_audio, language="es")
        texto = " ".join([segment.text for segment in segments]).strip()
        
        # Limpiar archivo temporal
        os.unlink(temp_audio)
        
        if texto:
            print(f"   Dijiste: {texto}")
            return texto.lower()
        else:
            return ""
            
    except subprocess.TimeoutExpired:
        # Limpiar archivo temporal si existe
        if 'temp_audio' in locals() and os.path.exists(temp_audio):
            os.unlink(temp_audio)
        return ""
    except Exception as e:
        # Limpiar archivo temporal si existe
        if 'temp_audio' in locals() and os.path.exists(temp_audio):
            os.unlink(temp_audio)
        print(f"   Error de voz: {e}")
        return ""


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
