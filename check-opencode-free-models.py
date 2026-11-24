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
import time
import urllib.request

CONFIG = os.path.expanduser("~/.config/opencode/opencode.jsonc")
ENDPOINT = "https://opencode.ai/inference/v1/models"
PROVIDER = "opencode-api"
# The systemone endpoint (opencode.ai/inference/systemone/v1) returns 404 and
# the opencode-jev provider was removed from the config; the free Jev model is no
# longer tracked. (Jev decisions run through the MCP server / TypeSafe API.)
EXTRA_FREE = set()


def fetch_free_ids() -> list[tuple[str, str]]:
    req = urllib.request.Request(ENDPOINT, headers={"User-Agent": "curl/8.0"})
    with urllib.request.urlopen(req, timeout=30) as response:
        data = json.load(response)["data"]
    out = []
    for model in data:
        # Only chat models belong in the opencode-api block.
        # Decision models (e.g. Jev, type=decision) run through the systemone
        # endpoint and are kept in the opencode-jev block.
        if (model.get("type") or "").lower() != "chat":
            continue
        cost_text = (model.get("cost") or {}).get("text") or {}
        input_price = (cost_text.get("input") or {}).get("price")
        output_price = (cost_text.get("output") or {}).get("price")
        if input_price == 0 and output_price == 0:
            out.append((model["id"], model.get("name") or model["id"]))
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
        sys.exit(f"HATA: {PROVIDER} models bloğu bulunamadı.")
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
    ap.add_argument("--apply", action="store_true", help="config'i güncelle")
    args = ap.parse_args()

    free = fetch_free_ids()
    free_ids = [mid for mid, _ in free]

    text = open(CONFIG, encoding="utf-8").read()
    current = read_config_models(text)
    cur_ids = list(current)

    added = [i for i in free_ids if i not in current]
    removed = [i for i in cur_ids if i not in free_ids]

    print(f"canlı ücretsiz sohbet modeli: {len(free_ids)}")
    print(f"config'deki model           : {len(cur_ids)}")
    print(f"eklenecek : {added or '-'}")
    print(f"kaldırılacak: {removed or '-'}")

    missing_extra = [m for m in EXTRA_FREE if m not in text]
    if missing_extra:
        print(f"UYARI: systemone ücretsiz modeli eksik: {missing_extra}")

    if not added and not removed and not missing_extra:
        print("SONUÇ: güncel, fark yok.")
        return 0

    if not args.apply:
        print("SONUÇ: drift var. --apply ile güncelle.")
        return 1

    bak = f"{CONFIG}.bak-{time.strftime('%Y-%m-%d-%H_%M_%S')}"
    shutil.copy2(CONFIG, bak)

    new_block = build_block(free, current)
    pattern = re.compile(
        r'("' + PROVIDER + r'"\s*:\s*\{.*?"models"\s*:\s*\{)(.*?)(\n\s*\})', re.S
    )
    new_text, n = pattern.subn(lambda m: m.group(1) + "\n" + new_block + m.group(3), text, count=1)
    if n != 1:
        sys.exit("HATA: models bloğu değiştirilemedi.")

    # Validate first, write second: never touch the config if the result is invalid.
    # The config is JSONC (comments / trailing commas), so convert it to strict
    # JSON for validation; the file on disk keeps its original JSONC text.
    try:
        json.loads(jsonc_to_json(new_text))
    except json.JSONDecodeError as e:
        sys.exit(
            f"HATA: üretilen içerik geçersiz JSON ({e}).\n"
            f"Config değiştirilmedi. Yedek: {bak}"
        )

    with open(CONFIG, "w", encoding="utf-8") as f:
        f.write(new_text)

    print(f"UYGULANDI. Yedek: {bak}")
    for mid in added:
        print(f"  + {mid}")
    for mid in removed:
        print(f"  - {mid}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
