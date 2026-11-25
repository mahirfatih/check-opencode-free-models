# Testing Guide — check-opencode-free-models

How the automated tests for
[`check-opencode-free-models.py`](https://github.com/mahirfatih/check-opencode-free-models/blob/main/check-opencode-free-models.py)
are organized and executed.

## Overview

The tool is a single-file, standard-library-only Python CLI. Its test suites
mirror the development lifecycle:

| Phase | Suite | File | Runs |
|---|---|---|---|
| Safety net | Smoke | `test/test-smoke.py` | Fast, minimal sanity checks (compile + module load + trivial JSONC cases). |
| Deepest minimum | Sanity | `test/test-sanity.py` | Minimal invariants (constants, example config, generated block validity). |
| Logic | Unit | `test/test-unit.py` | Pure functions with mocks (`jsonc_to_json`, `read_config_models`, `build_block`, `fetch_free_ids`, `main`). |
| Fix protection | Regression | `test/test-regression.py` | Reproduces the JSONC validation bug; verifies the fix and apply idempotency. |
| Cross-cutting | Integration | `test/test-integration.py` | Local HTTP server + full fetch→diff→build→validate→write→read-back pipeline. |
| Whole feature | End-to-End (E2E) | `test/test-e2e.py` | Real CLI subprocess, isolated `HOME`, full `--apply` lifecycle. |
| UI contract | Automated UI | `test/test-automated-ui.py` | Terminal output, user-facing messages, exit codes. |

## Running

```bash
python3 test/run-tests.py            # all suites (stdlib importlib runner)
python3 test/run-tests.py unit       # one suite
./test/run-all-tests.sh              # shell wrapper, all suites
./test/run-all-tests.sh smoke        # shell wrapper, one suite
python3 test/test-unit.py            # a single suite directly
```

`unittest discover` silently finds no tests in `test-*.py` files: hyphenated
file names are not importable module names. `test/run-tests.py` loads each suite
by path with `importlib.util.spec_from_file_location` and feeds it to the
standard `unittest` runner, so the suite stays dependency-free.

The full suite is expected to run in well under a minute (subprocess-based suites
use short timeouts; integration uses a local `127.0.0.1` server).

## Conventions

1. **Standard library only** — no third-party test dependencies
   (`unittest`, `unittest.mock`, `http.server`, `subprocess`, `importlib`).
2. **Isolated environments** — subprocess suites set `HOME` to a temp dir so the
   real `~/.config/opencode/opencode.jsonc` is never read or written.
3. **Turkish runtime strings stay Turkish** — assertions check the
   user-facing messages (`canlı ücretsiz sohbet modeli`, `SONUÇ: …`) so output
   regressions are caught; code comments/docstrings are English.
4. **Zero-dependency runtime** — tests must not add dependencies to
   `pyproject.toml` (`dependencies = []`).
5. **Naming** — suite files: `test/test-<area>.py` under `test/` (kebab-case);
   runners: `test/run-tests.py` and `test/run-all-tests.sh`.
6. **Extending the runner** — add a new suite to `SUITES` in `test/run-tests.py`
   so CI and the shell wrapper pick it up.

## Adding a new test

- Add the case to the most specific suite (unit > regression > integration > e2e > ui).
- Keep pure logic in unit tests with mocks; keep process/network boundaries in
  integration/E2E suites.
- Add the file name to this document's suite table, to `SUITES` in
  `test/run-tests.py`, and to the main `README.md` / `README.tr.md` Testing
  section when a new suite is introduced.

## CI

GitHub Actions (`.github/workflows/ci.yml`) runs on every push to `main` and on
pull requests:

```bash
python3 -m py_compile check-opencode-free-models.py test/run-tests.py
python3 test/run-tests.py
```

Actions are pinned to full commit SHAs; keep that convention when updating them.
