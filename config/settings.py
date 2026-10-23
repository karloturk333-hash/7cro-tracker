"""
Centralne konstante i postavke aplikacije.
Sve "magicne" vrijednosti (tickeri, boje, tecaj) drze se ovdje
da ostatak koda ostane cist i lako podesiv.
"""

from pathlib import Path

# --- Putanje ---
BASE_DIR = Path(__file__).resolve().parent.parent
SAMPLE_CSV = BASE_DIR / "data" / "sample" / "7cro_zse.csv"
BENCHMARK_CSV = BASE_DIR / "data" / "sample" / "crobex10tr_zse.csv"

# --- Instrument ---
ETF_NAME = "InterCapital CROBEX10tr UCITS ETF"
ETF_TICKER = "7CRO"
ETF_ISIN = "HRICAMFCR102"
YFINANCE_TICKER = "7CRO.ZA"  # ZSE pokrivenost slaba; samo fallback
BENCHMARK_NAME = "CROBEX10tr"
BENCHMARK_TICKER = "C10TR"
BENCHMARK_ISIN = "HRZB00ICB103"

# Likvidne hrvatske dionice za zadanu multi-instrument usporedbu.
COMPARISON_INSTRUMENTS = {
    "HT": {
        "name": "Hrvatski Telekom",
        "isin": "HRHT00RA0005",
        "path": BASE_DIR / "data" / "sample" / "ht_zse.csv",
    },
    "PODR": {
        "name": "Podravka",
        "isin": "HRPODRRA0004",
        "path": BASE_DIR / "data" / "sample" / "podr_zse.csv",
    },
    "KOEI": {
        "name": "KONČAR",
        "isin": "HRKOEIRA0009",
        "path": BASE_DIR / "data" / "sample" / "koei_zse.csv",
    },
}
COMPARISON_SYMBOLS = [ETF_TICKER, BENCHMARK_TICKER, *COMPARISON_INSTRUMENTS]

# --- ZSE REST API ---
# Javni endpoint: <BASE>/security-history/<MIC>/<ISIN>/<od>/<do>/<fmt>?language=EN
# Nema API ključa. Pun katalog InterCapital ETF-ova + regionalni mix:
# config/zse_instruments.json  i  docs/AGENT_ZSE_API.md
ZSE_API_BASE = "https://rest.zse.hr/web/Bvt9fe2peQ7pwpyYqODM"
ZSE_MIC = "XZAG"

# --- Valuta ---
# 7CRO je trgovao u HRK do 31.12.2022, u EUR od 1.1.2023.
# Fiksni konverzijski tecaj (Zakon o uvodenju eura, HNB).
HRK_TO_EUR = 7.53450
EUR_CHANGEOVER_DATE = "2023-01-01"

# --- Standardne kolone nakon normalizacije ---
OHLCV_COLUMNS = ["Date", "Open", "High", "Low", "Close", "Volume"]

# --- Dark theme boje (TradingView-like) ---
COLORS = {
    "background": "#131722",
    "panel": "#1e222d",
    "grid": "#2a2e39",
    "text": "#d1d4dc",
    "text_dim": "#787b86",
    "up": "#26a69a",
    "down": "#ef5350",
    "volume_up": "rgba(38, 166, 154, 0.5)",
    "volume_down": "rgba(239, 83, 80, 0.5)",
    "sma": "#2962ff",
    "ema": "#ff6d00",
    "benchmark": "#b388ff",
    "bollinger": "#26c6da",
    "atr": "#ffd54f",
    "stochastic_k": "#7e57c2",
    "stochastic_d": "#26a69a",
    "obv": "#ec407a",
    "crosshair": "#758696",
    "border": "#363a45",
}

# --- Default postavke indikatora ---
DEFAULT_SMA_PERIOD = 20
DEFAULT_EMA_PERIOD = 50
