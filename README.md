# check-opencode-free-models

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
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
python3 check-free-models.py            # drift report (exit 0: in sync, 1: drift)
python3 check-free-models.py --apply    # update, with backup
```

Example output:

```
canlı ücretsiz sohbet modeli: 11
config'deki model           : 11
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
0 6 * * * /Users/MahirFatih/Sites/check-opencode-free-models/check-free-models.py
```

Exit code `1` on drift (`SONUÇ: drift var. --apply ile güncelle.`), `0` when
in sync (`SONUÇ: güncel, fark yok.`).

## Files

| File | Description |
|---|---|
| `check-free-models.py` | Working script (live endpoint, drift, apply + backup). |
| `README.md` | This file (English). |
| `README.tr.md` | Turkish tour. |
| `CHANGELOG.md` | Release history. |
| `CONTRIBUTING.md` | Development setup and checks. |
| `LICENSE` | MIT. |

## Project structure

```
check-opencode-free-models/
├── check-free-models.py
├── README.md
├── README.tr.md
├── CHANGELOG.md
├── CONTRIBUTING.md
├── LICENSE
├── .gitignore
└── docs/
    └── README.md
```

## Testing & CI

There is no automated test suite yet. Before a change:

- `python3 -m py_compile check-free-models.py` — syntax.
- `python3 check-free-models.py` — drift report (exit `0` when in sync).

## Documentation

- [`README.tr.md`](./README.tr.md) — Turkish tour.
- [`docs/README.md`](./docs/README.md) — documentation map.
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
