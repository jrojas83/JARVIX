"""
JARVIX — Cache Semántica + Intent Matcher de 3 niveles
=======================================================
Nivel 1: Cache semántica  → reutiliza respuestas similares (umbral 0.92)
Nivel 2: Intent matcher   → acción local sin IA         (umbral 0.85)
Nivel 3: IA              → clasifica y despacha al intent correcto

Instalación:
    pip install sentence-transformers numpy
"""

from __future__ import annotations

import json
import time
import hashlib
from dataclasses import dataclass, field
from typing import Callable, Optional


# ──────────────────────────────────────────────────────────────────────────────
# Carga del modelo — lazy, una sola vez, compartido por todos los módulos
# ──────────────────────────────────────────────────────────────────────────────

_modelo_emb = None
_np_module = None

def _get_model():
    """Carga el modelo de embeddings solo la primera vez que se necesita."""
    global _modelo_emb
    if _modelo_emb is None:
        print("[semantic] Cargando modelo de embeddings (solo una vez)...")
        from sentence_transformers import SentenceTransformer
        # all-MiniLM-L6-v2: 90 MB, rápido, bueno en español
        _modelo_emb = SentenceTransformer("all-MiniLM-L6-v2")
        print("[semantic] Modelo listo.")
    return _modelo_emb


def _get_numpy():
    """Importa numpy bajo demanda (lazy loading)."""
    global _np_module
    if _np_module is None:
        import numpy as np
        _np_module = np
    return _np_module


def _embedding(texto: str):
    """Genera el vector de embeddings para un texto."""
    return _get_model().encode(texto, normalize_embeddings=True)


def _similitud(a, b):
    """Similitud coseno entre dos vectores normalizados. Rango: 0.0 – 1.0"""
    np = _get_numpy()
    return float(np.dot(a, b))


# ──────────────────────────────────────────────────────────────────────────────
# NIVEL 1 — Cache semántica
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class _EntradaCache:
    respuesta: str
    embedding: object
    hits: int = 0
    creada: float = field(default_factory=time.time)
    ttl_seg: float = 300  # 5 minutos por defecto


class CacheSemantica:
    """
    Guarda respuestas y las reutiliza cuando llega una orden semánticamente
    similar, sin importar si las palabras son distintas.

    Ejemplo:
        "¿qué hora es?" y "dime la hora" → misma respuesta cacheada
        "clima en medellín" y "temperatura en medellín" → misma respuesta
    """

    def __init__(self, umbral: float = 0.92, max_entradas: int = 200):
        self.umbral = umbral
        self.max_entradas = max_entradas
        self._cache: list[_EntradaCache] = []
        self._stats = {"hits": 0, "misses": 0}

    def buscar(self, orden: str) -> Optional[str]:
        """Busca una respuesta semánticamente equivalente. Retorna None si no hay hit."""
        emb = _embedding(orden)
        ahora = time.time()

        mejor_sim = 0.0
        mejor: Optional[_EntradaCache] = None

        for entrada in self._cache:
            # Ignorar entradas expiradas
            if ahora - entrada.creada > entrada.ttl_seg:
                continue
            sim = _similitud(emb, entrada.embedding)
            if sim > mejor_sim:
                mejor_sim = sim
                mejor = entrada

        if mejor and mejor_sim >= self.umbral:
            mejor.hits += 1
            self._stats["hits"] += 1
            return mejor.respuesta

        self._stats["misses"] += 1
        return None

    def guardar(self, orden: str, respuesta: str, ttl_seg: float = 300):
        """Guarda una nueva entrada en el cache."""
        # Evitar duplicados exactos
        for entrada in self._cache:
            if _similitud(_embedding(orden), entrada.embedding) >= 0.99:
                entrada.respuesta = respuesta  # actualizar
                return

        # Rotar si está lleno
        if len(self._cache) >= self.max_entradas:
            # Eliminar la con menos hits y más vieja
            self._cache.sort(key=lambda e: (e.hits, -e.creada))
            self._cache.pop(0)

        self._cache.append(_EntradaCache(
            respuesta=respuesta,
            embedding=_embedding(orden),
            ttl_seg=ttl_seg,
        ))

    def limpiar_expiradas(self):
        ahora = time.time()
        self._cache = [e for e in self._cache if ahora - e.creada <= e.ttl_seg]

    def estadisticas(self) -> str:
        total = self._stats["hits"] + self._stats["misses"]
        rate = (self._stats["hits"] / total * 100) if total else 0
        activas = sum(
            1 for e in self._cache
            if time.time() - e.creada <= e.ttl_seg
        )
        return (
            f"Cache semántica: {activas} entradas activas | "
            f"Hit rate: {rate:.0f}% | "
            f"Umbral: {self.umbral}"
        )


# ──────────────────────────────────────────────────────────────────────────────
# NIVEL 2 — Intent Matcher semántico
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class Intent:
    """
    Un intent define una acción local con múltiples frases de ejemplo.
    Las frases cubren variaciones naturales del mismo pedido.
    """
    nombre: str
    frases: list[str]
    accion: Callable[[str], str]
    ttl_cache: float = 300  # TTL para guardar en cache si se ejecuta
    _embeddings: list[object] = field(default_factory=list, repr=False)

    def precalcular_embeddings(self):
        """Precalcula embeddings de todas las frases. Llamar al inicio."""
        self._embeddings = [_embedding(f) for f in self.frases]

    def similitud_maxima(self, emb_orden: object) -> float:
        """Máxima similitud entre la orden y cualquiera de las frases del intent."""
        if not self._embeddings:
            self.precalcular_embeddings()
        return max(_similitud(emb_orden, e) for e in self._embeddings)


class IntentMatcher:
    """
    Compara una orden con todos los intents registrados y ejecuta
    el que tenga mayor similitud semántica, si supera el umbral.

    A diferencia de regex o keywords, entiende variaciones naturales:
        "sube el volumen" ≈ "pon el audio más alto" ≈ "aumenta el sonido"
    """

    def __init__(self, umbral: float = 0.85):
        self.umbral = umbral
        self._intents: list[Intent] = []

    def registrar(self, intent: Intent) -> "IntentMatcher":
        """Agrega un intent al matcher. Precalcula embeddings automáticamente."""
        intent.precalcular_embeddings()
        self._intents.append(intent)
        return self  # permite encadenar

    def resolver(self, orden: str) -> tuple[Optional[Intent], float]:
        """
        Retorna (intent_ganador, similitud) o (None, 0.0) si no supera el umbral.
        """
        if not self._intents:
            return None, 0.0

        emb = _embedding(orden)
        mejor_intent = None
        mejor_sim = 0.0

        for intent in self._intents:
            sim = intent.similitud_maxima(emb)
            if sim > mejor_sim:
                mejor_sim = sim
                mejor_intent = intent

        if mejor_sim >= self.umbral:
            return mejor_intent, mejor_sim
        return None, mejor_sim

    def listar(self) -> list[str]:
        return [f"{i.nombre} ({len(i.frases)} variaciones)" for i in self._intents]


# ──────────────────────────────────────────────────────────────────────────────
# NIVEL 3 — Clasificador con IA
# ──────────────────────────────────────────────────────────────────────────────

def _prompt_clasificador(orden: str, intents_disponibles: list[str]) -> str:
    """Prompt para que la IA clasifique la orden en el intent más lógico."""
    lista = "\n".join(f"- {nombre}" for nombre in intents_disponibles)
    return f"""Eres el clasificador de intents de JARVIX, un asistente de escritorio Linux.

El usuario dijo: "{orden}"

Intents disponibles:
{lista}
- NINGUNO (si no encaja con ninguno)

Responde ÚNICAMENTE con el nombre exacto del intent más apropiado.
No expliques, no agregues texto. Solo el nombre del intent.

Ejemplos:
- "pon algo de música" → spotify_play
- "cómo está el clima" → consultar_clima
- "apaga la pantalla" → NINGUNO
"""


class ClasificadorIA:
    """
    Cuando la cache y el matcher local fallan, la IA clasifica la orden
    en el intent más apropiado y lo ejecuta — en lugar de responder
    en lenguaje natural sin acción concreta.
    """

    def __init__(self, fn_llamar_ia: Callable[[str], str]):
        """
        fn_llamar_ia: función que toma un prompt y retorna la respuesta de la IA.
        Usa la función existente de JARVIX (groq, gemini, ollama, etc.)
        """
        self._llamar_ia = fn_llamar_ia

    def clasificar(self, orden: str, matcher: IntentMatcher) -> Optional[Intent]:
        """
        Pide a la IA que clasifique la orden. Si coincide con un intent
        registrado, lo retorna para ejecutarlo localmente.
        """
        nombres = [i.nombre for i in matcher._intents]
        if not nombres:
            return None

        prompt = _prompt_clasificador(orden, nombres)
        respuesta_ia = self._llamar_ia(prompt).strip()

        # Buscar el intent por nombre exacto
        for intent in matcher._intents:
            if intent.nombre.lower() == respuesta_ia.lower():
                return intent

        # Tolerancia: coincidencia parcial por si la IA agrega texto extra
        respuesta_lower = respuesta_ia.lower()
        for intent in matcher._intents:
            if intent.nombre.lower() in respuesta_lower:
                return intent

        return None  # "NINGUNO" o no reconoció


# ──────────────────────────────────────────────────────────────────────────────
# ORQUESTADOR — Los 3 niveles juntos
# ──────────────────────────────────────────────────────────────────────────────

class ProcesadorSemantico:
    """
    Orquesta los 3 niveles de resolución:

        orden → [Cache semántica] → [Intent matcher] → [IA clasificadora]
                      ↓hit                ↓hit               ↓hit
                 respuesta            acción local        acción local
                 directa              sin IA              vía IA
    """

    def __init__(
        self,
        fn_llamar_ia: Callable[[str], str],
        fn_respuesta_libre: Callable[[str], str],
        umbral_cache: float = 0.92,
        umbral_intent: float = 0.85,
    ):
        self.cache = CacheSemantica(umbral=umbral_cache)
        self.matcher = IntentMatcher(umbral=umbral_intent)
        self.clasificador = ClasificadorIA(fn_llamar_ia)
        self._fn_respuesta_libre = fn_respuesta_libre
        self._log: list[dict] = []

    def registrar_intent(self, intent: Intent) -> "ProcesadorSemantico":
        self.matcher.registrar(intent)
        return self

    def procesar(self, orden: str) -> tuple[str, str]:
        """
        Procesa una orden y retorna (respuesta, nivel_usado).
        nivel_usado: 'cache' | 'intent_local' | 'ia_intent' | 'ia_libre'
        """
        orden_norm = orden.strip().lower()

        # ── Nivel 1: Cache semántica ──────────────────────────────────────────
        cached = self.cache.buscar(orden_norm)
        if cached:
            self._registrar_log(orden, "cache", cached)
            return cached, "cache"

        # ── Nivel 2: Intent matcher local ─────────────────────────────────────
        intent, sim = self.matcher.resolver(orden_norm)
        if intent:
            respuesta = intent.accion(orden)
            self.cache.guardar(orden_norm, respuesta, ttl_seg=intent.ttl_cache)
            self._registrar_log(orden, f"intent_local (sim={sim:.2f})", respuesta)
            return respuesta, "intent_local"

        # ── Nivel 3: IA clasifica → ejecuta intent local ──────────────────────
        intent_ia = self.clasificador.clasificar(orden_norm, self.matcher)
        if intent_ia:
            respuesta = intent_ia.accion(orden)
            # Guardar en cache con TTL corto (la IA puede equivocarse)
            self.cache.guardar(orden_norm, respuesta, ttl_seg=120)
            self._registrar_log(orden, f"ia_intent→{intent_ia.nombre}", respuesta)
            return respuesta, "ia_intent"

        # ── Fallback: IA responde en lenguaje natural ─────────────────────────
        respuesta = self._fn_respuesta_libre(orden)
        self._registrar_log(orden, "ia_libre", respuesta)
        return respuesta, "ia_libre"

    def _registrar_log(self, orden: str, nivel: str, respuesta: str):
        self._log.append({
            "orden": orden,
            "nivel": nivel,
            "respuesta_preview": respuesta[:60],
            "ts": time.time(),
        })

    def estadisticas(self) -> str:
        niveles = [e["nivel"].split("(")[0].strip() for e in self._log]
        conteo = {}
        for n in niveles:
            conteo[n] = conteo.get(n, 0) + 1
        total = len(niveles)
        lineas = [self.cache.estadisticas(), f"Total procesadas: {total}"]
        for nivel, c in conteo.items():
            lineas.append(f"  {nivel}: {c} ({c/total*100:.0f}%)")
        return "\n".join(lineas)


# ──────────────────────────────────────────────────────────────────────────────
# INTENTS LISTOS PARA JARVIX — copia y adapta a acciones.py
# ──────────────────────────────────────────────────────────────────────────────

def construir_intents_jarvix(acciones) -> list[Intent]:
    """
    Crea los intents de JARVIX con múltiples variaciones naturales.
    'acciones' es el módulo acciones.py de JARVIX.
    """
    return [
        Intent(
            nombre="hora_actual",
            frases=[
                "qué hora es",
                "dime la hora",
                "qué hora tienes",
                "me puedes decir la hora",
                "cuánto es la hora",
                "hora actual",
                "qué horas son",
                "a qué horas estamos",
            ],
            accion=lambda _: acciones.obtener_hora(),
            ttl_cache=30,  # la hora cambia rápido
        ),
        Intent(
            nombre="consultar_clima",
            frases=[
                "clima en bogotá",
                "qué temperatura hace",
                "cómo está el tiempo",
                "va a llover hoy",
                "pronóstico del tiempo",
                "hace frío afuera",
                "temperatura actual",
                "cómo está el clima",
                "qué tan caliente está",
            ],
            accion=lambda orden: acciones.consultar_clima(orden),
            ttl_cache=600,  # 10 minutos
        ),
        Intent(
            nombre="subir_volumen",
            frases=[
                "sube el volumen",
                "más volumen",
                "pon el audio más alto",
                "aumenta el sonido",
                "no escucho bien",
                "súbele al volumen",
                "volumen más alto",
            ],
            accion=lambda _: acciones.subir_volumen(),
            ttl_cache=60,
        ),
        Intent(
            nombre="bajar_volumen",
            frases=[
                "baja el volumen",
                "menos volumen",
                "pon el audio más bajo",
                "disminuye el sonido",
                "está muy alto",
                "bájale al volumen",
                "volumen más bajo",
            ],
            accion=lambda _: acciones.bajar_volumen(),
            ttl_cache=60,
        ),
        Intent(
            nombre="silenciar",
            frases=[
                "silencia",
                "pon en mudo",
                "apaga el sonido",
                "quita el audio",
                "sin sonido",
                "mute",
                "silencio",
            ],
            accion=lambda _: acciones.silenciar(),
            ttl_cache=60,
        ),
        Intent(
            nombre="abrir_firefox",
            frases=[
                "abre firefox",
                "abre el navegador",
                "quiero navegar",
                "abre internet",
                "inicia firefox",
                "abre el browser",
                "necesito el navegador",
            ],
            accion=lambda _: acciones.abrir_app("firefox"),
            ttl_cache=120,
        ),
        Intent(
            nombre="abrir_vscode",
            frases=[
                "abre vscode",
                "abre el editor",
                "abre code",
                "quiero programar",
                "abre visual studio",
                "inicia el editor de código",
                "abrir vs code",
            ],
            accion=lambda _: acciones.abrir_app("code"),
            ttl_cache=120,
        ),
        Intent(
            nombre="abrir_terminal",
            frases=[
                "abre la terminal",
                "abre una consola",
                "necesito la terminal",
                "abre el terminal",
                "dame una terminal",
                "quiero una consola",
                "abrir bash",
            ],
            accion=lambda _: acciones.abrir_app("gnome-terminal"),
            ttl_cache=120,
        ),
        Intent(
            nombre="abrir_spotify",
            frases=[
                "abre spotify",
                "pon música",
                "quiero escuchar música",
                "abre la música",
                "inicia spotify",
                "pon algo de música",
                "quiero música",
            ],
            accion=lambda _: acciones.abrir_app("spotify"),
            ttl_cache=120,
        ),
        Intent(
            nombre="estado_sistema",
            frases=[
                "cómo está el sistema",
                "cuánta ram estoy usando",
                "estado del pc",
                "cómo va el computador",
                "uso de cpu",
                "recursos del sistema",
                "memoria disponible",
                "cuánto está usando el sistema",
            ],
            accion=lambda _: acciones.estado_sistema(),
            ttl_cache=30,
        ),
        Intent(
            nombre="wifi_activar",
            frases=[
                "activa el wifi",
                "enciende el wifi",
                "conecta el wifi",
                "activa la red",
                "quiero internet",
                "pon el wifi",
                "conectarme a internet",
            ],
            accion=lambda _: acciones.wifi(True),
            ttl_cache=60,
        ),
        Intent(
            nombre="wifi_desactivar",
            frases=[
                "desactiva el wifi",
                "apaga el wifi",
                "desconecta el wifi",
                "quita la red",
                "sin wifi",
                "apaga internet",
            ],
            accion=lambda _: acciones.wifi(False),
            ttl_cache=60,
        ),
        Intent(
            nombre="listar_notas",
            frases=[
                "lee mis notas",
                "qué notas tengo",
                "muéstrame las notas",
                "cuáles son mis notas",
                "qué tengo anotado",
                "mis apuntes",
                "ver notas",
            ],
            accion=lambda _: acciones.leer_notas(),
            ttl_cache=30,
        ),
        Intent(
            nombre="leer_pantalla",
            frases=[
                "qué hay en pantalla",
                "lee la pantalla",
                "qué estoy viendo",
                "analiza la pantalla",
                "qué dice la pantalla",
                "describe lo que ves",
                "qué hay en la pantalla",
            ],
            accion=lambda _: acciones.vision_pantalla(),
            ttl_cache=5,  # la pantalla cambia constantemente
        ),
        Intent(
            nombre="modo_trabajo",
            frases=[
                "activa modo trabajo",
                "voy a programar",
                "prepara el entorno de trabajo",
                "modo programación",
                "configura todo para trabajar",
                "empieza mi sesión de trabajo",
                "abre todo para trabajar",
                "modo dev",
            ],
            accion=lambda _: acciones.activar_modo_trabajo(),
            ttl_cache=300,
        ),
    ]
