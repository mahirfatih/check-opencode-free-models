# Check Opencode Free Models

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![MCP](https://img.shields.io/badge/MCP-stdio-lightgrey)
![Client](https://img.shields.io/badge/client-OpenCode-green)
[![PyPI](https://img.shields.io/pypi/v/check-opencode-free-models)](https://pypi.org/project/check-opencode-free-models/)
![License](https://img.shields.io/badge/license-MIT-blue)

🌐 **English** · [Türkçe](./README.tr.md)

**check-opencode-free-models** is a tiny tool that keeps the free **chat**
models published by the OpenCode Console in sync with
`~/.config/opencode/opencode.jsonc`.

It fetches `https://opencode.ai/inference/v1/models` (no auth), filters free
chat models, compares them against `provider.opencode-api.models`, reports drift
(`added` / `removed`), and — with `--apply` — rewrites the block in place
after taking a timestamped backup.

## Source & references

- Free models documentation: https://opencode.ai/docs/models/#free-models
- OpenCode Desktop: https://opencode.ai/desktop
- Live endpoint used by the script: `https://opencode.ai/inference/v1/models`
  (no auth; `cost.text.input.price == 0 && cost.text.output.price == 0` and
  `type == "chat"`).

## What gets pulled from where

| Source | What | Target |
|---|---|---|
| `https://opencode.ai/inference/v1/models` (no auth) | Free chat models (`type == "chat"`, `cost.text.input/output.price == 0`) — `id` + `name` | `~/.config/opencode/opencode.jsonc` → `provider.opencode-api.models` |
| Existing config | Preserves already-stored `name` values on update | merged into the rewritten block |
| `--apply` | Rewrites the block; backup `opencode.jsonc.bak-YYYY-MM-DD-HH_MM_SS` | same file |

Nothing else is read or written. The example config
`opencode-free-models.config.example.jsonc` shows the shape of the `opencode-api`
block (redacted, no secrets).

## Current free chat models

As of 2026-11-24, the Console lists 10 free chat models (run the script
to refresh):

- `beam-free` — Beam Free
- `big-pickle` — Big Pickle
- `deepseek-v4.1-flash-free` — DeepSeek V4.1 Flash Free
- `flint-40b-free` — Flint 40B Free
- `hy4-flash-free` — Hy4 flash Free
- `iceman-free` — Iceman Free
- `mimo-v2.6-flash-free` — MiMo-V2.6-Flash Free
- `nemotron-3.5-lightning-free` — Nemotron 3.5 Lightning Free
- `nemotron-3.5-super-vl-free` — Nemotron 3.5 Super VL Free
- `tidepool-alpha-free` — Tidepool Alpha Free

## How it works

1. **Fetch** — `fetch_free_ids()` reads every model from the source endpoint.
   Filter: `cost.text.input.price == 0 && cost.text.output.price == 0` and
   `type == "chat"`.
   - Decision models (`type: decision`, e.g. Jev `jev-1.13-free`) are not chat
     (`recommended_api: systemone`), so they are never written to the
     `opencode-api` block.
2. **Drift** — `read_config_models()` reads the `id -> name` map from
   `provider.opencode-api.models`. Diff against the live free list: `added`,
   `removed`.
3. **Apply** — with `--apply`:
   - Backup `opencode.jsonc.bak-YYYY-MM-DD-HH_MM_SS` (`shutil.copy2`,
     metadata preserved).
   - `build_block()` joins lines with commas (no trailing comma).
   - `pattern.subn` rewrites the `opencode-api` models block.
   - **Validate-before-write**: the rewritten text is parsed with
     `json.loads(new_text)` *before* the file is touched; on failure the config
     is left untouched.

Idempotent: re-running `--apply` reports no drift.

## Usage

```
python3 check-opencode-free-models.py            # drift report (exit 0: in sync, 1: drift)
python3 check-opencode-free-models.py --apply    # update, with backup
```

Example output:

```
canlı ücretsiz sohbet modeli: 10
config'deki model           : 10
eklenecek : -
kaldırılacak: -
SONUÇ: güncel, fark yok.
```

## OpenCode Desktop and crontab

This tool targets **OpenCode Desktop's** own
`~/.config/opencode/opencode.jsonc` — it never touches any other config file.

Apply updates automatically with `--apply`, or run a daily drift check from
crontab:

```
0 6 * * * /path/to/check-opencode-free-models/check-opencode-free-models.py
```

Exit code `1` on drift (`SONUÇ: drift var. --apply ile güncelle.`), `0` when
in sync (`SONUÇ: güncel, fark yok.`).

## Files

| File | Description |
|---|---|
| `check-opencode-free-models.py` | Working script (live endpoint, drift, apply + backup). |
| `opencode-free-models.config.example.jsonc` | Example `opencode-api` block (redacted, no secrets). |
| `README.md` | This file (English). |
| `README.tr.md` | Turkish tour. |
| `CHANGELOG.md` | Release history. |
| `CONTRIBUTING.md` | Development setup and checks. |
| `LICENSE` | MIT. |
| [`test/`](./test/) | Automated test suites (smoke / sanity / unit / regression / integration / e2e / ui) + [`test/README.md`](./test/README.md). |
| [`docs/testing/TESTING.md`](./docs/testing/TESTING.md) | Testing guide for the automated suites. |

## Project structure

```
check-opencode-free-models/
├── check-opencode-free-models.py
├── opencode-free-models.config.example.jsonc
├── README.md
├── README.tr.md
├── CHANGELOG.md
├── CONTRIBUTING.md
├── LICENSE
├── .gitignore
├── test/
│   ├── test_smoke.py
│   ├── test_sanity.py
│   ├── test_unit.py
│   ├── test_regression.py
│   ├── test_integration.py
│   ├── test_e2e.py
│   ├── test_automated_ui.py
│   ├── README.md
│   └── run_all_tests.sh
└── docs/
    ├── README.md
    └── testing/
        └── TESTING.md
```

## Testing & CI

The repository ships a standard-library-only automated test suite under
[`test/`](./test/):

```bash
python3 -m unittest discover -s test -p "test_*.py" -v
```

| Suite | File | Focus |
|---|---|---|
| Smoke | [`test/test_smoke.py`](./test/test_smoke.py) | Script compiles, module loads, minimal JSONC handling. |
| Sanity | [`test/test_sanity.py`](./test/test_sanity.py) | Constants, example config, generated block validity. |
| Unit | [`test/test_unit.py`](./test/test_unit.py) | Pure functions with mocks (`jsonc_to_json`, `read_config_models`, `build_block`, `fetch_free_ids`, `main`). |
| Regression | [`test/test_regression.py`](./test/test_regression.py) | JSONC validation bug (2026-11-24) and apply idempotency. |
| Integration | [`test/test_integration.py`](./test/test_integration.py) | Local HTTP server + full fetch→diff→build→validate→write→read-back pipeline. |
| End-to-End (E2E) | [`test/test_e2e.py`](./test/test_e2e.py) | Real CLI subprocess, isolated `HOME`, full `--apply` lifecycle. |
| Automated UI | [`test/test_automated_ui.py`](./test/test_automated_ui.py) | Terminal output, user-facing messages, exit codes. |

Before a change:

- `python3 -m py_compile check-opencode-free-models.py` — syntax.
- `python3 check-opencode-free-models.py` — drift report (exit `0` when in sync).
- `python3 -m unittest discover -s test -p "test_*.py" -v` — full test suite.

## Documentation

- [`README.tr.md`](./README.tr.md) — Turkish tour.
- [`docs/README.md`](./docs/README.md) — documentation map.
- [`docs/testing/TESTING.md`](./docs/testing/TESTING.md) — testing guide.
- [`CHANGELOG.md`](./CHANGELOG.md) — release history.
- [`CONTRIBUTING.md`](./CONTRIBUTING.md) — development setup.

## Future ideas

1. **Atomic write** — `tempfile` + `os.replace` after validation.
2. **Robust `type` filter** — `m.get("type") or "chat"`.
3. **Decision-model WARN** — report skipped `type=decision` models.
4. **Unit tests** — make `ENDPOINT`/`CONFIG` env-overridable and mock `urllib`.
5. **`--dry-run` alias**.
6. **`recommended_api` routing** — systemone endpoint is currently 404.

## License

MIT — see [`LICENSE`](./LICENSE).
