"""Write a capture as a Markdown note — atomically — into its routed folder."""
from __future__ import annotations

import os
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .config import Config
from .router import RouteResult
from .text import slugify


@dataclass(frozen=True)
class Capture:
    """A normalized voice capture, decoupled from any provider's payload shape."""
    id: str
    title: str = ""
    transcript: str = ""
    summary: str = ""
    recorded_at: str = ""   # ISO 8601; defaults to now when empty

    @property
    def text(self) -> str:
        return "\n".join(p for p in (self.title, self.summary, self.transcript) if p)


def atomic_write_text(path: Path, text: str, encoding: str = "utf-8") -> None:
    """Write text atomically: same-dir temp file + replace, cleanup on failure.
    A crash mid-write can never leave a half-written (corrupt) note."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.{time.time_ns()}.tmp")
    try:
        tmp.write_text(text, encoding=encoding)
        tmp.replace(path)
    finally:
        if tmp.exists():
            tmp.unlink()


def _yaml_scalar(value: object) -> str:
    if isinstance(value, list):
        inner = ", ".join(f'"{str(v)}"' for v in value)
        return f"[{inner}]"
    s = str(value)
    if s == "":
        return '""'
    return f'"{s}"' if any(c in s for c in ':#\n"') else s


def render_note(capture: Capture, route_result: RouteResult, recorded_at: str) -> str:
    fm = {
        "id": capture.id,
        "title": capture.title or "Untitled capture",
        "recorded_at": recorded_at,
        "route": route_result.route,
        "review_status": route_result.review_status,
        "route_confidence": route_result.confidence,
        "matched": list(route_result.matched),
        "tags": ["voice-capture", f"route-{route_result.route}"],
    }
    lines = ["---"]
    lines += [f"{k}: {_yaml_scalar(v)}" for k, v in fm.items()]
    lines += ["---", "", f"# {capture.title or 'Untitled capture'}", ""]
    if capture.summary:
        lines += ["## Summary", "", capture.summary, ""]
    if capture.transcript:
        lines += ["## Transcript", "", capture.transcript, ""]
    return "\n".join(lines)


def note_path(config: Config, capture: Capture, route_result: RouteResult, recorded_at: str) -> Path:
    try:
        stamp = datetime.fromisoformat(recorded_at.replace("Z", "+00:00")).strftime("%Y-%m-%d_%H-%M-%S")
    except ValueError:
        stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H-%M-%S")
    name = f"{stamp}_{slugify(capture.id, 'capture')[:24]}.md"
    return config.vault / route_result.folder / name


def write_note(config: Config, capture: Capture, route_result: RouteResult) -> Path:
    recorded_at = capture.recorded_at or datetime.now(timezone.utc).isoformat()
    path = note_path(config, capture, route_result, recorded_at)
    atomic_write_text(path, render_note(capture, route_result, recorded_at))
    return path
