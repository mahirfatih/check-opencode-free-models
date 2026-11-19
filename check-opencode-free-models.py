#!/usr/bin/env python3
"""OpenCode Console ücretsiz modellerini canlı endpoint ile karşılaştırır.

Kullanım:
    python3 check-opencode-free-models.py            # farkı raporla (drift varsa exit 1)
    python3 check-opencode-free-models.py --apply    # opencode.jsonc'yi güncelle (yedek alarak)

Kaynak: https://opencode.ai/inference/v1/models  (auth gerekmez; cost==0 => ücretsiz)
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
# systemone endpoint'i (opencode.ai/inference/systemone/v1) 404 dönüyor ve
# opencode-jev provider'ı config'den kaldırıldı; ücretsiz jev modeli artık
# takip edilmiyor. (Jev kararları MCP server üzerinden TypeSafe API ile çalışır.)
EXTRA_FREE = set()


def fetch_free_ids() -> list[tuple[str, str]]:
    req = urllib.request.Request(ENDPOINT, headers={"User-Agent": "curl/8.0"})
    with urllib.request.urlopen(req, timeout=30) as response:
        data = json.load(response)["data"]
    out = []
    for model in data:
        # Sadece sohbet (chat) modelleri opencode-api bloğuna ait.
        # Karar modelleri (jev gibi, type=decision) systemone endpoint'i
        # üzerinden çalışır ve opencode-jev bloğunda tutulur.
        if (model.get("type") or "").lower() != "chat":
            continue
        cost_text = (model.get("cost") or {}).get("text") or {}
        input_price = (cost_text.get("input") or {}).get("price")
        output_price = (cost_text.get("output") or {}).get("price")
        if input_price == 0 and output_price == 0:
            out.append((model["id"], model.get("name") or model["id"]))
    return out


def read_config_models(text: str) -> dict[str, str]:
    """opencode-api provider'ının models bloğundaki id -> name sözlüğü."""
    found = re.search(
        r'"' + PROVIDER + r'"\s*:\s*\{.*?"models"\s*:\s*\{(.*?)\n\s*\}',
        text,
        re.S,
    )
    if not found:
        sys.exit(f"HATA: {PROVIDER} models bloğu bulunamadı.")
    block = found.group(1)
    out: dict[str, str] = {}
    for line in block.splitlines():
        entry_match = re.match(r'\s*"([^"]+)"\s*:\s*\{\s*"name"\s*:\s*"([^"]*)"', line)
        if entry_match:
            out[entry_match.group(1)] = entry_match.group(2)
    return out


def build_block(free: list[tuple[str, str]], names: dict[str, str]) -> str:
    lines = []
    for mid, live_name in free:
        name = names.get(mid, live_name)  # mevcut isim korunur, yenisi canlıdan
        lines.append(f'        "{mid}": {{ "name": "{name}" }}')
    return ",\n".join(lines)  # JSON üyeleri virgülle ayrılmalı (son satırda virgül yok)


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

    # Önce doğrula, sonra yaz: geçersizse config'e hiç dokunma.
    try:
        json.loads(new_text)
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
