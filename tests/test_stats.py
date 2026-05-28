"""
Testovi za statistike.
"""

from core.stats import compute_stats


def test_last_price(ohlcv_df):
    """Zadnja close cijena u fixtureu je 69."""
    stats = compute_stats(ohlcv_df)
    assert stats["last_price"] == 69.0


def test_daily_change(ohlcv_df):
    """Zadnja - pretposljednja = 69 - 68 = +1.0."""
    stats = compute_stats(ohlcv_df)
    assert abs(stats["change_abs"] - 1.0) < 1e-9


def test_change_pct_sign_positive(ohlcv_df):
    """Rastući trend → pozitivna postotna promjena."""
    stats = compute_stats(ohlcv_df)
    assert stats["change_pct"] > 0


def test_52w_high_low(ohlcv_df):
    """High = max High kolone, Low = min Low kolone (sve unutar 60 dana)."""
    stats = compute_stats(ohlcv_df)
    assert stats["high_52w"] == ohlcv_df["High"].max()
    assert stats["low_52w"] == ohlcv_df["Low"].min()


def test_avg_volume_positive(ohlcv_df):
    stats = compute_stats(ohlcv_df)
    assert stats["avg_volume_30"] > 0


def test_empty_df_returns_empty():
    import pandas as pd

    assert compute_stats(pd.DataFrame()) == {}
