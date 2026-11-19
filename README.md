# check-opencode-free-models

OpenCode Console (`https://opencode.ai/inference/v1/models`) üzerinden, OpenCode
ücretsiz **chat** modellerini `~/.config/opencode/opencode.jsonc` ile **sync eden**
küçük bir araç.

## Nasıl çalışır

1. **Fetch:** `fetch_free_ids()` kaynak endpoint (`opencode.ai/inference/v1/models`,
   auth gerekmez) dan her modeli okur. Filtre: `cost.text.input.price == 0 &&
   cost.text.output.price == 0` ve `type == "chat"`.
   - Karar modelleri (`type: decision`, örneğin Jev `jev-1.13-free`) chat değil
     (`recommended_api: systemone`), bu yüzden `opencode-api` bloğuna yazılmaz.
2. **Drift:** `read_config_models()` → `provider.opencode-api.models` bloğundaki
   `id -> name` sözlüğünü okur. Canlı listedeki ücretsiz modellerle
   ayırımlar: eklenecek (`added`), kaldırılacak (`removed`).
3. **Apply:** `--apply` ile:
   - Yedeği `opencode.jsonc.bak-YYYY-MM-DD-HH_MM_SS`
     (`shutil.copy2`, metadata korunur) alır.
   - `build_block()` → her satır `        "id": { "name": "name" },` virgüllü
     satırlar; doğru virgüllere sahip yanlış satır üretmeyi engellemek için
     satırları aralarında virgül koyup yazdırır.
   - `pattern.subn` ile `opencode-api`'nin models bloğunu değiştirir.
   - **Validate-before-write:** değişmiş metni `json.loads(new_text)` ile
     **yazdırmadan önce** doğrular — geçersiz olursa config'e hiç dokunmaz.

İdempotent: tekrar `--apply` çalıştırınca drift yok.

## Kullanım

```
python3 check-free-models.py            # drift raporu (exit 0: güncel, 1: drift var)
python3 check-free-models.py --apply    # yedeği alarak güncelle
```

Örnek çıktı:

```
canlı ücretsiz sohbet modeli: 11
config'deki model           : 11
eklenecek : -
kaldırılacak: -
SONUÇ: güncel, fark yok.
```

## OpenCode Desktop ve Crontab

Bu araç **OpenCode Desktop'ın** kendi `~/.config/opencode/opencode.jsonc`
yapılandırmasını hedefler — başka bir config dosyasına dokunmaz.

`--apply` ile config'i otomatik güncelleyebilirsin, veya sadece drift
kontrolü için günlük bir crontab satırı ekleyebilirsin:

```
0 6 * * * /Users/MahirFatih/Sites/check-opencode-free-models/check-free-models.py
```

Drift olursa çıkış kodu 1 olur (`SONUÇ: drift var. --apply ile güncelle.`);
config güncel olduğunda 0 (`SONUÇ: güncel, fark yok.`).

## Dosyalar

| Dosya | Açıklama |
|---|---|
| `check-free-models.py` | Çalışan script (canlı uç, drift, apply + yedek). |
| `README.md` | Bu dosya. |

## Değerlendirme / ileride öneriler

1. **Atomic write** — geçerlik kontrolü yaptıktan sonra `tempfile` + `os.replace`
   (sistem call) kullan. Disk hata için geçici-durumla bozuk yazımı engellenir.
2. **Robust `type` filtresi** — `m.get("type") or "chat"` (olmayan type'da default
   chat) yapmak; daha yeni model formatı değişince silinmemiş chat modeli olur.
3. **Decision-modelleri WARN** — skip etmek yerine raporda
   `type=decision (systemone) models ignored: jev-1.13-free` gibi bir bilgi satırı
   ver: geçmişteki "açık-amamın" durumu (`jev-1.13-free`
   `opencode-api`'ye yazılıp 429 alma vakası) tekrarlanmasın.
4. **Unit tests** — `ENDPOINT` ve `CONFIG` module-level constantleri aslında
   env var'a dönebilir (`OPENCODE_MODELS_URL`, `OPENCODE_CONFIG_PATH`) ve endpoint
   `urllib` mock'lanabilir.
5. **`--dry-run` aliasi** — mevcut durumu 1 kez daha serbestçe içfakırlayabilir.
6. **`recommended_api` routing** — `api.recommended_api == "systemone"` model bir
   `opencode-jev` provider'ına kodlayasım, ama OpenCode'daki systemone/v1
   endpoint'i 404 dönüyor (denetimde). Jev kararları MCP server
   (`github:codaaiteam/jev-mcp`, TypeSafe API `api.typesafe.ai`) üzerinde
   çalışıyor — o kelimeye çıkışın rehberi `jev_gate`/`jev_check` MCP tool'ları.
