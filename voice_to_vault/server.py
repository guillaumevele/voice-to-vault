"""A minimal webhook listener (Python standard library only).

POST a transcript payload as JSON; it gets routed and filed into the vault.
Optionally verify an HMAC-SHA256 signature so only your provider can post.
"""
from __future__ import annotations

import hashlib
import hmac
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .config import Config
from .ingest import ingest
from .payload import capture_from_payload


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
            length = int(self.headers.get("Content-Length") or 0)
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
            self._send(200 if result.get("ok") else 422, result)

        def log_message(self, *args):  # silence default stderr logging
            pass

    return Handler


def serve(config: Config, host: str = "127.0.0.1", port: int = 8765, secret: str = "") -> None:
    server = ThreadingHTTPServer((host, port), make_handler(config, secret))
    print(f"voice-to-vault listening on http://{host}:{port}  (vault: {config.vault})")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()
