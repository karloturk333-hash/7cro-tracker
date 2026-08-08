"""Benchmark, likvidnost i svjezina podataka za ZSE market-intelligence prikaz."""

from __future__ import annotations

from datetime import date

import pandas as pd


def build_benchmark_comparison(asset: pd.DataFrame, benchmark: pd.DataFrame) -> pd.DataFrame:
    """Poravnaj zajednicke sesije i normaliziraj obje close serije na 100."""
    if asset.empty or benchmark.empty:
        return pd.DataFrame(columns=["Date", "7CRO", "CROBEX10tr"])

    joined = (
        asset[["Date", "Close"]]
        .rename(columns={"Close": "asset"})
        .merge(
            benchmark[["Date", "Close"]].rename(columns={"Close": "benchmark"}),
            on="Date",
            how="inner",
        )
        .dropna()
        .sort_values("Date")
        .reset_index(drop=True)
    )
    if joined.empty or joined.iloc[0]["asset"] == 0 or joined.iloc[0]["benchmark"] == 0:
        return pd.DataFrame(columns=["Date", "7CRO", "CROBEX10tr"])

    joined["7CRO"] = joined["asset"] / joined.iloc[0]["asset"] * 100
    joined["CROBEX10tr"] = joined["benchmark"] / joined.iloc[0]["benchmark"] * 100
    return joined[["Date", "7CRO", "CROBEX10tr"]]


def benchmark_stats(comparison: pd.DataFrame) -> dict:
    """Izracunaj relativni prinos i korelaciju dnevnih prinosa."""
    if comparison.empty:
        return {}

    asset_return = comparison.iloc[-1]["7CRO"] - 100
    benchmark_return = comparison.iloc[-1]["CROBEX10tr"] - 100
    daily = comparison[["7CRO", "CROBEX10tr"]].pct_change().dropna()
    correlation = daily["7CRO"].corr(daily["CROBEX10tr"]) if len(daily) >= 2 else float("nan")
    return {
        "asset_return_pct": float(asset_return),
        "benchmark_return_pct": float(benchmark_return),
        "tracking_difference_pct": float(asset_return - benchmark_return),
        "correlation": float(correlation),
        "sessions": int(len(comparison)),
    }


def liquidity_stats(market: pd.DataFrame, prices: pd.DataFrame) -> dict:
    """Sazmi ZSE VWAP, promet i broj transakcija za zadnjih 30 sesija."""
    if market.empty:
        return {}

    recent = market.sort_values("Date").tail(30)
    last = recent.iloc[-1]
    total_trades = recent["NumTrades"].sum()
    result = {
        "last_vwap": float(last["VWAP"]),
        "last_turnover": float(last["Turnover"]),
        "last_trades": int(last["NumTrades"]),
        "avg_turnover_30": float(recent["Turnover"].mean()),
        "avg_trades_30": float(recent["NumTrades"].mean()),
        "avg_trade_value_30": float(recent["Turnover"].sum() / total_trades) if total_trades else 0.0,
    }

    matching_price = prices.loc[prices["Date"] == last["Date"], "Close"] if not prices.empty else pd.Series()
    close = float(matching_price.iloc[-1]) if not matching_price.empty else None
    result["close_vs_vwap_pct"] = ((close / result["last_vwap"] - 1) * 100) if close and result["last_vwap"] else None
    return result


def freshness_status(last_date, *, as_of: date | None = None, stale_after: int = 2) -> dict:
    """Broji radne dane bez podataka; vikendi sami po sebi ne cine podatke starima."""
    if last_date is None or pd.isna(last_date):
        return {"business_days_stale": None, "is_stale": True}

    latest = pd.Timestamp(last_date).normalize()
    current = pd.Timestamp(as_of or date.today()).normalize()
    if latest >= current:
        days = 0
    else:
        days = len(pd.bdate_range(latest + pd.Timedelta(days=1), current))
    return {"business_days_stale": days, "is_stale": days > stale_after}
