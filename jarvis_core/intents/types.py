from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Mapping


Decision = dict  # compat: {"accion": str, "parametros": dict}


@dataclass(frozen=True)
class Intent:
    id: str
    phrases: tuple[str, ...] = ()
    contains: tuple[str, ...] = ()
    # matcher custom (devuelve Decision o None)
    match: Callable[[str], Decision | None] | None = None
    handler: Callable[[str], Decision] | None = None
    metadata: Mapping[str, str] | None = None

