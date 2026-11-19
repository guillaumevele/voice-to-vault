"""voice-to-vault — route voice/transcript captures into an Obsidian vault.

A small, dependency-free pipeline: a webhook (or CLI) receives a transcript,
deterministic config-driven routing decides which folder it belongs to, and an
atomic writer files it as a Markdown note — idempotently, with no silent loss.

Pairs nicely with `vault-ask` to query the resulting vault.
"""
from __future__ import annotations

from .config import Config, Route, load_config
from .ingest import State, ingest
from .payload import capture_from_payload
from .router import RouteResult, route
from .writer import Capture, write_note

__version__ = "0.1.1"

__all__ = [
    "Config", "Route", "load_config",
    "Capture", "RouteResult", "route", "write_note",
    "State", "ingest", "capture_from_payload",
    "__version__",
]
