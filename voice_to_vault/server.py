"""A minimal webhook listener (Python standard library only).

POST a transcript payload as JSON; it gets routed and filed into the vault.
Optionally verify an HMAC-SHA256 signature so only your provider can post.
"""
from __future__ import annotations

import hashlib
import hmac
import ipaddress
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from .config import Config
from .ingest import ingest
from .payload import capture_from_payload


# A transcript payload is text; anything larger than this is refused before it is
# read, so a single request cannot exhaust memory.
MAX_BODY_BYTES = 1024 * 1024


def is_loopback(host: str) -> bool:
    """True when `host` only accepts connections from this machine."""
    if host == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def verify_signature(body: bytes, signature: str, secret: str) -> bool:
    """Constant-time check of an `X-Signature: <hex hmac-sha256>` header."""
    if not secret:
        return True  # no secret configured -> verification disabled
    expected = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    provided = (signature or "").strip().lower().removeprefix("sha256=")
    return hmac.compare_digest(expected, provided)


def make_handler(config: Config, secret: str = ""):
    class Handler(BaseHTTPRequestHandler):
        def _send(self, code: int, obj: dict) -> None:
            payload = json.dumps(obj).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def do_GET(self):  # noqa: N802 (stdlib naming)
            self._send(200, {"ok": True, "service": "voice-to-vault"})

        def do_POST(self):  # noqa: N802
            # A browser page can send a cross-site "simple" POST (text/plain or a
            # form) to a listener on localhost without any preflight. Requiring
            # application/json forces a CORS preflight, which this server never
            # answers, so a web page cannot file notes into the vault.
            media_type = (self.headers.get("Content-Type") or "").split(";")[0].strip().lower()
            if media_type != "application/json":
                self._send(415, {"ok": False, "error": "content-type-must-be-application/json"})
                return
            try:
                length = int(self.headers.get("Content-Length") or 0)
            except ValueError:
                length = -1
            if length < 0:
                self._send(400, {"ok": False, "error": "invalid-content-length"})
                return
            if length > MAX_BODY_BYTES:
                self._send(413, {"ok": False, "error": "payload-too-large"})
                return
            body = self.rfile.read(length) if length else b""
            if not verify_signature(body, self.headers.get("X-Signature", ""), secret):
                self._send(401, {"ok": False, "error": "invalid-signature"})
                return
            try:
                data = json.loads(body or b"{}")
            except ValueError:
                self._send(400, {"ok": False, "error": "invalid-json"})
                return
            if not isinstance(data, dict):
                self._send(400, {"ok": False, "error": "json-must-be-object"})
                return
            result = ingest(config, capture_from_payload(data))
            # Never echo absolute filesystem paths (or OS error text, which
            # contains them) to the network caller.
            result.pop("error", None)
            if result.get("note"):
                try:
                    result["note"] = Path(result["note"]).relative_to(config.vault).as_posix()
                except ValueError:
                    result["note"] = Path(result["note"]).name
            self._send(200 if result.get("ok") else 422, result)

        def log_message(self, *args):  # silence default stderr logging
            pass

    return Handler


def serve(config: Config, host: str = "127.0.0.1", port: int = 8765, secret: str = "") -> None:
    if not secret and not is_loopback(host):
        raise ValueError(
            f"refusing to listen on {host} without VOICE_TO_VAULT_SECRET: anyone who "
            "can reach this port could write notes into the vault"
        )
    server = ThreadingHTTPServer((host, port), make_handler(config, secret))
    print(f"voice-to-vault listening on http://{host}:{port}  (vault: {config.vault})")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()
