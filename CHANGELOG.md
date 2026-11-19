# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.2]

### Changed

- Removed hardcoded local path from the crontab example in READMEs.

## [1.0.1]


### Added

- `opencode-free-models.config.example.jsonc`: shape of the `opencode-api`
  block (redacted, no secrets).
- "What gets pulled from where" documentation in `README.md` / `README.tr.md`.

### Changed

- Re-published (GitHub release + PyPI) with the complete file set.

## [1.0.0]

### Added

- `check-opencode-free-models.py`: compares the free **chat** models published by the
  OpenCode Console (`https://opencode.ai/inference/v1/models`, no auth) against
  the `provider.opencode-api.models` block of `~/.config/opencode/opencode.jsonc`.
- Drift report: lists models to add (`added`) and to remove (`removed`); exits
  `0` when in sync, `1` when drift is found.
- `--apply`: rewrites the `opencode-api` models block in place, taking a
  timestamped backup `opencode.jsonc.bak-YYYY-MM-DD-HH_MM_SS` (`shutil.copy2`,
  metadata preserved).
- Validate-before-write: the rewritten text is parsed with `json.loads` before
  the file is touched; on failure the config is left untouched.
- Filters: only `type == "chat"` models with `cost.text.input.price == 0` and
  `cost.text.output.price == 0`. Decision models (`type: decision`, e.g. Jev
  `jev-1.13-free`) are excluded from the `opencode-api` block.
- `opencode-free-models.config.example.jsonc`: shape of the `opencode-api`
  block (redacted, no secrets).
- `EXTRA_FREE` emptied; `jev-1.13-free` removed from `opencode-api`.
