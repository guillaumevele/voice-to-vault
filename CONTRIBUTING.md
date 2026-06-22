# Contributing

Thanks for your interest. voice-to-vault is intentionally small and
**dependency-free** (Python standard library only, web listener included).
Please keep it that way.

## Non-negotiables

- **Atomic writes**, **idempotent ingestion**, and **no silent loss** are the
  point of this project. Any change to `writer.py` or `ingest.py` must preserve
  them — and add a test that proves it.
- **Routing must not be decided by generic filler words** (the weak-terms filter).

## Development

```bash
git clone https://github.com/guillaumevele/voice-to-vault.git
cd voice-to-vault
python -m unittest discover -s tests -t tests -v
```

## Pull requests

- Add or update tests for any behaviour change.
- Keep the CLI and result schema stable where possible.
