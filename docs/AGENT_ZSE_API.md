# ZSE / InterCapital ETF API — spec za financijskog AI agenta

Ovaj dokument je namijenjen **Claude Sonnet 5** (ili drugom agentu):
ubaci ga u kontekst i integriraj ZSE podatke u postojeće fajlove.
**Ne traži API ključ.** Javni REST radi bez autentikacije.

Provjereno uživo **2026-08-21**. Strojno čitljivi katalog:
`config/zse_instruments.json`.

---

## 0. Zadatak za agenta (copy-paste)

```
Integriraj javni ZSE REST (bez API ključa) u ovaj financijski agent.

Izvor istine:
- docs/AGENT_ZSE_API.md
- config/zse_instruments.json

Obavezno:
1. Ne traži ni ne spremaj API key / OAuth / Bearer token.
2. Dohvaćaj OHLCV sa:
   GET https://rest.zse.hr/web/Bvt9fe2peQ7pwpyYqODM/security-history/XZAG/{ISIN}/{from}/{to}/json?language=EN
3. Koristi JSON (`fmt=json`), ne CSV, osim ako korisnik eksplicitno hoće CSV.
4. Za graf/prinos filtriraj samo `trading_model_id == "CT"`.
5. Cijene u JSON-u su STRINGOVI — parsiraj u float.
6. HRK retke (price_currency == "HRK", do 2022-12-31) podijeli s 7.53450 da dobiješ EUR.
7. Dok je burza otvorena (prije 18:00 CET) izbaci današnji nezavršeni bar.
8. Podrži sve InterCapital ETF-ove iz kataloga, posebno regionalni mix:
   7POL 34% / 7BET 26% / 7CRO 20% / 7SLO 20% (rizik 9/10, ETF 100% dionice).
9. Novi ticker: isti endpoint, samo novi ISIN. Predložak je u katalogu
   (`new_ticker_template`). 7POL (HRICAMFPWIG3, listing 2026-05-19) je
   najnoviji equity ETF u mixu.
10. 7CRO tracking vs CROBEX10tr: index-history na ZSE, ISIN HRZB00ICB103.
    7SLO tracking vs SBITOP TR: index-history na LJSE
    https://rest.ljse.si/web/Bvt9fe2peQ7pwpyYqODM/index-history/XLJU/SI0028409892/{from}/{to}/json?language=EN
    WIG30TR i BET-TRN NISU na ovom API-ju (GPW / BVB).
11. 7CASH i 7GROM imaju rijetko trgovanje — forward-fill last price, ne
    tretiraj prazan dan kao prinos 0.
12. yfinance (7CRO.ZA) je slab fallback. Primarni izvor je uvijek ZSE REST.

Kad završiš, dodaj male funkcije: fetch_security(), fetch_index(),
normalize_ohlcv(), regional_mix_nav(). Nemoj hardcodirati samo 7CRO.
```

---

## 1. Autentikacija — nema je

| Stavka | Vrijednost |
| --- | --- |
| API key | **nema** |
| Header `Authorization` | **nema** |
| Query `api_key` / `token` | **nema** |
| Cookie / login | **nema** |
| Rate-limit header | nije dokumentiran; 1–N GET-ova dnevno je dovoljno |

Segment `Bvt9fe2peQ7pwpyYqODM` u URL-u je **javni website token** koji ZSE/LJSE
stranica i sama šalje pregledniku. Nije osobni ključ. Ne rotira se po sesiji
(isti je godinama). Ako ikad padne na 401/403, novi `restAPI` URL se vidi u
HTML-u stranice instrumenta (`?restAPI=https://rest.zse.hr/web/...`).

User-Agent nije obavezan. Live GET bez specijalnih headera vraća 200.

---

## 2. Base URL-ovi

```
ZSE  https://rest.zse.hr/web/Bvt9fe2peQ7pwpyYqODM
LJSE https://rest.ljse.si/web/Bvt9fe2peQ7pwpyYqODM
```

MIC:

- Zagreb: `XZAG`
- Ljubljana: `XLJU`

Datumi u pathu: `YYYY-MM-DD`. Format: `json` ili `csv`.
Query: `?language=EN` (ili `HR`).

---

## 3. Endpointi (jedina dva koja trebaš)

### 3.1 Povijest instrumenta (ETF, dionica)

```
GET {base}/security-history/{MIC}/{ISIN}/{date_from}/{date_to}/{fmt}?language=EN
```

Primjer — 7CRO zadnjih ~10 dana, JSON:

```
https://rest.zse.hr/web/Bvt9fe2peQ7pwpyYqODM/security-history/XZAG/HRICAMFCR102/2026-08-11/2026-08-21/json?language=EN
```

CSV (isti raspon):

```
https://rest.zse.hr/web/Bvt9fe2peQ7pwpyYqODM/security-history/XZAG/HRICAMFCR102/2026-08-11/2026-08-21/csv?language=EN
```

Cijela povijest 7CRO (listing 2020-11-17) radi u jednom pozivu (~1000+ redaka).

### 3.2 Povijest indeksa (samo indeksi te burze)

```
GET {base}/index-history/{MIC}/{ISIN}/{date_from}/{date_to}/{fmt}?language=EN
```

CROBEX10tr (benchmark 7CRO):

```
https://rest.zse.hr/web/Bvt9fe2peQ7pwpyYqODM/index-history/XZAG/HRZB00ICB103/2026-08-11/2026-08-21/json?language=EN
```

SBITOP TR (benchmark 7SLO) — **LJSE, ne ZSE**:

```
https://rest.ljse.si/web/Bvt9fe2peQ7pwpyYqODM/index-history/XLJU/SI0028409892/2026-08-11/2026-08-21/json?language=EN
```

### 3.3 Što NE postoji na ovom REST-u

Nema javnog `quote`, `inav`, `orderbook`, `security-info` endpointa na
`rest.zse.hr` (vraćaju 400). Za zadnju cijenu uzmi zadnji CT red iz
`security-history`. Za iNAV vidi HTML stranicu instrumenta na zse.hr
(nije stabilan JSON ugovor).

WIG30TR (GPW) i BET-TRN (BVB) **nisu** na ZSE/LJSE REST-u.

Opcionalni website wrapper (isti podaci, ružniji JSON):

```
https://zse.hr/json/securityHistory/{ISIN}/{from}/{to}/en?restAPI=https://rest.zse.hr/web/Bvt9fe2peQ7pwpyYqODM/
```

Agent neka koristi `rest.zse.hr` izravno.

---

## 4. Katalog InterCapital ETF-ova (ZSE tickeri)

Svi su UCITS, valuta trgovanja EUR, MIC `XZAG`.

| Ticker | ISIN | Ime | Klasa | Listing | HRK povijest |
| --- | --- | --- | --- | --- | --- |
| **7CRO** | `HRICAMFCR102` | CROBEX10tr UCITS ETF | equity HR | 2020-11-17 | da, do 2022-12-31 |
| **7SLO** | `HRICAMFSBI06` | SBITOP TR UCITS ETF | equity SI | 2020-11-17 | da, do 2022-12-31 |
| **7BET** | `HRICAMFBETR5` | BET-TRN UCITS ETF | equity RO | 2023-05-31 | ne |
| **7POL** | `HRICAMFPWIG3` | Poland WIG30TR UCITS ETF | equity PL | **2026-05-19** | ne |
| 7CASH | `HRICAMFEUMM1` | Euro Money Market UCITS ETF | money market | 2023-10-30 | ne |
| 7GROM | `HRICAMFERGB2` | EUR Romania Govt Bond 5-10yr | bond | 2024-06-05 | ne |

**7POL je novi ticker** u regionalnom equity mixu (prvi dan trgovanja 19.5.2026.).

Stranica instrumenta (ISIN u queryju):

```
https://zse.hr/en/papir-311/310?isin={ISIN}
```

ZSE indeksi (isti `index-history` endpoint):

| Symbol | ISIN | Ime |
| --- | --- | --- |
| CBX | `HRZB00ICBEX6` | CROBEX |
| CBX10 | `HRZB00ICBE11` | CROBEX10 |
| C10TR | `HRZB00ICB103` | CROBEX10tr |
| CBXTR | `HRZB00ICBTR6` | CROBEXtr |

Likvidne dionice koje ovaj tracker već uspoređuje:

| Symbol | ISIN |
| --- | --- |
| HT | `HRHT00RA0005` |
| PODR | `HRPODRRA0004` |
| KOEI | `HRKOEIRA0009` |

---

## 5. Regionalni mix (ETF — 100% dionice)

Prikaz za **rizik 9 od 10**. Usluga je dostupna od razine 6.
Alokacija ovisi o razini rizika.

| Ticker | Država | Težina |
| --- | --- | --- |
| 7POL | Poljska | **34%** |
| 7BET | Rumunjska | **26%** |
| 7CRO | Hrvatska | **20%** |
| 7SLO | Slovenija | **20%** |
| | | 100% |

Dnevni prinos porta:

```
r_p,t = 0.34 * r_7POL,t + 0.26 * r_7BET,t + 0.20 * r_7CRO,t + 0.20 * r_7SLO,t
```

gdje je `r_i,t = last_i,t / last_i,t-1 - 1` na CT close u EUR.

Ako jedan ETF nema CT bar taj dan, **forward-fill** zadnji close.
Ne ubacuj 0% prinos samo zato što nije bilo trgovine.

Normalizirani NAV (start = 100 na prvom zajedničkom datumu kad sva četiri
imaju cijenu):

```
NAV_t = 100 * (0.34 * P7POL_t/P7POL_0 + 0.26 * P7BET_t/P7BET_0
             + 0.20 * P7CRO_t/P7CRO_0 + 0.20 * P7SLO_t/P7SLO_0)
```

Zajednički start za sva četiri je **2026-05-19** (listing 7POL).
7CRO/7SLO/7BET imaju dulju povijest — za usporedbu bez Poljske koristi
njihovo vlastito listing razdoblje.

---

## 6. Dodavanje novog InterCapital tickera

Isti API, novi ISIN. Nema novog ključa, nema novog hosta.

1. Nađi ticker na [zse.hr](https://zse.hr) ili [intercapitaletf.hr/etfs](https://intercapitaletf.hr/etfs/).
2. Otvori stranicu instrumenta i prepiši **ISIN** (12 znakova, npr. `HRICAMF....`).
3. Dodaj objekt u `config/zse_instruments.json` → `intercapital_etfs`
   (predložak: `new_ticker_template`).
4. History:

```
{zse_base}/security-history/XZAG/{NOVI_ISIN}/{first_trading_day}/{today}/json?language=EN
```

5. Ako ide u mix, dodaj `{ "symbol": "...", "weight": 0.xx }` u `regional_mix.weights`
   i renormaliziraj težine na 1.0.

Ako ISIN nije poznat, GET na `security-history` s krivim ISIN-om vraća **404**.
Prazan raspon (nema trgovine) vraća **200** s praznim `history` ili CSV headerom
bez redaka — to nije greška.

---

## 7. JSON shema (fmt=json)

Content-Type: `text/json;charset=UTF-8`. HTTP 200.

### security-history

```json
{
  "timestamp": "2026-08-21T15:01:23.751833+02:00",
  "mic": "XZAG",
  "symbol": "7CRO",
  "isin": "HRICAMFCR102",
  "history": [
    {
      "date": "2026-08-20",
      "trading_model_id": "CT",
      "open_price": "40.95",
      "high_price": "40.95",
      "low_price": "40.95",
      "last_price": "40.95",
      "vwap_price": "40.950000000000",
      "change_prev_close_percentage": "-0.12",
      "num_trades": 1,
      "volume": "19.00000",
      "turnover": "778.05",
      "price_currency": "EUR",
      "turnover_currency": "EUR"
    }
  ]
}
```

`history` je silazno po datumu (najnoviji prvi).

**Cijene, volume, turnover, % su stringovi.** `num_trades` je int.
OTC red često ima prazan `open_price`.

`trading_model_id`:

| Kod | Značenje | Za OHLCV graf |
| --- | --- | --- |
| `CT` | Continuous Trading | **DA — koristi** |
| `OTC` | OTC / blok izvan order booka | NE — duplicira datum |
| `BLOCK` | Block trades (dionice) | NE |

### index-history

```json
{
  "timestamp": "2026-08-21T15:01:30.116762+02:00",
  "mic": "XZAG",
  "symbol": "C10TR",
  "isin": "HRZB00ICB103",
  "history": [
    {
      "date": "2026-08-20",
      "open_value": "3391.91",
      "high_value": "3397.91",
      "low_value": "3383.28",
      "last_value": "3392.99",
      "change_prev_close_percentage": "0.07",
      "turnover": "421507.72"
    }
  ]
}
```

Nema `trading_model_id`, volume ni valute. Mapiraj `*_value` → OHLC,
`Volume = 0`.

### CSV (fmt=csv) — samo ako moraš

API CSV: **zarez** separator, **točka** decimal, quoted polja.

```
"mic","symbol","isin","date","trading_model_id","open_price","high_price","low_price","last_price","vwap_price","change_prev_close_percentage","num_trades","volume","turnover","price_currency","turnover_currency"
"XZAG","7CRO","HRICAMFCR102","2026-08-20","CT",40.95,40.95,40.95,40.95,40.950000000000,-0.12,1,19.00000,778.05,"EUR","EUR"
```

Ovaj repo sprema kanonski CSV s `;` i decimalnim zarezom. To je **drugačiji**
format od API odgovora. Ako parsiraš API CSV kao `;`, cijeli red postane jedan
stupac i merge tiho prestane raditi.

---

## 8. Normalizacija (obavezna pravila)

1. **Samo CT** za dnevni close/OHLCV.
2. Sortiraj uzlazno po `date`, dedupe po datumu (`keep=last`).
3. `last_price` = Close. `open/high/low_price` = Open/High/Low. `volume` = Volume.
4. **HRK → EUR** fiksnim tečajem Zakona o euru:

   ```
   HRK_TO_EUR = 7.53450
   EUR_CHANGEOVER = 2023-01-01
   ```

   Ako `price_currency == "HRK"`: podijeli OHLC (i VWAP) s 7.53450.
   Ako `turnover_currency == "HRK"`: podijeli turnover s 7.53450.
   Volume (broj udjela) se **ne** dijeli.

5. 7CRO/7SLO bez konverzije imaju lažni pad ~100 → ~13 na 2023-01-02.
   To nije crash, to je promjena valute.
6. **Nezavršeni dan**: ako je `now.hour < 18` (CET) i postoji red s današnjim
   datumom, baci ga. ZSE REST vraća intraday OHLC dok je sesija otvorena.
7. Rijetko trgovani (7CASH, 7GROM): ne interpoliraj cijenu; forward-fill.
8. Retry: 3 pokušaja, backoff 2s / 4s / 8s. HTTP != 200 ili prazan parse = greška.
   Ne prepisuj stare podatke praznim odgovorom.

Živi brojevi 2026-08-21 (zadnji CT close 2026-08-20, osim 7CASH/7GROM):

| Ticker | Last | Napomena |
| --- | --- | --- |
| 7CRO | 40.95 EUR | |
| 7SLO | 67.45 EUR | |
| 7BET | 31.75 EUR | |
| 7POL | 11.20 EUR | |
| 7CASH | 107.34 EUR | zadnji trade 2026-08-12 |
| 7GROM | 11.14 EUR | zadnji trade 2026-07-27 |
| C10TR | 3392.99 | CROBEX10tr |

---

## 9. Referentni klijent (stdlib, bez ključa)

```python
from __future__ import annotations

import json
import urllib.request
from datetime import date, datetime
from typing import Any

ZSE = "https://rest.zse.hr/web/Bvt9fe2peQ7pwpyYqODM"
LJSE = "https://rest.ljse.si/web/Bvt9fe2peQ7pwpyYqODM"
HRK_TO_EUR = 7.53450
MARKET_CLOSE_HOUR = 18  # CET

def _get_json(url: str, timeout: int = 30) -> dict[str, Any]:
    req = urllib.request.Request(url, headers={"User-Agent": "financial-agent/zse"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        if resp.status != 200:
            raise RuntimeError(f"HTTP {resp.status} for {url}")
        return json.loads(resp.read().decode("utf-8"))

def security_history(isin: str, date_from: str, date_to: str, *,
                     base: str = ZSE, mic: str = "XZAG") -> dict[str, Any]:
    url = f"{base}/security-history/{mic}/{isin}/{date_from}/{date_to}/json?language=EN"
    return _get_json(url)

def index_history(isin: str, date_from: str, date_to: str, *,
                  base: str = ZSE, mic: str = "XZAG") -> dict[str, Any]:
    url = f"{base}/index-history/{mic}/{isin}/{date_from}/{date_to}/json?language=EN"
    return _get_json(url)

def _f(value: Any) -> float | None:
    if value is None or value == "":
        return None
    return float(value)

def normalize_security(payload: dict[str, Any], *, now: datetime | None = None) -> list[dict]:
    now = now or datetime.now()
    rows = []
    for raw in payload.get("history") or []:
        if raw.get("trading_model_id") != "CT":
            continue
        scale = HRK_TO_EUR if raw.get("price_currency") == "HRK" else 1.0
        close = _f(raw.get("last_price"))
        if close is None:
            continue
        rows.append({
            "date": raw["date"],
            "open": (_f(raw.get("open_price")) or close) / scale,
            "high": (_f(raw.get("high_price")) or close) / scale,
            "low": (_f(raw.get("low_price")) or close) / scale,
            "close": close / scale,
            "volume": _f(raw.get("volume")) or 0.0,
            "vwap": (_f(raw.get("vwap_price")) or close) / scale,
            "turnover": _f(raw.get("turnover")) or 0.0,
            "num_trades": int(raw.get("num_trades") or 0),
            "symbol": payload.get("symbol"),
            "isin": payload.get("isin"),
        })
    rows.sort(key=lambda r: r["date"])
    deduped: dict[str, dict] = {}
    for row in rows:
        deduped[row["date"]] = row
    out = list(deduped.values())
    today = now.date().isoformat()
    if now.hour < MARKET_CLOSE_HOUR:
        out = [r for r in out if r["date"] != today]
    return out
```

curl:

```bash
curl -sS "https://rest.zse.hr/web/Bvt9fe2peQ7pwpyYqODM/security-history/XZAG/HRICAMFCR102/2026-08-01/2026-08-21/json?language=EN"
```

---

## 10. Mapiranje u ovaj repo (7cro-tracker)

Ako integriraš **ovaj** projekt, a ne vanjskog agenta:

| Što | Gdje |
| --- | --- |
| Base URL, 7CRO ISIN, tečaj | `config/settings.py` |
| Katalog mixa + svi ETF-ovi | `config/zse_instruments.json` |
| `build_url` / fetch | `data/zse_api.py` |
| CT filter, HRK→EUR, OHLCV | `data/loaders.py` |
| Cron pull 7CRO | `scripts/fetch_zse.py` |
| Cron pull CROBEX10tr | `scripts/fetch_zse_index.py` |
| Cron pull HT/PODR/KOEI | `scripts/fetch_zse_instruments.py` |

Proširenje na mix: parametriziraj fetch po ISIN-u iz JSON kataloga
(loader već prima ISIN). Nemoj copy-pasteati četiri skripte.

`YFINANCE_TICKER = "7CRO.ZA"` ostaje samo fallback.

---

## 11. Pravni / proizvodni disclaimer

Ovo nije službeni InterCapital ni ZSE proizvod. Podaci su javni end-of-day
/ website REST Zagrebačke (i Ljubljanske) burze. Ne redistribuirati kao
real-time vendorski feed. Za komercijalni real-time: ZSE Monitor / vendor
ugovor, ne ovaj endpoint.

---

## 12. Brzi smoke test (očekivano 2026-08-21+)

```bash
python - <<'PY'
import json, urllib.request
u = "https://rest.zse.hr/web/Bvt9fe2peQ7pwpyYqODM/security-history/XZAG/HRICAMFPWIG3/2026-05-19/2026-08-21/json?language=EN"
d = json.load(urllib.request.urlopen(u))
assert d["symbol"] == "7POL" and d["history"], d
print("OK", d["symbol"], "rows", len(d["history"]), "last", d["history"][0]["date"], d["history"][0]["last_price"])
PY
```

Očekivano: `OK 7POL rows 65 last 2026-08-20 11.20` (broj redaka raste s vremenom).
