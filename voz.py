# voz.py — Jarvis v8
# Sistema de voz mejorado con soporte para múltiples motores TTS
import speech_recognition as sr
import subprocess
import sys
import random
from config import IDIOMA_VOZ, PALABRA_ACTIVACION, TIMEOUT_ESCUCHA

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
    Devuelve cadena vacía si no escucha nada o hay error.
    """
    if timeout is None:
        timeout = TIMEOUT_ESCUCHA

    r = sr.Recognizer()
    r.pause_threshold = 1.0
    r.energy_threshold = 300

    try:
        with sr.Microphone() as source:
            print("🎤 Escuchando...")
            r.adjust_for_ambient_noise(source, duration=0.5)
            audio = r.listen(source, timeout=timeout, phrase_time_limit=12)

        texto = r.recognize_google(audio, language=IDIOMA_VOZ)
        print(f"   Dijiste: {texto}")
        return texto.lower()

    except sr.WaitTimeoutError:
        return ""
    except sr.UnknownValueError:
        return ""
    except sr.RequestError as e:
        print(f"   Error de reconocimiento: {e}")
        return ""
    except Exception as e:
        print(f"   Error de voz: {e}")
        return ""


def escuchar_con_activacion():
    """
    Modo espera robusto: escucha indefinidamente hasta detectar la palabra de
    activación. Si el micrófono falla, reintenta con backoff exponencial.
    Jamás cae silenciosamente: siempre muestra qué está pasando.
    """
    import time

    r = sr.Recognizer()
    r.pause_threshold = 0.8
    r.energy_threshold = 300

    intentos_error = 0
    MAX_BACKOFF    = 30   # segundos máximos de espera entre reintentos

    print(f"⏳ En espera... (di '{PALABRA_ACTIVACION}' para activar)")

    while True:
        try:
            with sr.Microphone() as source:
                intentos_error = 0  # Micrófono accesible → resetear backoff
                r.adjust_for_ambient_noise(source, duration=0.3)
                audio = r.listen(source, timeout=3, phrase_time_limit=5)

            texto = r.recognize_google(audio, language=IDIOMA_VOZ).lower()

            if PALABRA_ACTIVACION in texto:
                print(f"✅ Activado por '{PALABRA_ACTIVACION}'")
                hablar("Dime")
                with sr.Microphone() as source:
                    r.adjust_for_ambient_noise(source, duration=0.3)
                    print("🎤 Escuchando orden...")
                    audio = r.listen(source, timeout=TIMEOUT_ESCUCHA, phrase_time_limit=12)
                orden = r.recognize_google(audio, language=IDIOMA_VOZ).lower()
                print(f"   Dijiste: {orden}")
                return orden

        except (sr.WaitTimeoutError, sr.UnknownValueError):
            # Normal — silencio o audio no reconocido
            continue

        except sr.RequestError as e:
            # Error de red con la API de reconocimiento
            intentos_error += 1
            espera = min(2 ** intentos_error, MAX_BACKOFF)
            print(f"   ⚠️  Error reconocimiento de voz (intento {intentos_error}): {e}")
            print(f"   Reintentando en {espera}s...")
            time.sleep(espera)
            continue

        except OSError as e:
            # Micrófono desconectado o no disponible
            intentos_error += 1
            espera = min(2 ** intentos_error, MAX_BACKOFF)
            print(f"   ⚠️  Micrófono no disponible (intento {intentos_error}): {e}")
            print(f"   Reintentando en {espera}s... (reconecta el micro si es necesario)")
            time.sleep(espera)
            # Reinicializar recognizer por si el dispositivo cambió
            r = sr.Recognizer()
            r.pause_threshold = 0.8
            r.energy_threshold = 300
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
