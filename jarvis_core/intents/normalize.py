from __future__ import annotations

import re
import unicodedata


def strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


_WS = re.compile(r"\s+")
_PUNCT = re.compile(r"[^\w\s:]+", flags=re.UNICODE)


def normalize_text(text: str) -> str:
    t = (text or "").strip().lower()
    t = strip_accents(t)
    t = _PUNCT.sub(" ", t)
    t = _WS.sub(" ", t).strip()
    return t

