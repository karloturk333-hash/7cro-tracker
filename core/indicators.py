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


def add_bollinger_bands(
    df: pd.DataFrame,
    period: int = 20,
    std_dev: float = 2.0,
    col: str = "Close",
) -> pd.DataFrame:
    """Bollinger Bands: pomicni prosjek plus/minus `std_dev` standardnih devijacija."""
    df = df.copy()
    middle = df[col].rolling(window=period, min_periods=period).mean()
    deviation = df[col].rolling(window=period, min_periods=period).std(ddof=0)
    df[f"BB_middle_{period}"] = middle
    df[f"BB_upper_{period}"] = middle + std_dev * deviation
    df[f"BB_lower_{period}"] = middle - std_dev * deviation
    return df


def add_atr(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    """Average True Range kao mjera apsolutne volatilnosti."""
    df = df.copy()
    previous_close = df["Close"].shift(1)
    true_range = pd.concat(
        [
            df["High"] - df["Low"],
            (df["High"] - previous_close).abs(),
            (df["Low"] - previous_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    df[f"ATR_{period}"] = true_range.rolling(window=period, min_periods=period).mean()
    return df


def add_stochastic(
    df: pd.DataFrame,
    period: int = 14,
    smooth: int = 3,
) -> pd.DataFrame:
    """Stochastic oscillator %K i njegov `smooth`-dnevni %D prosjek."""
    df = df.copy()
    lowest = df["Low"].rolling(window=period, min_periods=period).min()
    highest = df["High"].rolling(window=period, min_periods=period).max()
    price_range = highest - lowest
    k = (df["Close"] - lowest) / price_range.where(price_range != 0) * 100
    df[f"STOCH_K_{period}"] = k
    df[f"STOCH_D_{period}_{smooth}"] = k.rolling(window=smooth, min_periods=smooth).mean()
    return df


def add_obv(df: pd.DataFrame, col: str = "Close") -> pd.DataFrame:
    """On-Balance Volume: kumulativni volumen potpisan smjerom promjene cijene."""
    df = df.copy()
    direction = df[col].diff()
    signed_volume = df["Volume"].where(direction > 0, -df["Volume"])
    signed_volume = signed_volume.where(direction != 0, 0.0)
    if not signed_volume.empty:
        signed_volume.iloc[0] = 0.0
    df["OBV"] = signed_volume.cumsum()
    return df
