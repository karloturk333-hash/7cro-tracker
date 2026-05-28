"""
Sažete statistike za "kartice" na vrhu dashboarda.
"""

from __future__ import annotations

import pandas as pd


def compute_stats(df: pd.DataFrame) -> dict:
    """
    Izračuna ključne metrike iz OHLCV DataFramea.

    Vraća dict s:
        last_price       — zadnja close cijena (EUR)
        change_abs       — apsolutna dnevna promjena (EUR)
        change_pct       — postotna dnevna promjena (%)
        avg_volume_30    — prosječni volumen zadnjih 30 dana trgovanja
        high_52w         — najviša cijena u zadnjih 52 tjedna
        low_52w          — najniža cijena u zadnjih 52 tjedna
        last_date        — datum zadnjeg podatka
    """
    if df.empty:
        return {}

    last = df.iloc[-1]
    prev_close = df.iloc[-2]["Close"] if len(df) >= 2 else last["Close"]

    change_abs = last["Close"] - prev_close
    change_pct = (change_abs / prev_close * 100) if prev_close else 0.0

    # 52 tjedna ~ zadnjih 365 dana
    cutoff = last["Date"] - pd.Timedelta(days=365)
    last_year = df[df["Date"] >= cutoff]

    avg_volume_30 = df["Volume"].tail(30).mean()

    return {
        "last_price": float(last["Close"]),
        "change_abs": float(change_abs),
        "change_pct": float(change_pct),
        "avg_volume_30": float(avg_volume_30),
        "high_52w": float(last_year["High"].max()),
        "low_52w": float(last_year["Low"].min()),
        "last_date": last["Date"],
    }
