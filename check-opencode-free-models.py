#!/usr/bin/env python3
"""Compare OpenCode Console's free models against the live endpoint.

Usage:
    python3 check-opencode-free-models.py            # report drift (exit 1 if drift is found)
    python3 check-opencode-free-models.py --apply    # update opencode.jsonc (with a backup)

Source: https://opencode.ai/inference/v1/models  (no auth; cost==0 => free)
Config: ~/.config/opencode/opencode.jsonc  (provider.opencode-api.models)
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
import tempfile
import time
import urllib.request

VERSION = "1.0.4"
CONFIG = os.path.expanduser(os.environ.get("OPENCODE_CONFIG_PATH", "~/.config/opencode/opencode.jsonc"))
ENDPOINT = os.environ.get("OPENCODE_MODELS_URL", "https://opencode.ai/inference/v1/models")
PROVIDER = "opencode-api"
# The systemone endpoint (opencode.ai/inference/systemone/v1) returns 404 and
# the opencode-jev provider was removed from the config; the free Jev model is no
# longer tracked. (Jev decisions run through the MCP server / TypeSafe API.)
EXTRA_FREE = set()


SKIPPED_FREE_MODELS: list[tuple[str, str]] = []


def fetch_free_ids() -> list[tuple[str, str]]:
    req = urllib.request.Request(ENDPOINT, headers={"User-Agent": "curl/8.0"})
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=30) as response:  # nosemgrep: python.lang.security.audit.dynamic-urllib-use-detected.dynamic-urllib-use-detected (ENDPOINT is a module-level constant, not user input)
                data = json.load(response)["data"]
            break
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError) as exc:
            last_error = exc
            if attempt < 2:
                time.sleep(0.5 * (attempt + 1))
    else:
        raise RuntimeError(f"could not fetch models from {ENDPOINT}: {last_error}")

    out = []
    skipped: list[tuple[str, str]] = []
    for model in data:
        # Only chat models belong in the opencode-api block.
        # Decision models (e.g. Jev, type=decision) run through the systemone
        # endpoint and are kept in the opencode-jev block.
        cost_text = (model.get("cost") or {}).get("text") or {}
        input_price = (cost_text.get("input") or {}).get("price")
        output_price = (cost_text.get("output") or {}).get("price")
        if input_price != 0 or output_price != 0:
            continue
        # Free model: keep chat ones, warn about the rest (e.g. type=decision).
        if (model.get("type") or "chat").lower() != "chat":
            skipped.append((model["id"], model.get("name") or model["id"]))
            continue
        out.append((model["id"], model.get("name") or model["id"]))
    SKIPPED_FREE_MODELS[:] = skipped
    return out


def jsonc_to_json(text: str) -> str:
    """Convert JSONC text to strict JSON (for validation only, never for writing).

    opencode.jsonc is a JSONC file: it may contain // and /* */ comments as well
    as trailing commas. Since ``json.loads`` rejects those, this removes comments
    and trailing commas — without touching anything inside string literals —
    before the generated content is validated.
    """
    out: list[str] = []
    i = 0
    n = len(text)
    in_string = False
    escaped = False

    while i < n:
        ch = text[i]

        if in_string:
            out.append(ch)
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
            i += 1
            continue

        if ch == '"':
            in_string = True
            out.append(ch)
            i += 1
        elif ch == "/" and i + 1 < n and text[i + 1] == "/":
            # // comment: skip to end of line, keep the line structure.
            i += 2
            while i < n and text[i] not in "\r\n":
                i += 1
            out.append("\n")
        elif ch == "/" and i + 1 < n and text[i + 1] == "*":
            # /* */ comment: skip to the closing delimiter.
            i += 2
            while i + 1 < n and not (text[i] == "*" and text[i + 1] == "/"):
                i += 1
            i += 2
            out.append(" ")
        elif ch in "}]":
            # Trailing comma: drop the last comma before the closing bracket.
            j = len(out) - 1
            while j >= 0 and out[j].isspace():
                j -= 1
            if j >= 0 and out[j] == ",":
                del out[j:]
            out.append(ch)
            i += 1
        else:
            out.append(ch)
            i += 1

    return "".join(out)


def read_config_models(text: str) -> dict[str, str]:
    """Return the id -> name map from the opencode-api provider's models block."""
    found = re.search(
        r'"' + PROVIDER + r'"\s*:\s*\{.*?"models"\s*:\s*\{(.*?)\n\s*\}',
        text,
        re.S,
    )
    if not found:
        sys.exit(f"ERROR: {PROVIDER} models block not found.")
    block = found.group(1)
    # Entries may be one-line (`"id": { "name": "X" },`) or multi-line (the shape
    # of the example config). \s* spans newlines, so one regex covers both.
    out = dict(re.findall(r'\s*"([^"]+)"\s*:\s*\{\s*"name"\s*:\s*"([^"]*)"', block, re.S))
    return out


def build_block(free: list[tuple[str, str]], names: dict[str, str]) -> str:
    lines = []
    for mid, live_name in free:
        name = names.get(mid, live_name)  # keep the existing name, fall back to the live one
        lines.append(f'        "{mid}": {{ "name": "{name}" }}')
    return ",\n".join(lines)  # JSON members must be comma-separated (no trailing comma)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="update config")
    ap.add_argument("--dry-run", action="store_true", help="report drift without making changes (default)")
    ap.add_argument("--config", metavar="PATH", help="path to opencode.jsonc (overrides OPENCODE_CONFIG_PATH)")
    ap.add_argument("--version", action="version", version=f"%(prog)s {VERSION}")
    args = ap.parse_args()

    # --dry-run wins over --apply: never write when explicitly requested.
    if args.dry_run:
        args.apply = False

    # --config overrides the env/default config path.
    global CONFIG
    if args.config:
        CONFIG = os.path.expanduser(args.config)

    try:
        free = fetch_free_ids()
    except RuntimeError as exc:
        sys.exit(f"ERROR: {exc}")
    free_ids = [mid for mid, _ in free]

    text = open(CONFIG, encoding="utf-8").read()
    current = read_config_models(text)
    cur_ids = list(current)

    added = [i for i in free_ids if i not in current]
    removed = [i for i in cur_ids if i not in free_ids]

    print(f"live free chat models: {len(free_ids)}")
    print(f"config models            : {len(cur_ids)}")
    print(f"to add     : {added or '-'}")
    print(f"to remove  : {removed or '-'}")

    missing_extra = [m for m in EXTRA_FREE if m not in text]
    if missing_extra:
        print(f"WARNING: missing systemone free model: {missing_extra}")

    skipped_free = list(SKIPPED_FREE_MODELS)
    if skipped_free:
        print(f"WARNING: non-chat free model skipped: {skipped_free}")

    if not added and not removed and not missing_extra:
        print("RESULT: in sync, no drift.")
        return 0

    if not args.apply:
        print("RESULT: drift found. Update with --apply.")
        return 1

    bak = f"{CONFIG}.bak-{time.strftime('%Y-%m-%d-%H_%M_%S')}"
    shutil.copy2(CONFIG, bak)

    new_block = build_block(free, current)
    pattern = re.compile(
        r'("' + PROVIDER + r'"\s*:\s*\{.*?"models"\s*:\s*\{)(.*?)(\n\s*\})', re.S
    )
    new_text, n = pattern.subn(lambda m: m.group(1) + "\n" + new_block + m.group(3), text, count=1)
    if n != 1:
        sys.exit("ERROR: models block could not be updated.")

    # Validate first, write second: never touch the config if the result is invalid.
    # The config is JSONC (comments / trailing commas), so convert it to strict
    # JSON for validation; the file on disk keeps its original JSONC text.
    try:
        json.loads(jsonc_to_json(new_text))
    except json.JSONDecodeError as e:
        sys.exit(
            f"ERROR: generated content is invalid JSON ({e}).\n"
            f"Config unchanged. Backup: {bak}"
        )

    # Atomic write: write to a temp file in the same directory, then os.replace.
    # This avoids a partially-written config if the process is interrupted.
    tmp_fd, tmp_path = tempfile.mkstemp(
        prefix=".opencode.jsonc.", dir=os.path.dirname(os.path.abspath(CONFIG))
    )
    try:
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
            f.write(new_text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, CONFIG)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise

    print(f"APPLIED. Backup: {bak}")
    for mid in added:
        print(f"  + {mid}")
    for mid in removed:
        print(f"  - {mid}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
