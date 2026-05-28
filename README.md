# 7CRO Tracker Dashboard

Profesionalni dashboard za praćenje **InterCapital CROBEX10tr UCITS ETF (7CRO)** —
TradingView-like izgled: dark mode, candlestick graf, volume, tehnički indikatori,
crosshair i zoom.

Izrađeno u Pythonu (Streamlit + lightweight-charts) sa službenim podacima
Zagrebačke burze (ZSE).

## Značajke

- **Candlestick graf** s volumenom za cijeli životni vijek ETF-a (od 2020.)
- **Tehnički indikatori**: SMA i EMA (s podesivim periodima)
- **Statistike**: zadnja cijena, dnevna promjena, 52-tjedni max/min, prosječni volumen
- **Vremenski raspon**: od 1 mjeseca do cijele povijesti
- **Robustan data layer**: CSV upload + yfinance fallback + ugrađeni ZSE podaci
- **Točna valutna obrada**: HRK cijene (do 31.12.2022.) automatski konvertirane u
  EUR po fiksnom tečaju 7,53450 → kontinuiran, financijski ispravan graf

## Struktura projekta

```
7cro-tracker/
├── app.py                  # Streamlit entry point
├── config/settings.py      # tickeri, boje, tečaj, konstante
├── data/
│   ├── loaders.py          # CSV / yfinance / sample + normalizacija
│   └── sample/7cro_zse.csv # ugrađeni ZSE podaci
├── core/
│   ├── indicators.py       # SMA, EMA (+ RSI, MACD spremni za v2)
│   └── stats.py            # statistike
└── ui/
    ├── charts.py           # lightweight-charts konfiguracija
    ├── sidebar.py          # kontrole
    └── metrics.py          # kartice statistika
```

## Pokretanje (Windows)

Otvori terminal (PowerShell ili VS Code terminal) u folderu projekta.

```powershell
# 1. Napravi virtualni environment (izolira pakete projekta)
python -m venv venv

# 2. Aktiviraj ga
venv\Scripts\activate

# 3. Instaliraj pakete
pip install -r requirements.txt

# 4. Pokreni aplikaciju
streamlit run app.py
```

Otvorit će se u browseru na `http://localhost:8501`.
Aplikacija odmah radi s ugrađenim ZSE podacima — ne treba ti ništa dodatno.

> Napomena: koristi Python 3.10–3.12. Za izlaz iz venv-a upiši `deactivate`.

## Podaci

Aplikacija koristi službeni ZSE export povijesti (`SecurityHistory`).
Za osvježavanje: preuzmi novi CSV sa [ZSE stranice 7CRO](https://zse.hr/en/papir-311/310?isin=HRICAMFCR102)
i uploadaj ga kroz sidebar — loader automatski prepoznaje ZSE format.

## Roadmap (v2)

- RSI i MACD u zasebnim panelima (logika već implementirana u `core/indicators.py`)
- Usporedba s CROBEX indeksom / drugim ETF-ovima (normalizirano na 100)
- Deploy na Streamlit Cloud

---

*Projekt nije službeno povezan s InterCapitalom. Podaci: Zagreb Stock Exchange.*
