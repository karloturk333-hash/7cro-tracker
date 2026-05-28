"""
Centralne konstante i postavke aplikacije.
Sve "magične" vrijednosti (tickeri, boje, tečaj) drže se ovdje
da ostatak koda ostane čist i lako podesiv.
"""

from pathlib import Path

# --- Putanje ---
BASE_DIR = Path(__file__).resolve().parent.parent
SAMPLE_CSV = BASE_DIR / "data" / "sample" / "7cro_zse.csv"

# --- Instrument ---
ETF_NAME = "InterCapital CROBEX10tr UCITS ETF"
ETF_TICKER = "7CRO"
ETF_ISIN = "HRICAMFCR102"
YFINANCE_TICKER = "7CRO.ZA"  # pokušaj; ZSE pokrivenost je slaba pa je ovo samo fallback

# --- Valuta ---
# 7CRO je trgovao u HRK do 31.12.2022, u EUR od 1.1.2023.
# Fiksni konverzijski tečaj (Zakon o uvođenju eura, HNB).
HRK_TO_EUR = 7.53450
EUR_CHANGEOVER_DATE = "2023-01-01"

# --- Standardne kolone nakon normalizacije ---
# Cijeli app se oslanja na točno ove kolone, bez obzira na izvor podataka.
OHLCV_COLUMNS = ["Date", "Open", "High", "Low", "Close", "Volume"]

# --- Dark theme boje (TradingView-like) ---
COLORS = {
    "background": "#131722",
    "panel": "#1e222d",
    "grid": "#2a2e39",
    "text": "#d1d4dc",
    "text_dim": "#787b86",
    "up": "#26a69a",        # zelena (rast)
    "down": "#ef5350",      # crvena (pad)
    "volume_up": "rgba(38, 166, 154, 0.5)",
    "volume_down": "rgba(239, 83, 80, 0.5)",
    "sma": "#2962ff",       # plava
    "ema": "#ff6d00",       # narančasta
    "crosshair": "#758696",
    "border": "#363a45",
}

# --- Default postavke indikatora ---
DEFAULT_SMA_PERIOD = 20
DEFAULT_EMA_PERIOD = 50
