from __future__ import annotations

import time
from dataclasses import dataclass


@dataclass
class CircuitState:
    failures: int = 0
    opened_until: float = 0.0

    def is_open(self) -> bool:
        return time.time() < self.opened_until


class CircuitBreaker:
    """
    Circuit breaker simple por proveedor.

    - Abre tras `failure_threshold` fallos consecutivos.
    - Permanece abierto `cooldown_s`.
    - Al éxito, resetea contador.
    """

    def __init__(self, *, failure_threshold: int = 2, cooldown_s: float = 20.0):
        self.failure_threshold = max(1, failure_threshold)
        self.cooldown_s = max(1.0, cooldown_s)
        self._states: dict[str, CircuitState] = {}

    def state(self, key: str) -> CircuitState:
        st = self._states.get(key)
        if st is None:
            st = CircuitState()
            self._states[key] = st
        return st

    def allow(self, key: str) -> bool:
        return not self.state(key).is_open()

    def on_success(self, key: str) -> None:
        st = self.state(key)
        st.failures = 0
        st.opened_until = 0.0

    def on_failure(self, key: str) -> None:
        st = self.state(key)
        st.failures += 1
        if st.failures >= self.failure_threshold:
            st.opened_until = time.time() + self.cooldown_s

