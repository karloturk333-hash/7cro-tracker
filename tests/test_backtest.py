"""Testovi za mini backtest engine."""

import numpy as np
import pandas as pd

from quant.backtest import generate_signals, run_backtest


def _trend_df(n=120):
    """Cisto rastuci trend — strategija bi trebala biti u trzistu vecinom."""
    dates = pd.date_range("2024-01-01", periods=n, freq="D")
    close = pd.Series(np.linspace(10, 50, n))
    return pd.DataFrame({
        "Date": dates, "Open": close, "High": close + 0.5,
        "Low": close - 0.5, "Close": close, "Volume": [100.0] * n,
    })


def test_signals_columns():
    out = generate_signals(_trend_df(), fast=10, slow=30)
    for col in ["sma_fast", "sma_slow", "signal", "position"]:
        assert col in out.columns


def test_no_lookahead_position_shifted():
    """Pozicija mora biti pomaknuta (shift) — danasnja odluka, sutrasnji trade."""
    out = generate_signals(_trend_df(), fast=10, slow=30)
    # prvi position je 0 (nema jucerasnjeg signala)
    assert out["position"].iloc[0] == 0


def test_uptrend_strategy_in_market():
    """Na rastucem trendu strategija provede vecinu vremena u trzistu."""
    out = generate_signals(_trend_df(), fast=10, slow=30)
    # nakon warmup-a, pozicija je uglavnom 1
    assert out["position"].iloc[40:].mean() > 0.8


def test_backtest_returns_keys():
    res = run_backtest(_trend_df(), fast=10, slow=30)
    for k in ["strategy_return", "buyhold_return", "n_trades", "max_drawdown", "win"]:
        assert k in res


def test_drawdown_non_positive():
    """Max drawdown je <= 0 (pad ili nula)."""
    res = run_backtest(_trend_df(), fast=10, slow=30)
    assert res["max_drawdown"] <= 0


def test_n_trades_non_negative():
    res = run_backtest(_trend_df(), fast=10, slow=30)
    assert res["n_trades"] >= 0
