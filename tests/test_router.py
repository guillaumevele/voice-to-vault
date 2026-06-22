import tempfile
import unittest
from pathlib import Path

from conftest import make_config

from voice_to_vault.router import route


class TestRouter(unittest.TestCase):
    def setUp(self):
        self.cfg = make_config(Path(tempfile.mkdtemp()))

    def test_routes_by_keyword(self):
        r = route("Reminder about the invoice for the client meeting", self.cfg)
        self.assertEqual(r.route, "work")
        self.assertEqual(r.review_status, "auto-routed")
        self.assertGreaterEqual(r.score, 2)

    def test_alias_counts_double(self):
        r = route("notes on the project kickoff", self.cfg)
        self.assertEqual(r.route, "work")  # "project" alias

    def test_weak_words_do_not_decide_a_route(self):
        # "note", "idea", "today" are weak: a capture that only contains them must
        # NOT be confidently routed (the black-hole bug we deliberately avoid).
        r = route("Just a quick voice note idea for today", self.cfg)
        self.assertEqual(r.review_status, "needs-review")
        self.assertEqual(r.route, "inbox")

    def test_no_match_falls_back_to_default_needs_review(self):
        r = route("xyzzy quux fnord", self.cfg)
        self.assertEqual(r.route, "inbox")
        self.assertEqual(r.review_status, "needs-review")
        self.assertEqual(r.confidence, "low")

    def test_whole_word_only(self):
        # "deadline" must not be matched by "deadlines"? it should (substring of
        # word boundary): ensure "art" never matches inside "department".
        cfg = make_config(Path("/tmp"))
        r = route("a department reorg", cfg)
        self.assertEqual(r.route, "inbox")  # no real keyword hit


if __name__ == "__main__":
    unittest.main()
