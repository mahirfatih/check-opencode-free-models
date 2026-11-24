# Security

## How to report a security issue

This project is a small tool that keeps the free **chat** models published by
the OpenCode Console (`https://opencode.ai/inference/v1/models`, no auth) in
sync with the `provider.opencode-api.models` block in
`~/.config/opencode/opencode.jsonc`. A security report covers both a
vulnerability in the tool and the security of the configured file.

Report via [GitHub Issues](https://github.com/mahirfatih/check-opencode-free-models/issues).
Please include how to reproduce the issue and any evidence you have.

## Supported versions

The tool's behavior is defined by the `version` field in `pyproject.toml`;
security fixes are applied to the current release.

## Security policy

The tool acts on the user's own files:

- **Read:** `~/.config/opencode/opencode.jsonc` (the live endpoint and the
  existing config).
- **Write (only with `--apply`):** only the `opencode-api.models` block is
  rewritten. Without `--apply`, no file is written.
- **Backup:** before writing with `--apply`, a timestamped
  `opencode.jsonc.bak-YYYY-MM-DD-HH_MM_SS` is created (`shutil.copy2`,
  metadata preserved).
- **Validate-before-write:** the rewritten text is checked with `json.loads`
  before the file is touched; on failure the file is left unchanged.

## Reporting process

- Prefer short, reproducible reports (steps, inputs, observed vs expected).
- Do not include private or environment-specific data in reports.
- If a fix is made in response, the related issue is updated with the change
  and any PR/commit that fixes it.
