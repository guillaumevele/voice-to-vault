"""Idempotent ingestion of a capture into the vault.

Two hard guarantees:
  - **Idempotent**: the same capture id is never written twice.
  - **No silent loss**: if the note fails to write, the capture is NOT marked
    processed, so it can be retried — instead of being lost forever while the
    caller is told everything is fine.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

from . import writer
from .config import Config
from .router import route
from .writer import Capture, atomic_write_text


class State:
    """A tiny idempotence ledger (capture id -> record), persisted atomically."""

    def __init__(self, path: Path):
        self.path = Path(path)
        self.processed: dict[str, dict] = {}

    def load(self) -> "State":
        if self.path.exists():
            try:
                data = json.loads(self.path.read_text(encoding="utf-8"))
                self.processed = dict(data.get("processed") or {})
            except (ValueError, OSError):
                # Corrupt ledger: move it aside (never silently wipe history) and
                # start fresh so ingestion can continue.
                try:
                    self.path.replace(self.path.with_suffix(self.path.suffix + ".corrupt"))
                except OSError:
                    pass
                self.processed = {}
        return self

    def has(self, capture_id: str) -> bool:
        return capture_id in self.processed

    def mark(self, capture_id: str, note: str | None) -> None:
        self.processed[capture_id] = {"ts": int(time.time() * 1000), "note": note}
        atomic_write_text(self.path, json.dumps({"processed": self.processed}, indent=2))


def _state_path(config: Config) -> Path:
    return config.vault / ".voice-to-vault" / "state.json"


def ingest(config: Config, capture: Capture, state: State | None = None) -> dict:
    """Route and write one capture, exactly once. Returns a structured result."""
    if not capture.id:
        return {"ok": False, "action": "missing-id"}
    state = state or State(_state_path(config)).load()
    if state.has(capture.id):
        return {"ok": True, "action": "already-processed", "id": capture.id}

    route_result = route(capture.text, config)
    try:
        path = writer.write_note(config, capture, route_result)
    except OSError as exc:
        # Note write failed: do NOT mark processed (retryable), do NOT pretend success.
        return {
            "ok": False,
            "action": "write-failed",
            "id": capture.id,
            "error": str(exc),
            "route": route_result.route,
        }

    state.mark(capture.id, str(path))
    return {
        "ok": True,
        "action": "written",
        "id": capture.id,
        "note": str(path),
        "route": route_result.route,
        "review_status": route_result.review_status,
        "confidence": route_result.confidence,
    }
