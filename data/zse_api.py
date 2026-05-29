"""
ZSE REST API integracija — automatski dohvat povijesti 7CRO.

Javni endpoint vraca isti format kao rucni CSV export sa zse.hr,
pa parsiranje reuse-amo iz loaders.py.
"""

from __future__ import annotations

import io

import pandas as pd

from config.settings import OHLCV_COLUMNS, ZSE_API_BASE, ZSE_MIC
from data.loaders import _read_zse_csv

# Sat (CET) nakon kojeg smatramo danasnji trgovinski dan zavrsenim.
MARKET_CLOSE_HOUR = 18


def build_url(isin: str, date_from: str, date_to: str, fmt: str = "csv") -> str:
    """
    Sastavi ZSE REST URL za security-history.
    Format: <BASE>/security-history/<MIC>/<ISIN>/<od>/<do>/<fmt>?language=EN
    """
    return (
        f"{ZSE_API_BASE}/security-history/{ZSE_MIC}/{isin}/"
        f"{date_from}/{date_to}/{fmt}?language=EN"
    )


def fetch_history(isin: str, date_from: str, date_to: str, timeout: int = 30) -> bytes:
    """Dohvati sirovi CSV s ZSE API-ja. Jedina funkcija koja dira mrezu."""
    import requests

    url = build_url(isin, date_from, date_to, fmt="csv")
    resp = requests.get(url, timeout=timeout)
    resp.raise_for_status()
    return resp.content


def parse_zse_csv_bytes(raw: bytes) -> pd.DataFrame:
    """Sirovi ZSE CSV (bytes) -> normalizirani OHLCV df (EUR, CT only)."""
    return _read_zse_csv(io.BytesIO(raw))


def load_from_api(isin: str, date_from: str, date_to: str) -> pd.DataFrame:
    """Fetch + parse u jednom koraku."""
    return parse_zse_csv_bytes(fetch_history(isin, date_from, date_to))


def merge_with_existing(old: pd.DataFrame, new: pd.DataFrame) -> pd.DataFrame:
    """
    Inkrementalno spoji nove podatke s postojecima.
    Kod preklapanja datuma zadrzava NOVU vrijednost. Ako je `new` prazan,
    vraca `old` netaknut.
    """
    if new is None or new.empty:
        return old.reset_index(drop=True)
    if old is None or old.empty:
        return new.reset_index(drop=True)

    combined = pd.concat([old, new], ignore_index=True)
    combined["Date"] = pd.to_datetime(combined["Date"])
    combined = (
        combined.sort_values("Date")
        .drop_duplicates(subset="Date", keep="last")
        .reset_index(drop=True)
    )
    return combined[OHLCV_COLUMNS]


def drop_unfinished_today(df: pd.DataFrame, now=None) -> pd.DataFrame:
    """
    Izbaci danasnji (jos nezavrseni) candle ako je trenutni sat prije
    zatvaranja burze (MARKET_CLOSE_HOUR, CET). Stariji dani se ne diraju.
    """
    from datetime import datetime

    if df is None or df.empty:
        return df
    if now is None:
        now = datetime.now()

    today = pd.Timestamp(now.date())
    out = df.copy()
    out["Date"] = pd.to_datetime(out["Date"])

    if now.hour < MARKET_CLOSE_HOUR:
        out = out[out["Date"] != today]

    return out.reset_index(drop=True)
