"""Security behaviour of the webhook listener and of the front-matter writer."""
import http.client
import json
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path

from voice_to_vault.config import Config, Route
from voice_to_vault.router import RouteResult
from voice_to_vault.server import MAX_BODY_BYTES, is_loopback, make_handler, serve
from voice_to_vault.writer import Capture, render_note


class ServerCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.vault = Path(self.tmp.name)
        config = Config(vault=self.vault, routes=(), default_route=Route("inbox", "00-inbox"))
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(config))
        self.port = self.server.server_address[1]
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.tmp.cleanup()

    def post(self, body: bytes, headers: dict):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        try:
            conn.request("POST", "/", body=body, headers=headers)
            resp = conn.getresponse()
            return resp.status, json.loads(resp.read() or b"{}")
        finally:
            conn.close()

    def notes(self):
        return [p for p in self.vault.rglob("*.md")]

    def test_json_post_is_filed_and_path_is_vault_relative(self):
        body = json.dumps({"id": "abc", "transcript": "hello"}).encode()
        status, data = self.post(body, {"Content-Type": "application/json; charset=utf-8"})
        self.assertEqual(status, 200)
        self.assertEqual(len(self.notes()), 1)
        self.assertTrue(data["note"].startswith("00-inbox/"))
        self.assertNotIn(str(self.vault), json.dumps(data))

    def test_cross_site_simple_post_is_refused(self):
        body = json.dumps({"id": "csrf", "transcript": "from a web page"}).encode()
        for content_type in ("text/plain", "application/x-www-form-urlencoded", "multipart/form-data"):
            status, data = self.post(body, {"Content-Type": content_type})
            self.assertEqual(status, 415, content_type)
        status, _ = self.post(body, {})
        self.assertEqual(status, 415)
        self.assertEqual(self.notes(), [])

    def test_oversized_body_is_refused_before_reading(self):
        # Only the header announces the size: the server must answer without
        # waiting for (or buffering) the body.
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        try:
            conn.putrequest("POST", "/")
            conn.putheader("Content-Type", "application/json")
            conn.putheader("Content-Length", str(MAX_BODY_BYTES + 1))
            conn.endheaders()
            self.assertEqual(conn.getresponse().status, 413)
        finally:
            conn.close()
        self.assertEqual(self.notes(), [])

    def test_invalid_content_length_is_refused(self):
        for value in ("-1", "abc"):
            conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
            try:
                conn.putrequest("POST", "/")
                conn.putheader("Content-Type", "application/json")
                conn.putheader("Content-Length", value)
                conn.endheaders()
                self.assertEqual(conn.getresponse().status, 400, value)
            finally:
                conn.close()


class TestBindPolicy(unittest.TestCase):
    def test_loopback_detection(self):
        for host in ("127.0.0.1", "localhost", "::1", "127.0.0.2"):
            self.assertTrue(is_loopback(host), host)
        for host in ("0.0.0.0", "::", "192.168.1.10", "example.com", ""):
            self.assertFalse(is_loopback(host), host)

    def test_public_bind_without_secret_is_refused(self):
        config = Config(vault=Path("."), routes=(), default_route=Route("inbox", "00-inbox"))
        with self.assertRaises(ValueError):
            serve(config, host="0.0.0.0", port=0, secret="")


class TestFrontMatterEscaping(unittest.TestCase):
    ROUTE = RouteResult("inbox", "00-inbox", "low", "needs-review", (), 0)

    def front_matter(self, **fields):
        note = render_note(Capture(**fields), self.ROUTE, "2026-06-20T10:00:00Z")
        head = note.split("\n---\n", 1)[0].splitlines()[1:]
        return head

    def test_title_cannot_inject_front_matter_keys(self):
        evil = 'x"\nreview_status: "auto-routed'
        head = self.front_matter(id="1", title=evil)
        keys = [line.split(":", 1)[0] for line in head]
        self.assertEqual(keys.count("review_status"), 1)
        self.assertEqual(len(head), 8)  # one line per key, nothing added
        title_line = next(line for line in head if line.startswith("title: "))
        self.assertEqual(json.loads(title_line[len("title: "):]), evil)

    def test_id_cannot_inject_front_matter_keys(self):
        head = self.front_matter(id="a\ntags: [pwned]", title="t")
        self.assertEqual(len(head), 8)
        self.assertEqual(sum(1 for line in head if line.startswith("tags:")), 1)

    def test_plain_values_stay_readable(self):
        head = self.front_matter(id="abc-123", title="Weekly sync")
        self.assertIn("id: abc-123", head)
        self.assertIn("title: Weekly sync", head)
        self.assertIn('recorded_at: "2026-06-20T10:00:00Z"', head)


if __name__ == "__main__":
    unittest.main()
