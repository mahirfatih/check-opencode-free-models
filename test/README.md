# Tests — check-opencode-free-models

This folder contains the automated test suites for
[`check-opencode-free-models.py`](../check-opencode-free-models.py).

## Suites

| Suite | File | Purpose |
|---|---|---|
| Smoke | [`test-smoke.py`](./test-smoke.py) | Fastest safety net: script compiles, module loads, minimal JSONC normalization cases. |
| Sanity | [`test-sanity.py`](./test-sanity.py) | Deepest minimal invariants: constants, example config, generated block validity. |
| Unit | [`test-unit.py`](./test-unit.py) | Pure-function tests with mocks: `jsonc_to_json`, `read_config_models`, `build_block`, `fetch_free_ids`, `main` flows. |
| Regression | [`test-regression.py`](./test-regression.py) | The 2026-11-24 JSONC validation bug and its fix; apply idempotency. |
| Integration | [`test-integration.py`](./test-integration.py) | Component-level pipeline against a local HTTP server (fetch → diff → build → validate → write → read-back). |
| End-to-End (E2E) | [`test-e2e.py`](./test-e2e.py) | Real CLI subprocess against an isolated `HOME` + temp `opencode.jsonc` (`--apply` lifecycle). |
| Automated UI | [`test-automated-ui.py`](./test-automated-ui.py) | Terminal UI contract: rendered output, Turkish runtime messages, exit codes. |

## Run

```bash
# All suites (stdlib runner; loads kebab-case files by path)
python3 test/run-tests.py

# One suite by name: smoke | sanity | unit | regression | integration | e2e | ui
python3 test/run-tests.py unit

# Shell wrapper (same runner)
./test/run-all-tests.sh
./test/run-all-tests.sh smoke
./test/run-all-tests.sh unit

# Single suite directly
python3 test/test-smoke.py
python3 test/test-unit.py
```

`unittest discover` cannot import hyphenated module names, so `run-tests.py`
uses `importlib.util.spec_from_file_location` instead. No third-party packages
are needed. Requirements: Python ≥ 3.10, standard library only.

## Conventions

- Tests load the source module via `importlib` from the repository root — the
  file name (`check-opencode-free-models.py`) is not a valid Python identifier.
- Suite files use kebab-case (`test-<area>.py`); Python identifiers inside them
  stay snake_case (PEP 8).
- Subprocess-based suites point `HOME` at a temporary directory so the real
  `~/.config/opencode/opencode.jsonc` is never touched.
- Live-endpoint-dependent behaviour is covered through local `http.server`
  fakes in the integration suite; unit tests mock `urllib`.
- Runtime output stays Turkish (user-facing); assertions target those messages.
- Add every new suite to `SUITES` in `run-tests.py` so CI picks it up.

## Details

See [`docs/testing/TESTING.md`](../docs/testing/TESTING.md) for the lifecycle
mapping, conventions and CI wiring.
