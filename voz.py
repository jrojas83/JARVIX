# voz.py — Jarvis v2
import speech_recognition as sr
import subprocess
import sys
from config import IDIOMA_VOZ, PALABRA_ACTIVACION, TIMEOUT_ESCUCHA

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


def hablar(texto):
    """
    Convierte texto a voz. Intenta espeak primero, luego pyttsx3 si falla.
    """
    print(f"🔊 Jarvis: {texto}")
    try:
        subprocess.run(
            ["espeak", "-v", "es+m3", "-s", "140", "-a", "150", texto],
            capture_output=True,
            timeout=10
        )
    except FileNotFoundError:
        # Fallback a pyttsx3
        try:
            import pyttsx3
            engine = pyttsx3.init()
            engine.setProperty("rate", 150)
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
