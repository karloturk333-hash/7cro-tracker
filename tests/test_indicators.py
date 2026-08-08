"""
Testovi za tehničke indikatore.
"""

import pandas as pd
import pytest

from core.indicators import (
    add_atr,
    add_bollinger_bands,
    add_ema,
    add_macd,
    add_obv,
    add_rsi,
    add_sma,
    add_stochastic,
)


def test_sma_adds_column(ohlcv_df):
    out = add_sma(ohlcv_df, period=5)
    assert "SMA_5" in out.columns


def test_sma_value_correct(ohlcv_df):
    """SMA_5 na poziciji 4 = prosjek prvih 5 close (10,11,12,13,14) = 12."""
    out = add_sma(ohlcv_df, period=5)
    assert out["SMA_5"].iloc[4] == 12.0


def test_sma_warmup_is_nan(ohlcv_df):
    """Prvih (period-1) vrijednosti su NaN (nema dovoljno podataka)."""
    out = add_sma(ohlcv_df, period=5)
    assert out["SMA_5"].iloc[:4].isna().all()


def test_ema_adds_column(ohlcv_df):
    out = add_ema(ohlcv_df, period=10)
    assert "EMA_10" in out.columns


def test_ema_no_nan_after_first(ohlcv_df):
    """EMA (adjust=False) ima vrijednost od prvog reda."""
    out = add_ema(ohlcv_df, period=10)
    assert out["EMA_10"].notna().all()


def test_rsi_in_valid_range(ohlcv_df):
    """RSI mora biti između 0 i 100."""
    out = add_rsi(ohlcv_df, period=14)
    rsi = out["RSI_14"].dropna()
    assert (rsi >= 0).all() and (rsi <= 100).all()


def test_rsi_high_on_uptrend(ohlcv_df):
    """Na čisto rastućem trendu RSI je visok (>70)."""
    out = add_rsi(ohlcv_df, period=14)
    assert out["RSI_14"].dropna().iloc[-1] > 70


def test_macd_columns(ohlcv_df):
    out = add_macd(ohlcv_df)
    for col in ["MACD", "MACD_signal", "MACD_hist"]:
        assert col in out.columns


def test_macd_hist_is_difference(ohlcv_df):
    """Histogram = MACD - signal."""
    out = add_macd(ohlcv_df)
    diff = (out["MACD_hist"] - (out["MACD"] - out["MACD_signal"])).abs().max()
    assert diff < 1e-9


def test_indicators_do_not_mutate_input(ohlcv_df):
    """Indikatori vraćaju novi df, ne mijenjaju ulazni (čiste funkcije)."""
    cols_before = list(ohlcv_df.columns)
    add_sma(ohlcv_df, 5)
    add_rsi(ohlcv_df)
    assert list(ohlcv_df.columns) == cols_before


def test_bollinger_bands_have_expected_columns_and_order(ohlcv_df):
    out = add_bollinger_bands(ohlcv_df, period=20)
    assert {"BB_middle_20", "BB_upper_20", "BB_lower_20"} <= set(out.columns)
    last = out.iloc[-1]
    assert last["BB_upper_20"] > last["BB_middle_20"] > last["BB_lower_20"]


def test_atr_matches_constant_fixture_range(ohlcv_df):
    out = add_atr(ohlcv_df, period=14)
    assert out["ATR_14"].iloc[-1] == pytest.approx(2.0)
    assert out["ATR_14"].iloc[:13].isna().all()


def test_stochastic_is_bounded_and_has_signal(ohlcv_df):
    out = add_stochastic(ohlcv_df, period=14, smooth=3)
    k = out["STOCH_K_14"].dropna()
    assert (k >= 0).all() and (k <= 100).all()
    assert out["STOCH_D_14_3"].notna().any()


def test_obv_accumulates_volume_on_uptrend(ohlcv_df):
    out = add_obv(ohlcv_df)
    assert out["OBV"].iloc[0] == 0
    assert out["OBV"].is_monotonic_increasing
    assert out["OBV"].iloc[-1] == ohlcv_df["Volume"].iloc[1:].sum()
