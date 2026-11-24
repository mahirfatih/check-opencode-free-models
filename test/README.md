# Tests — check-opencode-free-models

This folder contains the automated test suites for
[`check-opencode-free-models.py`](../check-opencode-free-models.py).

## Suites

| Suite | File | Purpose |
|---|---|---|
| Smoke | [`test_smoke.py`](./test_smoke.py) | Fastest safety net: script compiles, module loads, minimal JSONC normalization cases. |
| Sanity | [`test_sanity.py`](./test_sanity.py) | Deepest minimal invariants: constants, example config, generated block validity. |
| Unit | [`test_unit.py`](./test_unit.py) | Pure-function tests with mocks: `jsonc_to_json`, `read_config_models`, `build_block`, `fetch_free_ids`, `main` flows. |
| Regression | [`test_regression.py`](./test_regression.py) | The 2026-11-24 JSONC validation bug and its fix; apply idempotency. |
| Integration | [`test_integration.py`](./test_integration.py) | Component-level pipeline against a local HTTP server (fetch → diff → build → validate → write → read-back). |
| End-to-End (E2E) | [`test_e2e.py`](./test_e2e.py) | Real CLI subprocess against an isolated `HOME` + temp `opencode.jsonc` (`--apply` lifecycle). |
| Automated UI | [`test_automated_ui.py`](./test_automated_ui.py) | Terminal UI contract: rendered output, Turkish runtime messages, exit codes. |

## Run

```bash
# All suites (unittest discovery, verbose)
python3 -m unittest discover -s test -p "test_*.py" -v

# Or via the orchestrator (runs all, or one by pattern)
./test/run_all_tests.sh
./test/run_all_tests.sh smoke
./test/run_all_tests.sh unit

# Single suite directly
python3 test/test_smoke.py
python3 test/test_unit.py
```

Requirements: Python ≥ 3.10, standard library only (no third-party packages).

## Conventions

- Tests load the source module via `importlib` from the repository root — the
  file name (`check-opencode-free-models.py`) is not a valid Python identifier.
- Subprocess-based suites point `HOME` at a temporary directory so the real
  `~/.config/opencode/opencode.jsonc` is never touched.
- Live-endpoint-dependent behaviour is covered through local `http.server`
  fakes in the integration suite; unit tests mock `urllib`.
- Runtime output stays Turkish (user-facing); assertions target those messages.
