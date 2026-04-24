# whatsapp.py — Jarvis v3
# Controla WhatsApp Web con Selenium para enviar mensajes y recordatorios.
#
# Instalación:
#   pip install selenium webdriver-manager
#
# La primera vez abrirá el navegador para que escanees el QR.
# Después guarda la sesión en ~/.jarvis_whatsapp_session/
# y ya no pide QR en los siguientes usos.

import os
import time
import threading
import json
from datetime import datetime

try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.firefox.options import Options as FirefoxOptions
    from selenium.webdriver.firefox.service import Service as FirefoxService
    from selenium.common.exceptions import (
        TimeoutException, NoSuchElementException, WebDriverException
    )
    SELENIUM_OK = True
except ImportError:
    SELENIUM_OK = False

HOME            = os.path.expanduser("~")
PERFIL_FIREFOX  = os.path.join(HOME, ".jarvis_whatsapp_session")
WA_URL          = "https://web.whatsapp.com"

# ── Instancia global del driver (singleton) ────────────────
_driver     = None
_driver_lock = threading.Lock()

# ─── Selectores XPath (WhatsApp Web) ──────────────────────
# WhatsApp cambia sus clases frecuentemente — usamos texto/aria que son más estables
XPATH_BUSQUEDA   = '//div[@contenteditable="true"][@data-tab="3"]'
XPATH_CONTACTO   = '//span[@title="{nombre}"]'
XPATH_INPUT_MSG  = '//div[@contenteditable="true"][@data-tab="10"]'
XPATH_QR         = '//canvas[@aria-label="Scan me!"]'
XPATH_LISTO      = '//div[@data-tab="3"]'   # barra de búsqueda = sesión abierta


# ─── Gestión del driver ────────────────────────────────────

def _crear_driver():
    """Crea una instancia de Firefox con perfil persistente (guarda sesión WA)."""
    opts = FirefoxOptions()
    # Perfil persistente → guarda cookies/sesión de WhatsApp
    opts.add_argument("-profile")
    opts.add_argument(PERFIL_FIREFOX)
    # NO headless: WhatsApp Web bloquea Firefox headless
    os.makedirs(PERFIL_FIREFOX, exist_ok=True)

    try:
        from webdriver_manager.firefox import GeckoDriverManager
        service = FirefoxService(GeckoDriverManager().install())
        driver  = webdriver.Firefox(service=service, options=opts)
    except Exception:
        # Si webdriver_manager falla, intentar geckodriver del sistema
        driver = webdriver.Firefox(options=opts)

    driver.set_page_load_timeout(30)
    return driver


def obtener_driver():
    """Retorna el driver activo o crea uno nuevo."""
    global _driver
    with _driver_lock:
        if _driver is None:
            _driver = _crear_driver()
        else:
            # Verificar que sigue vivo
            try:
                _ = _driver.current_url
            except WebDriverException:
                _driver = _crear_driver()
    return _driver


def cerrar_driver():
    global _driver
    with _driver_lock:
        if _driver:
            try:
                _driver.quit()
            except Exception:
                pass
            _driver = None


# ─── Abrir y verificar sesión ──────────────────────────────

def abrir_whatsapp_web(esperar_qr=True):
    """
    Abre WhatsApp Web. Si hay sesión guardada, entra directo.
    Si no, espera hasta 60 s para escanear el QR.
    Devuelve (True, "conectado") o (False, "motivo").
    """
    if not SELENIUM_OK:
        return False, ("selenium no instalado. Ejecuta: "
                       "pip install selenium webdriver-manager")
    try:
        driver = obtener_driver()
        driver.get(WA_URL)

        # Dar tiempo a cargar
        time.sleep(3)

        wait = WebDriverWait(driver, 60 if esperar_qr else 15)

        # ¿Ya hay sesión activa?
        try:
            wait.until(EC.presence_of_element_located((By.XPATH, XPATH_LISTO)))
            return True, "WhatsApp Web conectado."
        except TimeoutException:
            pass

        # ¿Apareció el QR?
        try:
            WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.XPATH, XPATH_QR))
            )
            if esperar_qr:
                print("📱 Escanea el código QR en el navegador (tienes 60 segundos)...")
                # Esperar a que desaparezca el QR (=sesión iniciada)
                WebDriverWait(driver, 60).until(
                    EC.invisibility_of_element_located((By.XPATH, XPATH_QR))
                )
                time.sleep(2)
                return True, "Sesión de WhatsApp iniciada correctamente."
        except TimeoutException:
            pass

        return False, "No se pudo conectar a WhatsApp Web. Revisa el navegador."

    except Exception as e:
        return False, f"Error abriendo WhatsApp Web: {e}"


# ─── Enviar mensaje ────────────────────────────────────────

def enviar_mensaje_whatsapp(contacto, mensaje):
    """
    Envía un mensaje de WhatsApp al contacto indicado.
    contacto: nombre exacto como aparece en WhatsApp (ej: 'Mamá', '+57 300 123 4567')
    Devuelve string con resultado.
    """
    if not SELENIUM_OK:
        return "selenium no instalado. Ejecuta: pip install selenium webdriver-manager"

    try:
        driver = obtener_driver()

        # Asegurarse de estar en WA Web
        if "web.whatsapp.com" not in driver.current_url:
            ok, msg = abrir_whatsapp_web(esperar_qr=False)
            if not ok:
                return msg

        wait = WebDriverWait(driver, 20)

        # 1. Buscar el contacto en la barra de búsqueda
        barra = wait.until(EC.element_to_be_clickable((By.XPATH, XPATH_BUSQUEDA)))
        barra.click()
        time.sleep(0.5)
        barra.clear()
        barra.send_keys(contacto)
        time.sleep(2)   # Esperar resultados

        # 2. Hacer clic en el primer resultado con ese nombre
        try:
            resultado = wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH, XPATH_CONTACTO.format(nombre=contacto))
                )
            )
            resultado.click()
        except TimeoutException:
            # Intentar con búsqueda parcial
            try:
                resultado = driver.find_element(
                    By.XPATH,
                    f'//span[contains(@title, "{contacto}")]'
                )
                resultado.click()
            except NoSuchElementException:
                return f"No encontré el contacto '{contacto}' en WhatsApp."

        time.sleep(1)

        # 3. Escribir y enviar el mensaje
        input_msg = wait.until(
            EC.element_to_be_clickable((By.XPATH, XPATH_INPUT_MSG))
        )
        input_msg.click()
        # Escribir línea a línea (para saltos de línea usar Shift+Enter)
        for linea in mensaje.split("\n"):
            input_msg.send_keys(linea)
            if linea != mensaje.split("\n")[-1]:
                input_msg.send_keys(Keys.SHIFT + Keys.ENTER)
        input_msg.send_keys(Keys.ENTER)

        time.sleep(1)
        return f"✅ Mensaje enviado a '{contacto}': {mensaje[:60]}{'...' if len(mensaje)>60 else ''}"

    except Exception as e:
        return f"Error enviando mensaje: {e}"


# ─── Leer últimos mensajes ─────────────────────────────────

def leer_mensajes_whatsapp(contacto, cantidad=5):
    """
    Lee los últimos N mensajes de una conversación.
    Devuelve string con los mensajes.
    """
    if not SELENIUM_OK:
        return "selenium no instalado."

    try:
        driver  = obtener_driver()
        wait    = WebDriverWait(driver, 20)

        # Abrir conversación
        barra = wait.until(EC.element_to_be_clickable((By.XPATH, XPATH_BUSQUEDA)))
        barra.click()
        barra.clear()
        barra.send_keys(contacto)
        time.sleep(2)

        try:
            resultado = wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH, XPATH_CONTACTO.format(nombre=contacto))
                )
            )
            resultado.click()
        except TimeoutException:
            return f"No encontré el contacto '{contacto}'."

        time.sleep(2)

        # Extraer texto de los globos de mensaje
        # Selector estable: divs con data-pre-plain-text (contiene remitente+hora)
        bubbles = driver.find_elements(
            By.XPATH,
            '//div[@class and .//span[@class and @dir="ltr"]]'
            '//span[@dir="ltr"]'
        )

        textos = []
        for b in bubbles[-cantidad:]:
            t = b.text.strip()
            if t:
                textos.append(t)

        if not textos:
            return f"No pude leer mensajes de '{contacto}'. ¿La conversación está abierta?"

        return f"Últimos mensajes de '{contacto}':\n" + "\n".join(
            f"  • {t}" for t in textos[-cantidad:]
        )

    except Exception as e:
        return f"Error leyendo mensajes: {e}"


# ─── Recordatorio por WhatsApp ─────────────────────────────

def recordatorio_whatsapp(contacto, mensaje, segundos):
    """
    Envía un mensaje de WhatsApp a `contacto` después de `segundos`.
    Corre en background sin bloquear Jarvis.
    """
    def _enviar():
        time.sleep(segundos)
        resultado = enviar_mensaje_whatsapp(contacto, f"⏰ Recordatorio: {mensaje}")
        print(f"   [WhatsApp] {resultado}")
        # También notificar localmente
        try:
            from recordatorios import notificar
            notificar("⏰ Recordatorio enviado por WhatsApp",
                      f"→ {contacto}: {mensaje}",
                      urgencia="normal", duracion=5000)
        except Exception:
            pass

    t = threading.Thread(target=_enviar, daemon=True)
    t.start()

    # Calcular descripción de tiempo
    if segundos >= 3600:
        h  = segundos // 3600
        mn = (segundos % 3600) // 60
        desc = f"{h}h {mn}m" if mn else f"{h} hora{'s' if h>1 else ''}"
    elif segundos >= 60:
        mn   = segundos // 60
        desc = f"{mn} minuto{'s' if mn>1 else ''}"
    else:
        desc = f"{segundos} segundos"

    return f"📱 Recordatorio WhatsApp programado: '{mensaje}' → {contacto} en {desc}."


# ─── Estado de conexión ────────────────────────────────────

def estado_whatsapp():
    """Verifica si WhatsApp Web está abierto y conectado."""
    if not SELENIUM_OK:
        return "selenium no instalado."
    if _driver is None:
        return "WhatsApp Web no está abierto. Di 'abre whatsapp' para iniciar."
    try:
        _ = _driver.current_url
        if "web.whatsapp.com" in _driver.current_url:
            return "WhatsApp Web está abierto y activo."
        return "El navegador está abierto pero no en WhatsApp Web."
    except WebDriverException:
        return "WhatsApp Web se cerró inesperadamente."
