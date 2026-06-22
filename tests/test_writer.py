import tempfile
import unittest
from pathlib import Path

from conftest import make_config

from voice_to_vault.router import route
from voice_to_vault.writer import Capture, atomic_write_text, write_note


class TestAtomicWrite(unittest.TestCase):
    def test_atomic_write_exact_and_no_residual_tmp(self):
        d = Path(tempfile.mkdtemp())
        target = d / "sub" / "note.md"
        atomic_write_text(target, "hello\nworld")
        self.assertEqual(target.read_text(encoding="utf-8"), "hello\nworld")
        residual = list(d.rglob(".note.md.*.tmp"))
        self.assertEqual(residual, [])


class TestWriteNote(unittest.TestCase):
    def test_note_lands_in_routed_folder_with_frontmatter(self):
        vault = Path(tempfile.mkdtemp())
        cfg = make_config(vault)
        cap = Capture(
            id="cap-001", title="Invoice follow-up",
            transcript="Need to send the invoice to the client after the meeting.",
            recorded_at="2026-06-20T10:00:00Z",
        )
        rr = route(cap.text, cfg)
        path = write_note(cfg, cap, rr)
        self.assertTrue(path.exists())
        self.assertEqual(path.parent, vault / "Work")
        body = path.read_text(encoding="utf-8")
        self.assertIn("id: cap-001", body)
        self.assertIn("route: work", body)
        self.assertIn("## Transcript", body)


if __name__ == "__main__":
    unittest.main()
