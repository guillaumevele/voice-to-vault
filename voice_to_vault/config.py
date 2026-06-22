"""Configuration: where the vault is and how captures are routed.

Routes are *your* config — a list of `{name, folder, keywords, aliases}`. Nothing
is hardcoded to any particular person or project.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

# Generic words that say nothing about *topic* and must never decide a route on
# their own (otherwise everything lands in whichever route happens to list them).
# This is the "black hole" lesson: meta/filler words are filtered from routing.
DEFAULT_WEAK_TERMS = frozenset({
    "note", "notes", "idea", "ideas", "voice", "memo", "recording", "transcript",
    "thing", "stuff", "today", "thought", "capture", "test",
    "idee", "idees", "truc", "chose", "memo", "vocal", "vocale", "enregistrement",
})


@dataclass(frozen=True)
class Route:
    name: str
    folder: str
    keywords: tuple[str, ...] = ()
    aliases: tuple[str, ...] = ()


@dataclass(frozen=True)
class Config:
    vault: Path
    routes: tuple[Route, ...]
    default_route: Route
    weak_terms: frozenset = DEFAULT_WEAK_TERMS

    @property
    def all_routes(self) -> tuple[Route, ...]:
        return self.routes + (self.default_route,)


def _route_from_dict(data: dict) -> Route:
    return Route(
        name=str(data["name"]),
        folder=str(data.get("folder") or data["name"]),
        keywords=tuple(str(k) for k in data.get("keywords", [])),
        aliases=tuple(str(a) for a in data.get("aliases", [])),
    )


def load_config(path: str | Path) -> Config:
    """Load a JSON config file. Schema:

        {
          "vault": "~/Obsidian/MyVault",
          "default_route": {"name": "inbox", "folder": "00-inbox"},
          "routes": [
            {"name": "work", "folder": "Work",
             "keywords": ["meeting", "deadline"], "aliases": ["project"]},
            {"name": "personal", "folder": "Personal", "keywords": ["family"]}
          ],
          "weak_terms": ["optional", "extra", "stopwords"]
        }
    """
    data = json.loads(Path(path).expanduser().read_text(encoding="utf-8"))
    vault = Path(str(data["vault"])).expanduser()
    routes = tuple(_route_from_dict(r) for r in data.get("routes", []))
    default_raw = data.get("default_route") or {"name": "inbox", "folder": "00-inbox"}
    default_route = _route_from_dict(default_raw)
    weak = data.get("weak_terms")
    weak_terms = frozenset(str(w).lower() for w in weak) if weak else DEFAULT_WEAK_TERMS
    return Config(vault=vault, routes=routes, default_route=default_route, weak_terms=weak_terms)
