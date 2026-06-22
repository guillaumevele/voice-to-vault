"""Map an arbitrary provider's webhook JSON to a normalized Capture.

Different transcription services use different field names. Rather than hardcode
one provider, we look for the usual suspects (and you can pre-map upstream).
"""
from __future__ import annotations

from .writer import Capture


def _first(payload: dict, *keys: str) -> str:
    for key in keys:
        cur: object = payload
        for part in key.split("."):
            if isinstance(cur, dict) and part in cur:
                cur = cur[part]
            else:
                cur = None
                break
        if isinstance(cur, (str, int, float)) and str(cur).strip():
            return str(cur).strip()
    return ""


def capture_from_payload(payload: dict) -> Capture:
    """Best-effort extraction of a Capture from a generic JSON payload."""
    recording = payload.get("recording") if isinstance(payload.get("recording"), dict) else {}
    return Capture(
        id=_first(payload, "id", "recording_id", "recording.id", "uuid"),
        title=_first(payload, "title", "recording.title", "name"),
        transcript=_first(payload, "transcript", "text", "transcription.text", "body"),
        summary=_first(payload, "summary", "summary.text", "summarization.summary"),
        recorded_at=_first(
            payload, "recorded_at", "recording_at", "recording.created_at",
            "created_at", "createdAt", "timestamp",
        ),
    )
