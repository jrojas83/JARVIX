"""
Jarvis Core (v7+ refactor).

Este paquete encapsula la nueva arquitectura modular:
- app: bucle principal (async-friendly)
- ai: orquestación de modelos (timeouts/retries/circuit breaker/first-wins)
- intents: resolución de órdenes (intents + sinónimos)
- plugins: compatibilidad con el sistema de plugins existente

El archivo raíz `jarvis.py` permanece como entrypoint compatible.
"""

