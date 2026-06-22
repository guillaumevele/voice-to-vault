"""Shared test helpers (no pytest required; plain unittest)."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from voice_to_vault.config import Config, Route  # noqa: E402


def make_config(vault: Path) -> Config:
    return Config(
        vault=vault,
        routes=(
            Route("work", "Work", keywords=("meeting", "deadline", "invoice"), aliases=("project",)),
            Route("ideas", "Ideas", keywords=("brainstorm", "concept")),
            Route("tasks", "Tasks", keywords=("todo", "remind")),
        ),
        default_route=Route("inbox", "00-inbox"),
    )
