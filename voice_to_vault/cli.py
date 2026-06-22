"""Command-line interface for voice-to-vault."""
from __future__ import annotations

import argparse
import json
import os
import sys

from . import __version__
from .config import load_config
from .ingest import ingest
from .payload import capture_from_payload
from .router import route as route_text


def _cmd_ingest(args) -> int:
    config = load_config(args.config)
    raw = args.json if args.json is not None else sys.stdin.read()
    try:
        payload = json.loads(raw or "{}")
    except ValueError as exc:
        print(f"voice-to-vault: invalid JSON ({exc})", file=sys.stderr)
        return 2
    result = ingest(config, capture_from_payload(payload))
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result.get("ok") else 1


def _cmd_route(args) -> int:
    config = load_config(args.config)
    result = route_text(" ".join(args.text), config)
    print(json.dumps(result.__dict__, indent=2, ensure_ascii=False))
    return 0


def _cmd_serve(args) -> int:
    from .server import serve  # imported lazily so `ingest`/`route` need no http
    config = load_config(args.config)
    secret = os.environ.get("VOICE_TO_VAULT_SECRET", "")
    serve(config, host=args.host, port=args.port, secret=secret)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="voice-to-vault",
        description="Route voice/transcript captures into an Obsidian vault.",
    )
    parser.add_argument("--version", action="version", version=f"voice-to-vault {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p_ingest = sub.add_parser("ingest", help="ingest one capture from JSON (arg or stdin)")
    p_ingest.add_argument("--config", required=True)
    p_ingest.add_argument("--json", default=None, help="capture payload as JSON (else stdin)")
    p_ingest.set_defaults(func=_cmd_ingest)

    p_route = sub.add_parser("route", help="show where some text would be routed")
    p_route.add_argument("--config", required=True)
    p_route.add_argument("text", nargs="+")
    p_route.set_defaults(func=_cmd_route)

    p_serve = sub.add_parser("serve", help="run the webhook listener")
    p_serve.add_argument("--config", required=True)
    p_serve.add_argument("--host", default="127.0.0.1")
    p_serve.add_argument("--port", type=int, default=8765)
    p_serve.set_defaults(func=_cmd_serve)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
