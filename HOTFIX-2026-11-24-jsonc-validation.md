# HOTFIX — 2026-11-24 — JSONC validation failure

**Scope:** `--apply` against `~/.config/opencode/opencode.jsonc`
**Status:** Fixed and applied. Config is up to date; backups are in place.
**Code:** `check-opencode-free-models.py` (repository source) and
`~/.config/opencode/check-free-models.py` (the installed copy that is run)

---

## 1. Symptom

```
$ python3 check-free-models.py --apply
canlı ücretsiz sohbet modeli: 10
config'deki model           : 11
eklenecek : -
kaldırılacak: ['longcat-2.5-free']
HATA: üretilen içerik geçersiz JSON (Expecting property name enclosed in double quotes: line 149 column 7 (char 5331)).
Config değiştirilmedi. Yedek: /Users/MahirFatih/.config/opencode/opencode.jsonc.bak-2026-11-24-10_47_42
```

Drift detection (`added` / `removed`) worked correctly and the backup had already
been taken. Only the **validation step before the write** failed, so the config
file was never touched.

## 2. Root cause

The target file is named `opencode.jsonc` — i.e. **JSONC** (JSON + comments).
The `mcp.sage` block in that file contains two comment lines:

```jsonc
"sage": {
  "type": "local",
  "enabled": true,
  // --project-root . resolves to the session's working directory, so every
  // project gets its own isolated SAGE store under <project>/.wrongstack/memories.
  "command": [ ... ]
}
```

The script validated the generated text with:

```python
json.loads(new_text)   # strict JSON parser
```

`json.loads` does not accept comments. Because the models block was shortened by
one line in the generated text, original line 150 became **line 149** in that
text; the error occurred exactly at the `//` starting the comment (column 7,
character 5331).

In short: **the bug was in the validator, not in the config.** The config was
valid JSONC; the tool mistook it for strict JSON and handed it to a strict parser.
Finding/replacing the block with regex and taking the backup both worked — only
the final gate was wrong.

## 3. What was needed

The `--apply` flow's "validate first, write second" safety had to stay in place:
writing malformed content could irreversibly break the OpenCode config. So
**removing validation was not an option** — the validator had to understand
JSONC.

Options considered:

| Option | Verdict | Reason |
|---|---|---|
| Delete the comments from the config | ❌ | Edits the user's file, does not remove the root cause, and fails again on any other JSONC config. |
| Add an external `jsonc` / `commentjson` package | ❌ | The project deliberately has **zero dependencies** (`dependencies = []`) and supports Python ≥3.10. A new package for one validation step is unnecessary. |
| Normalize JSONC to strict JSON locally before validation | ✅ | No dependencies, the bytes written to disk are unchanged, the validate-before-write guarantee is preserved, and a pure function is easy to test. |

## 4. Why this fix

`jsonc_to_json()` was added to `check-opencode-free-models.py`, and validation now
reads:

```python
json.loads(jsonc_to_json(new_text))
```

What the function does:

- Drops `//` line comments up to end of line, **preserving line structure** so
  line numbers in error messages stay meaningful.
- Removes `/* ... */` block comments.
- Never enters string literals: it tracks escape characters (`\"`, `\\`), so
  URLs such as `"http://x/*y*/"` are left intact.
- Removes trailing commas before a closing `}` / `]`.
- Used **for validation only** — the original JSONC text (with its comments) is
  still what gets written to disk.

This fixes the problem at the right layer: the read/write logic and the config
format are untouched; only the data fed to the strict parser is normalized. A
full JSONC parser was unnecessary — OpenCode config keys are quoted, so stripping
comments and trailing commas is sufficient.

## 5. Verification

1. **Existing config:** `json.loads(jsonc_to_json(config))` succeeded — 4 providers read.
2. **Generated content (not written):** the models block was replaced, validated,
   and `n == 1`.
3. **Edge case:** `{"url": "http://x/*y*/", "a": [1, 2,], // comment\n /* block */ "b": "}"}`
   → comment-like characters inside the string were preserved, the trailing comma
   was removed, and the `json.loads` equality check passed.
4. **Live `--apply`:**

```
kaldırılacak: ['longcat-2.5-free']
UYGULANDI. Yedek: /Users/MahirFatih/.config/opencode/opencode.jsonc.bak-2026-11-24-11_02_14
  - longcat-2.5-free
```

5. **Second dry run:** `SONUÇ: güncel, fark yok.` / `exit=0`.
   The comment lines are still in the file and `longcat-2.5-free` is gone.

## 6. Notes

- The first failed attempt also created a backup
  (`opencode.jsonc.bak-2026-11-24-10_47_42`). Since the config was never changed,
  that backup can be deleted safely; it is harmless.
- The repository file and `~/.config/opencode/check-free-models.py` differ only in
  the usage examples inside the docstring (the file name); the fix itself is
  identical in both.
- The change is not committed yet (`git status`: `M check-opencode-free-models.py`).
