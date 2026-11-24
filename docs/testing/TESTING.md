# Testing Guide — check-opencode-free-models

How the automated tests for
[`check-opencode-free-models.py`](https://github.com/mahirfatih/check-opencode-free-models/blob/main/check-opencode-free-models.py)
are organized and executed.

## Overview

The tool is a single-file, standard-library-only Python CLI. Its test suites
mirror the development lifecycle:

| Phase | Suite | File | Runs |
|---|---|---|---|
| Safety net | Smoke | `test/test_smoke.py` | Fast, minimal sanity checks (compile + module load + trivial JSONC cases). |
| Deepest minimum | Sanity | `test/test_sanity.py` | Minimal invariants (constants, example config, generated block validity). |
| Logic | Unit | `test/test_unit.py` | Pure functions with mocks (`jsonc_to_json`, `read_config_models`, `build_block`, `fetch_free_ids`, `main`). |
| Fix protection | Regression | `test/test_regression.py` | Reproduces the JSONC validation bug; verifies the fix and apply idempotency. |
| Cross-cutting | Integration | `test/test_integration.py` | Local HTTP server + full fetch→diff→build→validate→write→read-back pipeline. |
| Whole feature | End-to-End (E2E) | `test/test_e2e.py` | Real CLI subprocess, isolated `HOME`, full `--apply` lifecycle. |
| UI contract | Automated UI | `test/test_automated_ui.py` | Terminal output, user-facing messages, exit codes. |

## Running

```bash
python3 -m unittest discover -s test -p "test_*.py" -v
./test/run_all_tests.sh            # same, via orchestrator
./test/run_all_tests.sh unit      # one suite via orchestrator
python3 test/test_unit.py         # a single suite directly
```

The full suite is expected to run in well under a minute (subprocess-based suites
use short timeouts; integration uses a local `127.0.0.1` server).

## Conventions

1. **Standard library only** — no third-party test dependencies
   (pytest/unittest + `unittest.mock`, `http.server`, `subprocess`).
2. **Isolated environments** — subprocess suites set `HOME` to a temp dir so the
   real `~/.config/opencode/opencode.jsonc` is never read or written.
3. **Turkish runtime strings stay Turkish** — assertions check the
   user-facing messages (`canlı ücretsiz sohbet modeli`, `SONUÇ: …`) so output
   regressions are caught; code comments/docstrings are English.
4. **Zero-dependency runtime** — tests must not add dependencies to
   `pyproject.toml` (`dependencies = []`).
5. **Naming** — suite files: `test_<area>.py` under `test/`; orchestrator:
   `test/run_all_tests.sh`.

## Adding a new test

- Add the case to the most specific suite (unit > regression > integration > e2e > ui).
- Keep pure logic in unit tests with mocks; keep process/network boundaries in
  integration/E2E suites.
- Add the file name to this document's suite table and to the main
  `README.md` / `README.tr.md` Testing section when a new suite is introduced.

## CI

There is no GitHub Actions workflow yet for the Python tool. When one is added,
wire `python3 -m unittest discover -s test -p "test_*.py" -v` into the pipeline.
