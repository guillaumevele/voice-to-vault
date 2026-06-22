# voice-to-vault

[![CI](https://github.com/guillaumevele/voice-to-vault/actions/workflows/ci.yml/badge.svg)](https://github.com/guillaumevele/voice-to-vault/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/)
[![Zero dependencies](https://img.shields.io/badge/dependencies-zero-success.svg)](pyproject.toml)

**Turn voice captures into a well-organized Obsidian vault.**

Point your transcription service's webhook at `voice-to-vault`. Each capture is
**routed** to the right folder by your own rules, written as a clean Markdown
note with front matter — **atomically**, **idempotently**, and with a guarantee
it's never silently lost. Then query the result with
[vault-ask](https://github.com/guillaumevele/vault-ask).

```console
$ echo '{"id":"abc","title":"Client invoice","transcript":"Send the invoice to the client after the meeting."}' \
    | voice-to-vault ingest --config config.json
{
  "ok": true,
  "action": "written",
  "note": ".../Work/2026-06-20_10-00-00_abc.md",
  "route": "work",
  "review_status": "auto-routed",
  "confidence": "high"
}
```

## Why

Voice capture is easy; keeping the result *organized and trustworthy* is the hard
part. `voice-to-vault` is the small, boring, correct middle layer:

- **Config-driven routing** — you declare routes (`keywords` / `aliases` → folder).
  Generic filler words ("note", "idea", "today") never decide a route on their own,
  so captures don't all pile into one place. Ties go to *needs-review*, not a guess.
- **Atomic writes** — a crash mid-write can never leave a half-written note.
- **Idempotent + no silent loss** — the same capture is never written twice, and if
  a write fails the capture is *not* marked done, so it can be retried instead of
  vanishing while the caller is told "ok".
- **Provider-agnostic** — maps common webhook payload shapes to a normalized capture.
- **Zero dependencies** — Python standard library only (the web listener too).

## Install

Requires **Python 3.9+**.

```bash
pip install git+https://github.com/guillaumevele/voice-to-vault.git
```

## Configure

Copy [`examples/config.example.json`](examples/config.example.json) and edit it:

```json
{
  "vault": "~/Obsidian/MyVault",
  "default_route": { "name": "inbox", "folder": "00-inbox" },
  "routes": [
    { "name": "work", "folder": "Work",
      "keywords": ["meeting", "deadline", "invoice"], "aliases": ["project"] },
    { "name": "tasks", "folder": "Tasks", "keywords": ["todo", "remind", "call back"] }
  ]
}
```

## Use

```bash
# See where some text would be routed (no write):
voice-to-vault route --config config.json "remind me to call back the client"

# Ingest one capture (JSON arg or stdin):
voice-to-vault ingest --config config.json --json '{"id":"1","transcript":"..."}'

# Run the webhook listener (stdlib http server):
export VOICE_TO_VAULT_SECRET=your-shared-secret   # optional HMAC-SHA256 verification
voice-to-vault serve --config config.json --port 8765
```

Point your provider's webhook at `http://host:8765/`. If `VOICE_TO_VAULT_SECRET`
is set, requests must carry an `X-Signature: <hex hmac-sha256(body)>` header.

## Library

The pieces are usable directly, with no web layer:

```python
from voice_to_vault import load_config, ingest, capture_from_payload

config = load_config("config.json")
result = ingest(config, capture_from_payload(my_payload_dict))
```

## Tests

```bash
python -m unittest discover -s tests -t tests
```

## License

MIT — see [LICENSE](LICENSE).
