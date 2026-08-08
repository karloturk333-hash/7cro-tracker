from datetime import date

import pandas as pd

from core.market_intelligence import (
    benchmark_stats,
    build_benchmark_comparison,
    freshness_status,
    liquidity_stats,
)


def _prices(values):
    return pd.DataFrame(
        {
            "Date": pd.date_range("2026-01-01", periods=len(values), freq="D"),
            "Close": values,
        }
    )


def test_comparison_rebases_both_series_to_100():
    comparison = build_benchmark_comparison(_prices([10, 11, 12]), _prices([1000, 1050, 1100]))
    assert comparison.iloc[0]["7CRO"] == 100
    assert comparison.iloc[0]["CROBEX10tr"] == 100
    assert comparison.iloc[-1]["7CRO"] == 120
    assert comparison.iloc[-1]["CROBEX10tr"] == 110


def test_benchmark_stats_reports_tracking_difference():
    comparison = build_benchmark_comparison(_prices([10, 11, 12]), _prices([1000, 1050, 1100]))
    stats = benchmark_stats(comparison)
    assert abs(stats["tracking_difference_pct"] - 10) < 1e-9
    assert stats["sessions"] == 3


def test_liquidity_stats_uses_turnover_and_vwap():
    prices = _prices([10, 12])
    market = pd.DataFrame(
        {
            "Date": prices["Date"],
            "VWAP": [10.0, 11.0],
            "Turnover": [1000.0, 2200.0],
            "NumTrades": [10, 20],
            "Volume": [100, 200],
        }
    )
    stats = liquidity_stats(market, prices)
    assert stats["avg_trade_value_30"] == 3200 / 30
    assert abs(stats["close_vs_vwap_pct"] - (12 / 11 - 1) * 100) < 1e-9


def test_freshness_ignores_weekend():
    status = freshness_status(pd.Timestamp("2026-08-07"), as_of=date(2026, 8, 8))
    assert status == {"business_days_stale": 0, "is_stale": False}


def test_freshness_warns_after_two_business_days():
    status = freshness_status(pd.Timestamp("2026-08-03"), as_of=date(2026, 8, 7))
    assert status["business_days_stale"] == 4
    assert status["is_stale"] is True
