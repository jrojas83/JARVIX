# clima.py — Jarvis v5
# Consulta el clima via OpenWeatherMap (API gratuita).
# Requiere: pip install requests   (ya está en el proyecto)
# Lazy loading: requests solo se importa cuando se usa
#
# Cómo obtener tu API key GRATIS:
#   1. Ve a https://openweathermap.org/api
#   2. Crea una cuenta (es gratis)
#   3. En "My API Keys" copia la key
#   4. Pégala en config.py → OPENWEATHER_API_KEY

_requests_module = None

def _get_requests():
    """Importa requests bajo demanda (lazy loading)."""
    global _requests_module
    if _requests_module is None:
        import requests
        _requests_module = requests
    return _requests_module

from datetime import datetime

# Importar key desde config (puede estar vacía)
try:
    from config import OPENWEATHER_API_KEY, CIUDAD_DEFAULT
except ImportError:
    OPENWEATHER_API_KEY = ""
    CIUDAD_DEFAULT      = "Cali,CO"

BASE_URL     = "https://api.openweathermap.org/data/2.5"
ICONOS_CLIMA = {
    "clear sky":           "☀️",
    "few clouds":          "🌤️",
    "scattered clouds":    "⛅",
    "broken clouds":       "☁️",
    "overcast clouds":     "☁️",
    "light rain":          "🌦️",
    "moderate rain":       "🌧️",
    "heavy intensity rain":"🌧️",
    "thunderstorm":        "⛈️",
    "snow":                "❄️",
    "mist":                "🌫️",
    "fog":                 "🌫️",
    "drizzle":             "🌦️",
}

def _icono(descripcion):
    desc_lower = descripcion.lower()
    for key, icono in ICONOS_CLIMA.items():
        if key in desc_lower:
            return icono
    return "🌡️"

def _ciudad_a_query(texto):
    """
    Extrae el nombre de ciudad de una frase en español.
    'cómo está el clima en medellín' → 'medellín,CO'
    'clima en bogotá' → 'bogotá,CO'
    'temperatura en nueva york' → 'nueva york'
    Si no hay ciudad, usa CIUDAD_DEFAULT.
    """
    texto = texto.lower().strip()
    for prefijo in ["clima en ", "tiempo en ", "temperatura en ",
                    "cómo está el clima en ", "como esta el clima en ",
                    "cómo está el tiempo en ", "como esta el tiempo en ",
                    "qué clima hace en ", "que clima hace en "]:
        if prefijo in texto:
            ciudad = texto.split(prefijo, 1)[1].strip()
            ciudad = ciudad.rstrip("?¿.,")
            # Si es ciudad colombiana, añadir ,CO
            ciudades_co = ["cali", "bogotá", "bogota", "medellín", "medellin",
                           "barranquilla", "cartagena", "bucaramanga", "pereira",
                           "manizales", "armenia", "cúcuta", "cucuta", "ibagué",
                           "ibague", "pasto", "santa marta", "villavicencio"]
            if any(c in ciudad for c in ciudades_co) and ",co" not in ciudad:
                ciudad += ",CO"
            return ciudad if ciudad else CIUDAD_DEFAULT
    return CIUDAD_DEFAULT


def obtener_clima(ciudad_o_frase=None):
    """
    Consulta el clima actual para una ciudad.
    Acepta nombre directo ('Cali') o frase ('clima en medellín').
    Devuelve string legible para hablar/mostrar.
    """
    if not OPENWEATHER_API_KEY or OPENWEATHER_API_KEY == "TU_API_KEY_AQUI":
        return ("Para usar el clima necesito una API key de OpenWeatherMap. "
                "Es gratis en openweathermap.org. "
                "Agrégala en config.py como OPENWEATHER_API_KEY.")

    # Determinar ciudad
    if ciudad_o_frase:
        ciudad = _ciudad_a_query(ciudad_o_frase)
        # Si no cambió (no encontró prefijo), usar el texto directo como ciudad
        if ciudad == CIUDAD_DEFAULT and not any(
            p in ciudad_o_frase.lower()
            for p in ["clima", "tiempo", "temperatura"]
        ):
            ciudad = ciudad_o_frase.strip()
    else:
        ciudad = CIUDAD_DEFAULT

    try:
        requests_lib = _get_requests()
        resp = requests_lib.get(
            f"{BASE_URL}/weather",
            params={
                "q":     ciudad,
                "appid": OPENWEATHER_API_KEY,
                "units": "metric",
                "lang":  "es",
            },
            timeout=8
        )
        if resp.status_code == 401:
            return "API key de OpenWeatherMap inválida. Revisa config.py."
        if resp.status_code == 404:
            return f"No encontré la ciudad '{ciudad}'. Intenta con otro nombre."
        resp.raise_for_status()
        d = resp.json()

        nombre_ciudad = d["name"]
        pais          = d["sys"]["country"]
        temp          = round(d["main"]["temp"])
        sensacion     = round(d["main"]["feels_like"])
        humedad       = d["main"]["humidity"]
        descripcion   = d["weather"][0]["description"].capitalize()
        icono         = _icono(d["weather"][0]["description"])
        viento        = round(d["wind"]["speed"] * 3.6)  # m/s → km/h

        return (
            f"{icono} {descripcion} en {nombre_ciudad}, {pais}. "
            f"Temperatura: {temp}°C (sensación {sensacion}°C). "
            f"Humedad: {humedad}%. Viento: {viento} km/h."
        )

    except Exception as e:
        requests_lib = _get_requests()
        if isinstance(e, requests_lib.exceptions.ConnectionError):
            return "Sin conexión a internet para consultar el clima."
        if isinstance(e, requests_lib.exceptions.Timeout):
            return "El servidor del clima tardó demasiado, intenta de nuevo."
        return f"Error consultando el clima: {e}"


def obtener_pronostico(ciudad_o_frase=None):
    """
    Pronostico de los próximos 3 días (resumen por día).
    """
    if not OPENWEATHER_API_KEY or OPENWEATHER_API_KEY == "TU_API_KEY_AQUI":
        return "Configura OPENWEATHER_API_KEY en config.py para usar el pronóstico."

    ciudad = _ciudad_a_query(ciudad_o_frase) if ciudad_o_frase else CIUDAD_DEFAULT

    try:
        requests_lib = _get_requests()
        resp = requests_lib.get(
            f"{BASE_URL}/forecast",
            params={
                "q":     ciudad,
                "appid": OPENWEATHER_API_KEY,
                "units": "metric",
                "lang":  "es",
                "cnt":   24,   # 3 días × 8 mediciones/día
            },
            timeout=8
        )
        if resp.status_code != 200:
            return f"No pude obtener el pronóstico para '{ciudad}'."
        d     = resp.json()
        items = d["list"]

        # Agrupar por día
        dias  = {}
        for item in items:
            fecha = item["dt_txt"].split(" ")[0]
            if fecha not in dias:
                dias[fecha] = {"temps": [], "desc": []}
            dias[fecha]["temps"].append(item["main"]["temp"])
            dias[fecha]["desc"].append(item["weather"][0]["description"])

        lineas = [f"Pronóstico para {d['city']['name']}:"]
        for fecha, info in list(dias.items())[:3]:
            dt       = datetime.strptime(fecha, "%Y-%m-%d")
            dia_nom  = dt.strftime("%A %d/%m")
            t_min    = round(min(info["temps"]))
            t_max    = round(max(info["temps"]))
            desc_mas = max(set(info["desc"]), key=info["desc"].count).capitalize()
            icono    = _icono(desc_mas)
            lineas.append(f"  {icono} {dia_nom}: {desc_mas}, {t_min}°–{t_max}°C")

        return "\n".join(lineas)

    except Exception as e:
        return f"Error en pronóstico: {e}"
        return f"Error en pronóstico: {e}"
