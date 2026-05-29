# Plan v3 — Auto-pull sa ZSE + Drawing Tools

> Sve nove funkcije razvijati **TDD-om**: prvo test, pa implementacija.

---

## Dio 1: Automatski dnevni pull sa ZSE (GitHub Actions + ZSE API)

### Cilj
App uvijek ima svjeze podatke bez rucnog skidanja CSV-a.

### Arhitektura
```
GitHub Actions (cron, svaki radni dan 18:00)
        │
        ▼
scripts/fetch_zse.py  ──>  rest.zse.hr/.../security-history/XZAG/HRICAMFCR102/<od>/<do>/csv
        │                          │
        │                          ▼
        │                  normalize_df (postojeci loader)
        ▼
data/sample/7cro_zse.csv  (commit nazad u repo)
        │
        ▼
Streamlit Cloud auto-redeploy  ──>  svjez graf
```

### Komponente

**1. `data/zse_api.py`** (NOVO)
- `build_url(isin, date_from, date_to, fmt="csv")` — sastavi ZSE REST URL
- `fetch_history(isin, date_from, date_to)` — GET zahtjev, vrati raw bytes
- `load_from_api(...)` — fetch + provedi kroz `normalize_df` (reuse iz loaders.py)
- **RIZIK:** URL sadrzi token (`rest.zse.hr/web/<TOKEN>/...`). Prvi korak: provjeriti je li token stalan ili se rotira po sesiji. Ako rotira → treba ga dohvatiti s glavne stranice prije poziva.

**2. `scripts/fetch_zse.py`** (NOVO)
- Standalone skripta: povuce zadnjih ~30 dana, spoji s postojecim CSV-om, dedupe po datumu, spremi
- Inkrementalni update (ne povlaci cijelu povijest svaki put)

**3. `.github/workflows/update-data.yml`** (NOVO)
```yaml
on:
  schedule:
    - cron: "0 17 * * 1-5"   # 17:00 UTC = 18:00 HR, radnim danom
  workflow_dispatch:          # rucno pokretanje gumbom
jobs:
  update:
    - checkout, setup-python, pip install
    - python scripts/fetch_zse.py
    - git commit & push ako ima promjena
```

### TDD testovi (prvo napisati)
- `test_build_url` — tocan format URL-a
- `test_fetch_parses_to_ohlcv` — mock HTTP odgovor → normalizirani df
- `test_incremental_merge` — spajanje novih + starih bez duplih datuma
- `test_api_failure_fallback` — ako API padne, zadrzi postojeci CSV (ne brise podatke)

### Fallback lanac (vec postoji u loaders.py)
uploadani CSV → API/cron CSV → sample CSV. Nikad ne pukne.

---

## Dio 2: Drawing Tools (ravnalo, trendline, Fibonacci) — PROCJENA

### Tehnicki zid
`streamlit-lightweight-charts` 0.7.x je **read-only** — ne prima klikove misa
nazad u Python, nema interaktivnog crtanja. Ovo je kljucno ogranicenje.

### Opcija A — Staticni alati (mali trud, radi odmah)
- Fibonacci: korisnik unese 2 cijene (high/low) → app izracuna razine
  (0, 0.236, 0.382, 0.5, 0.618, 0.786, 1.0) i nacrta horizontalne linije
- Trendline: korisnik odabere 2 datuma+cijene → linija izmedu njih
- Horizontalna linija: jedna cijena → support/resistance
- **Trud:** ~1 dan. Radi u trenutnom wrapperu (price lines / line series).
- **Mana:** nije "povuci misem", nego input-based.

### Opcija B — Puni mouse-draw (velik trud, prava TradingView interakcija)
- Prepisati chart layer u custom `components.html` s lightweight-charts v4 + drawing plugins
- Mis crta trendline, Fib, ravnalo direktno na grafu
- Stanje crteza cuvati u browseru (localStorage) ili session_state
- **Trud:** ~3-5 dana. Chart layer (charts.py) se prebacuje u JS.
- **Dobit:** izgleda i radi kao pravi TradingView. Vrlo impresivno za portfolio.

### Preporuka
Krenuti s **Opcijom A** (brza pobjeda, Fibonacci je najkorisniji), a Opciju B
drzati kao "stretch goal" ako ostane vremena. Opcija A pokriva 80% dojma uz 20% truda.

---

## Redoslijed izvedbe v3
1. Provjeriti ZSE API token (stalan vs rotirajuci) — 30 min istrazivanja
2. TDD: testovi za zse_api.py
3. zse_api.py + scripts/fetch_zse.py
4. GitHub Actions workflow + prvi test run (workflow_dispatch)
5. (kasnije) Drawing tools — Opcija A
