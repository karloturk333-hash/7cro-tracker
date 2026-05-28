"""
Testovi za chart layer — hover legenda i struktura panela.
"""

from core.indicators import add_macd, add_rsi
from ui.charts import build_chart_config, hover_legend_data


def test_legend_has_required_keys(ohlcv_df):
    leg = hover_legend_data(ohlcv_df)
    for key in ["date", "open", "high", "low", "close", "volume", "change_pct", "direction", "is_buy"]:
        assert key in leg


def test_legend_buy_on_uptrend(ohlcv_df):
    """Rastući trend (Close > Open) → BUY."""
    leg = hover_legend_data(ohlcv_df)
    assert leg["direction"] == "BUY"
    assert leg["is_buy"] is True


def test_legend_close_matches_last(ohlcv_df):
    leg = hover_legend_data(ohlcv_df)
    assert leg["close"] == ohlcv_df["Close"].iloc[-1]


def test_legend_empty_df():
    import pandas as pd

    assert hover_legend_data(pd.DataFrame()) == {}


def test_single_pane_without_oscillators(ohlcv_df):
    """Bez RSI/MACD → samo 1 pane (cijena)."""
    cfg = build_chart_config(ohlcv_df, {"SMA_20": False})
    assert len(cfg) == 1


def test_three_panes_with_rsi_and_macd(ohlcv_df):
    """S RSI i MACD → 3 panea."""
    df = add_rsi(ohlcv_df)
    df = add_macd(df)
    cfg = build_chart_config(df, {"RSI": True, "MACD": True})
    assert len(cfg) == 3


def test_main_pane_has_candlestick(ohlcv_df):
    cfg = build_chart_config(ohlcv_df, {})
    types = [s["type"] for s in cfg[0]["series"]]
    assert "Candlestick" in types and "Histogram" in types


def test_fullscreen_height_larger(ohlcv_df):
    normal = build_chart_config(ohlcv_df, {}, main_height=520)
    full = build_chart_config(ohlcv_df, {}, main_height=700)
    assert full[0]["chart"]["height"] > normal[0]["chart"]["height"]
