import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from conftest import make_config

import voice_to_vault.writer as writer_mod
from voice_to_vault.ingest import State, ingest
from voice_to_vault.writer import Capture


class TestIngest(unittest.TestCase):
    def setUp(self):
        self.vault = Path(tempfile.mkdtemp())
        self.cfg = make_config(self.vault)

    def _cap(self, cid="cap-1"):
        return Capture(id=cid, title="Client meeting", transcript="invoice deadline meeting")

    def test_writes_then_is_idempotent(self):
        first = ingest(self.cfg, self._cap())
        self.assertEqual(first["action"], "written")
        self.assertEqual(first["route"], "work")
        self.assertTrue(Path(first["note"]).exists())
        # second time: same id -> not written again
        second = ingest(self.cfg, self._cap())
        self.assertEqual(second["action"], "already-processed")

    def test_no_silent_loss_on_write_failure(self):
        # If the note write fails, the capture must NOT be marked processed, so it
        # can be retried — never silently dropped.
        with patch.object(writer_mod, "write_note", side_effect=OSError("disk full")):
            res = ingest(self.cfg, self._cap("cap-fail"))
        self.assertFalse(res["ok"])
        self.assertEqual(res["action"], "write-failed")
        state = State(self.vault / ".voice-to-vault" / "state.json").load()
        self.assertFalse(state.has("cap-fail"))
        # a retry (now succeeding) writes it
        retry = ingest(self.cfg, self._cap("cap-fail"))
        self.assertEqual(retry["action"], "written")

    def test_missing_id_rejected(self):
        self.assertFalse(ingest(self.cfg, Capture(id=""))["ok"])

    def test_corrupt_state_is_set_aside_not_wiped(self):
        state_path = self.vault / ".voice-to-vault" / "state.json"
        state_path.parent.mkdir(parents=True, exist_ok=True)
        state_path.write_text("{ this is not json", encoding="utf-8")
        ingest(self.cfg, self._cap("cap-after-corrupt"))
        # corrupt file preserved alongside, fresh ledger continues
        self.assertTrue(state_path.with_suffix(".json.corrupt").exists())
        reloaded = json.loads(state_path.read_text(encoding="utf-8"))
        self.assertIn("cap-after-corrupt", reloaded["processed"])


if __name__ == "__main__":
    unittest.main()
