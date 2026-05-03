"""
jarvis_core/vision.py — Visión de pantalla para JARVIX
=======================================================
100% OFFLINE. Sin APIs externas. Sin internet.

Usa:
  - mss          → captura de pantalla rápida (pip install mss)
  - Pillow        → procesamiento de imagen (pip install Pillow)
  - pytesseract  → OCR local (pip install pytesseract)
  - xdotool      → detectar ventana activa (sudo apt install xdotool)
  - wmctrl       → fallback detección de ventana (sudo apt install wmctrl)

Instalar dependencias completas:
  pip install mss Pillow pytesseract
  sudo apt install tesseract-ocr tesseract-ocr-spa xdotool wmctrl

Uso desde acciones.py / intenciones.py:
  from jarvis_core.vision import ScreenVision
  vision = ScreenVision()
  texto = vision.leer_pantalla()       # OCR completo
  ventana = vision.ventana_activa()    # "Firefox — Google"
  resumen = vision.describir()         # descripción en lenguaje natural (sin IA)
"""

import logging
import os
import re
import subprocess
import time
from io import BytesIO
from typing import Optional

log = logging.getLogger("jarvis.vision")

# ── Imports opcionales — nunca crashean al importar ───────────
try:
    import mss
    MSS_OK = True
except ImportError:
    MSS_OK = False

try:
    from PIL import Image, ImageEnhance, ImageFilter
    PIL_OK = True
except ImportError:
    PIL_OK = False

try:
    import pytesseract
    OCR_OK = True
except ImportError:
    OCR_OK = False


# ════════════════════════════════════════════════════════════════
class ScreenVision:
    """
    Visión de pantalla 100% local.

    Parámetros
    ----------
    monitor      : índice de monitor (1 = principal)
    cache_seg    : segundos que se cachea el resultado (evita OCR repetido)
    max_width    : ancho máximo antes de hacer OCR (más pequeño = más rápido)
    lang_ocr     : idioma(s) de tesseract, e.g. "spa+eng"
    """

    def __init__(self, monitor: int = 1, cache_seg: int = 15,
                 max_width: int = 1280, lang_ocr: str = "spa+eng"):
        self.monitor = monitor
        self.cache_seg = cache_seg
        self.max_width = max_width
        self.lang_ocr = lang_ocr
        self._cache: dict = {}

    # ─── API pública ────────────────────────────────────────

    def ventana_activa(self) -> str:
        """
        Devuelve el título de la ventana activa sin hacer OCR.
        Muy rápido — usa xdotool o wmctrl.
        """
        # Intento 1: xdotool
        try:
            wid = subprocess.check_output(
                ["xdotool", "getactivewindow"], stderr=subprocess.DEVNULL
            ).decode().strip()
            titulo = subprocess.check_output(
                ["xdotool", "getwindowname", wid], stderr=subprocess.DEVNULL
            ).decode().strip()
            return titulo
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass

        # Intento 2: wmctrl
        try:
            out = subprocess.check_output(
                ["wmctrl", "-l"], stderr=subprocess.DEVNULL
            ).decode()
            for line in out.splitlines():
                if "*" in line or len(out.splitlines()) == 1:
                    partes = line.split(None, 3)
                    if len(partes) >= 4:
                        return partes[3]
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass

        # Intento 3: xprop
        try:
            out = subprocess.check_output(
                ["xprop", "-root", "_NET_ACTIVE_WINDOW"], stderr=subprocess.DEVNULL
            ).decode()
            m = re.search(r"0x[0-9a-f]+", out)
            if m:
                titulo_raw = subprocess.check_output(
                    ["xprop", "-id", m.group(), "WM_NAME"], stderr=subprocess.DEVNULL
                ).decode()
                m2 = re.search(r'"(.+)"', titulo_raw)
                if m2:
                    return m2.group(1)
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass

        return "Ventana desconocida"

    def leer_pantalla(self) -> str:
        """
        OCR completo de la pantalla. Devuelve todo el texto visible.
        Usa caché para no repetir OCR en menos de cache_seg segundos.
        """
        cached = self._get_cache("ocr")
        if cached is not None:
            return cached

        img = self._capturar()
        if img is None:
            return self._error_deps()

        if not OCR_OK:
            return "OCR no disponible. Instala: pip install pytesseract && sudo apt install tesseract-ocr tesseract-ocr-spa"

        try:
            # Preprocesar para mejorar OCR
            img_proc = self._preprocesar(img)
            texto = pytesseract.image_to_string(img_proc, lang=self.lang_ocr)
            lineas = [l.strip() for l in texto.splitlines() if l.strip()]
            resultado = "\n".join(lineas[:60])  # máx 60 líneas
            self._set_cache("ocr", resultado)
            return resultado if resultado else "No encontré texto legible en pantalla."
        except Exception as e:
            log.error("[VISION] Error OCR: %s", e)
            return f"Error al leer pantalla: {e}"

    def describir(self) -> str:
        """
        Descripción en lenguaje natural de lo que hay en pantalla.
        Combina ventana activa + palabras clave del OCR.
        100% local, sin IA.
        """
        cached = self._get_cache("desc")
        if cached is not None:
            return cached

        ventana = self.ventana_activa()
        texto_ocr = self.leer_pantalla() if OCR_OK and MSS_OK and PIL_OK else ""

        # Analizar el contexto a partir de palabras clave
        ctx = self._analizar_contexto(ventana, texto_ocr)
        resultado = f"Ventana activa: {ventana}. {ctx}"
        self._set_cache("desc", resultado)
        return resultado

    def describir_breve(self) -> str:
        """
        Una línea: app + qué parece estar haciendo.
        Para mensajes de inactividad o contexto rápido.
        """
        ventana = self.ventana_activa()
        app = ventana.split(" — ")[0].split(" - ")[0].strip()
        return app if app else "escritorio"

    def proponer_accion(self) -> Optional[str]:
        """
        Devuelve una propuesta de ayuda basada en lo que hay en pantalla,
        o None si no hay nada concreto que proponer.
        """
        ventana = self.ventana_activa().lower()
        texto = ""
        if OCR_OK and MSS_OK and PIL_OK:
            texto = self.leer_pantalla().lower()

        propuestas = [
            # Patrones: (palabras_en_ventana_o_texto, propuesta)
            (["error", "exception", "traceback", "errno"],
             "Veo un error en pantalla. ¿Quieres que te ayude a interpretarlo?"),
            (["untitled", "sin título", "new document", "nuevo documento"],
             "Parece que tienes un documento nuevo. ¿Necesitas ayuda para redactar algo?"),
            (["terminal", "bash", "zsh"],
             "Tienes una terminal abierta. ¿Necesitas ayuda con algún comando?"),
            (["gmail", "outlook", "thunderbird", "email", "correo"],
             "Veo que tienes el correo abierto. ¿Necesitas ayuda para redactar?"),
            (["stackoverflow", "error 404", "cannot find", "no such file"],
             "Parece que estás buscando solucionar un problema. ¿Te ayudo?"),
            (["pdf", "document", "docx", ".pdf"],
             "Tienes un documento abierto. ¿Quieres que te ayude a resumirlo?"),
        ]

        contexto_completo = ventana + " " + texto
        for palabras, propuesta in propuestas:
            if any(p in contexto_completo for p in palabras):
                return propuesta

        return None

    def estado_dependencias(self) -> str:
        """Verifica qué está instalado y qué falta."""
        xdotool = self._cmd_existe("xdotool")
        wmctrl = self._cmd_existe("wmctrl")
        tesseract = self._cmd_existe("tesseract")

        lineas = ["Estado de dependencias de Visión:"]
        lineas.append(f"  mss (screenshot):      {'✅' if MSS_OK else '❌  pip install mss'}")
        lineas.append(f"  Pillow (imágenes):     {'✅' if PIL_OK else '❌  pip install Pillow'}")
        lineas.append(f"  pytesseract (Python):  {'✅' if OCR_OK else '❌  pip install pytesseract'}")
        lineas.append(f"  tesseract (binario):   {'✅' if tesseract else '❌  sudo apt install tesseract-ocr tesseract-ocr-spa'}")
        lineas.append(f"  xdotool (ventana):     {'✅' if xdotool else '⚠️   sudo apt install xdotool'}")
        lineas.append(f"  wmctrl (fallback):     {'✅' if wmctrl else '⚠️   sudo apt install wmctrl'}")
        ok = MSS_OK and PIL_OK and OCR_OK and tesseract
        lineas.append("")
        lineas.append("  → " + ("Todo listo ✅" if ok else "Faltan dependencias. Ejecuta: bash instalar.sh"))
        return "\n".join(lineas)

    # ─── Internos ────────────────────────────────────────────

    def _capturar(self) -> Optional["Image.Image"]:
        if not MSS_OK or not PIL_OK:
            return None
        try:
            with mss.mss() as sct:
                mon = sct.monitors[self.monitor]
                sct_img = sct.grab(mon)
                img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
            if img.width > self.max_width:
                ratio = self.max_width / img.width
                img = img.resize((self.max_width, int(img.height * ratio)), Image.LANCZOS)
            return img
        except Exception as e:
            log.error("[VISION] Error capturando pantalla: %s", e)
            return None

    def _preprocesar(self, img: "Image.Image") -> "Image.Image":
        """Mejora la imagen para que tesseract lea mejor."""
        try:
            img = img.convert("L")                        # escala de grises
            img = ImageEnhance.Contrast(img).enhance(2.0) # más contraste
            img = img.filter(ImageFilter.SHARPEN)          # nitidez
        except Exception:
            pass
        return img

    def _analizar_contexto(self, ventana: str, texto: str) -> str:
        """Devuelve una descripción de contexto basada en palabras clave."""
        v = ventana.lower()
        t = texto.lower()
        ctx = v + " " + t

        if "code" in v or "vs code" in v or "pycharm" in v or "nvim" in v:
            return "Parece que estás programando."
        if "firefox" in v or "chrome" in v or "chromium" in v:
            return "Tienes el navegador abierto."
        if "terminal" in v or "bash" in v or "zsh" in v or "konsole" in v:
            return "Tienes una terminal abierta."
        if "gmail" in t or "outlook" in t or "thunderbird" in v:
            return "Tienes el correo abierto."
        if "youtube" in t or "vlc" in v or "mpv" in v:
            return "Parece que estás viendo un video."
        if "spotify" in v or "rhythmbox" in v or "música" in t:
            return "Tienes música o audio abierto."
        if "libreoffice" in v or "writer" in v or "calc" in v:
            return "Tienes un documento de oficina abierto."
        if "error" in t or "exception" in t or "traceback" in t:
            return "Hay un error visible en pantalla."
        return ""

    def _get_cache(self, key: str):
        entry = self._cache.get(key)
        if entry and time.time() - entry["ts"] < self.cache_seg:
            return entry["v"]
        return None

    def _set_cache(self, key: str, val):
        self._cache[key] = {"v": val, "ts": time.time()}

    def _error_deps(self) -> str:
        return "Visión no disponible. Instala: pip install mss Pillow pytesseract"

    @staticmethod
    def _cmd_existe(cmd: str) -> bool:
        try:
            subprocess.check_output(["which", cmd], stderr=subprocess.DEVNULL)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
