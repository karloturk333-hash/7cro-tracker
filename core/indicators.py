"""
Tehnički indikatori — čiste funkcije nad OHLCV DataFrameom.

Svaka funkcija prima df i vraća NOVI df s dodatnom kolonom.
Bez side-effecta, lako za testiranje i kombiniranje.
"""

from __future__ import annotations

import pandas as pd


def add_sma(df: pd.DataFrame, period: int = 20, col: str = "Close") -> pd.DataFrame:
    """Simple Moving Average — prosjek zadnjih `period` close cijena."""
    df = df.copy()
    df[f"SMA_{period}"] = df[col].rolling(window=period, min_periods=period).mean()
    return df


def add_ema(df: pd.DataFrame, period: int = 50, col: str = "Close") -> pd.DataFrame:
    """Exponential Moving Average — daje veću težinu novijim cijenama."""
    df = df.copy()
    df[f"EMA_{period}"] = df[col].ewm(span=period, adjust=False).mean()
    return df


# --- Pripremljeno za v2 (RSI, MACD) ---

def add_rsi(df: pd.DataFrame, period: int = 14, col: str = "Close") -> pd.DataFrame:
    """Relative Strength Index (0-100). Spreman za v2."""
    df = df.copy()
    delta = df[col].diff()
    gain = delta.clip(lower=0).rolling(window=period).mean()
    loss = (-delta.clip(upper=0)).rolling(window=period).mean()
    rs = gain / loss
    df[f"RSI_{period}"] = 100 - (100 / (1 + rs))
    return df


def add_macd(
    df: pd.DataFrame,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
    col: str = "Close",
) -> pd.DataFrame:
    """MACD linija, signalna linija i histogram. Spreman za v2."""
    df = df.copy()
    ema_fast = df[col].ewm(span=fast, adjust=False).mean()
    ema_slow = df[col].ewm(span=slow, adjust=False).mean()
    df["MACD"] = ema_fast - ema_slow
    df["MACD_signal"] = df["MACD"].ewm(span=signal, adjust=False).mean()
    df["MACD_hist"] = df["MACD"] - df["MACD_signal"]
    return df
