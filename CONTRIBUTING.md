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
- `python3 test/run-tests.py` — full automated test suite (smoke / sanity /
  unit / regression / integration / e2e / ui; see [`test/README.md`](./test/README.md)).
  `./test/run-all-tests.sh unit` runs one suite via the shell wrapper.
- Keep the script a single file; do not split it into a package.
- Kebab-case file names for shell and Python files (the main script and all test
  suites). Python identifiers inside the files stay PEP 8 snake_case; the runner
  loads hyphenated suite files by path because `unittest` discovery cannot.
- Update `README.md` / `README.tr.md` and `CHANGELOG.md` in the same commit
  when behaviour changes.

## Pull requests

- One logical change per PR, English imperative commit messages (≤ 72 chars).
- Do not commit real `opencode.jsonc` files or API keys; use redacted examples.
