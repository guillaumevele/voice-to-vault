"""Small text helpers shared across modules (zero dependencies)."""
from __future__ import annotations

import re
import unicodedata


def normalize(text: str) -> str:
    """Lowercase + strip accents for accent/case-insensitive matching."""
    decomposed = unicodedata.normalize("NFKD", str(text or ""))
    stripped = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return stripped.lower()


def contains_word(haystack_normalized: str, term: str) -> bool:
    """Whole-word containment of `term` in already-normalized text. Avoids
    accidental substring hits ('art' must not match 'depart')."""
    needle = normalize(term).strip()
    if not needle:
        return False
    return re.search(
        rf"(?<![a-z0-9]){re.escape(needle)}(?![a-z0-9])",
        haystack_normalized,
    ) is not None


def slugify(value: str, fallback: str = "note") -> str:
    text = normalize(value)
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return text or fallback
