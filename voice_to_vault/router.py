"""Deterministic routing: which folder does a capture belong to?

Keyword/alias matching with whole-word boundaries and a weak-term filter, so a
generic word never decides a route on its own. Ties fall back to needs-review
rather than guessing.
"""
from __future__ import annotations

from dataclasses import dataclass

from .config import Config, Route
from .text import contains_word, normalize


@dataclass(frozen=True)
class RouteResult:
    route: str
    folder: str
    confidence: str       # "high" | "medium" | "low"
    review_status: str    # "auto-routed" | "needs-review"
    matched: tuple[str, ...]
    score: int


def _hits(text_norm: str, terms, weak_terms) -> list[str]:
    out = []
    for term in terms:
        norm = normalize(term).strip()
        if not norm or norm in weak_terms:
            continue
        if contains_word(text_norm, norm):
            out.append(term)
    return out


def route(text: str, config: Config) -> RouteResult:
    """Route free text to the best-matching route. Aliases weigh double; the
    strongest route wins; an exact tie is left for human review."""
    text_norm = normalize(text)
    scored: list[tuple[int, int, Route, list[str]]] = []
    for index, rule in enumerate(config.routes):
        kw = _hits(text_norm, rule.keywords, config.weak_terms)
        al = _hits(text_norm, rule.aliases, config.weak_terms)
        hits = kw + al
        if hits:
            score = len(kw) + 2 * len(al)
            scored.append((score, -index, rule, hits))

    if not scored:
        d = config.default_route
        return RouteResult(d.name, d.folder, "low", "needs-review", (), 0)

    scored.sort(key=lambda item: (item[0], item[1]), reverse=True)
    score, _neg_index, rule, hits = scored[0]
    tied = len(scored) > 1 and scored[1][0] == score
    confidence = "high" if score >= 3 and not tied else "medium" if score >= 2 and not tied else "low"
    review = "auto-routed" if confidence in {"high", "medium"} else "needs-review"
    return RouteResult(rule.name, rule.folder, confidence, review, tuple(dict.fromkeys(hits)), score)
