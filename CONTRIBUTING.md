# Contributing

Thanks for your interest in **check-opencode-free-models**. This is a small,
single-file tool, so the contribution surface is intentionally narrow.

## Development setup

```bash
python3 check-opencode-free-models.py            # drift report (read-only)
python3 check-opencode-free-models.py --apply    # apply + timestamped backup
```

No third-party dependencies: only the Python standard library
(`argparse`, `json`, `re`, `shutil`, `urllib`, …).

## Checks before a change

- `python3 -m py_compile check-opencode-free-models.py` — syntax.
- `python3 check-opencode-free-models.py` — drift report (exit `0` when in sync).
- `python3 -m unittest discover -s test -p "test_*.py" -v` — full automated test suite
  (smoke / sanity / unit / regression / integration / e2e / ui; see [`test/README.md`](./test/README.md)).
- Keep the script a single file; do not split it into a package.
- PEP 8 naming for everything inside the file (the file name itself stays
  kebab-case per the repo convention).
- Update `README.md` / `README.tr.md` and `CHANGELOG.md` in the same commit
  when behaviour changes.

## Pull requests

- One logical change per PR, English imperative commit messages (≤ 72 chars).
- Do not commit real `opencode.jsonc` files or API keys; use redacted examples.
