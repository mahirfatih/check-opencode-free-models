# Documentation

A map of the documents in this repository. The top-level
[`README.md`](../README.md) is the quick tour (English); the Turkish tour is
[`README.tr.md`](../README.tr.md).

Everything here is written in **English**. The Turkish quick tour is
[`README.tr.md`](../README.tr.md) at the repository root.

## Start here

- [`../README.md`](../README.md) — install, usage, parameters.
- [`../README.tr.md`](../README.tr.md) — the same tour in Turkish.

## Reference — what the tool relies on

- OpenCode Console endpoint: `https://opencode.ai/inference/v1/models`
  (no auth; `cost.text.input.price == 0 && cost.text.output.price == 0` and
  `type == "chat"`).
- Target config: `~/.config/opencode/opencode.jsonc`,
  `provider.opencode-api.models`.

## Guides — how do I work on it

- [`../CONTRIBUTING.md`](../CONTRIBUTING.md) — development setup and checks.
- [`../CHANGELOG.md`](../CHANGELOG.md) — release history.
