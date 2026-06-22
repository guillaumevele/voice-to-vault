import hashlib
import hmac
import unittest

from voice_to_vault.payload import capture_from_payload
from voice_to_vault.server import verify_signature


class TestPayload(unittest.TestCase):
    def test_extracts_common_shapes(self):
        cap = capture_from_payload({
            "recording": {"id": "abc", "title": "Hello", "created_at": "2026-06-20T10:00:00Z"},
            "transcript": "the full text",
            "summary": "short",
        })
        self.assertEqual(cap.id, "abc")
        self.assertEqual(cap.title, "Hello")
        self.assertEqual(cap.transcript, "the full text")
        self.assertEqual(cap.summary, "short")
        self.assertEqual(cap.recorded_at, "2026-06-20T10:00:00Z")

    def test_flat_shape(self):
        cap = capture_from_payload({"id": "x1", "text": "hello", "title": "T"})
        self.assertEqual(cap.id, "x1")
        self.assertEqual(cap.transcript, "hello")


class TestSignature(unittest.TestCase):
    SECRET = "shh"

    def _sig(self, body: bytes) -> str:
        return hmac.new(self.SECRET.encode(), body, hashlib.sha256).hexdigest()

    def test_valid_signature(self):
        body = b'{"id":"1"}'
        self.assertTrue(verify_signature(body, self._sig(body), self.SECRET))

    def test_invalid_signature(self):
        self.assertFalse(verify_signature(b'{"id":"1"}', "deadbeef", self.SECRET))

    def test_sha256_prefix_accepted(self):
        body = b'{"id":"1"}'
        self.assertTrue(verify_signature(body, "sha256=" + self._sig(body), self.SECRET))

    def test_no_secret_disables_verification(self):
        self.assertTrue(verify_signature(b"anything", "", ""))


if __name__ == "__main__":
    unittest.main()
