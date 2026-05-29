"""
Testovi za ZSE REST API integraciju (auto-pull). Mreza se ne dira (mock).
"""

import pandas as pd

from config.settings import ETF_ISIN, ZSE_MIC
from data.zse_api import (
    build_url,
    drop_unfinished_today,
    merge_with_existing,
    parse_zse_csv_bytes,
)


def test_build_url_format():
    url = build_url(ETF_ISIN, "2026-04-28", "2026-05-28", fmt="csv")
    assert ZSE_MIC in url and ETF_ISIN in url
    assert "2026-04-28" in url and "2026-05-28" in url
    assert url.endswith("/csv?language=EN")


def test_parse_zse_csv_bytes_to_ohlcv():
    raw = (
        '"mic";"symbol";"isin";"date";"trading_model_id";"open_price";'
        '"high_price";"low_price";"last_price";"vwap_price";'
        '"change_prev_close_percentage";"num_trades";"volume";"turnover";'
        '"price_currency";"turnover_currency"\n'
        '"XZAG";"7CRO";"HRICAMFCR102";"2026-05-28";"CT";37,90;37,90;37,61;'
        '37,61;37,77;-0,50;4;115,00000;4344,60;"EUR";"EUR"\n'
    ).encode("utf-8")
    df = parse_zse_csv_bytes(raw)
    assert list(df.columns) == ["Date", "Open", "High", "Low", "Close", "Volume"]
    assert abs(df.iloc[0]["Close"] - 37.61) < 0.001


def test_merge_adds_new_rows():
    old = pd.DataFrame({
        "Date": pd.to_datetime(["2026-05-26", "2026-05-27"]),
        "Open": [37.7, 37.8], "High": [37.7, 37.8], "Low": [37.5, 37.8],
        "Close": [37.5, 37.8], "Volume": [201.0, 24.0],
    })
    new = pd.DataFrame({
        "Date": pd.to_datetime(["2026-05-28"]),
        "Open": [37.9], "High": [37.9], "Low": [37.61],
        "Close": [37.61], "Volume": [115.0],
    })
    merged = merge_with_existing(old, new)
    assert len(merged) == 3
    assert merged["Date"].is_monotonic_increasing


def test_merge_dedupe_keeps_new():
    old = pd.DataFrame({
        "Date": pd.to_datetime(["2026-05-28"]),
        "Open": [37.0], "High": [37.0], "Low": [37.0],
        "Close": [37.0], "Volume": [10.0],
    })
    new = pd.DataFrame({
        "Date": pd.to_datetime(["2026-05-28"]),
        "Open": [37.9], "High": [37.9], "Low": [37.61],
        "Close": [37.61], "Volume": [115.0],
    })
    merged = merge_with_existing(old, new)
    assert len(merged) == 1
    assert merged.iloc[0]["Close"] == 37.61


def test_merge_empty_new_keeps_old():
    old = pd.DataFrame({
        "Date": pd.to_datetime(["2026-05-28"]),
        "Open": [37.9], "High": [37.9], "Low": [37.61],
        "Close": [37.61], "Volume": [115.0],
    })
    new = pd.DataFrame(columns=["Date", "Open", "High", "Low", "Close", "Volume"])
    assert len(merge_with_existing(old, new)) == 1


def test_drop_unfinished_today_before_close():
    from datetime import datetime

    df = pd.DataFrame({
        "Date": pd.to_datetime(["2026-05-28", "2026-05-29"]),
        "Open": [37.8, 37.9], "High": [37.8, 38.0], "Low": [37.6, 37.7],
        "Close": [37.8, 37.95], "Volume": [24.0, 50.0],
    })
    out = drop_unfinished_today(df, now=datetime(2026, 5, 29, 14, 0))
    assert pd.Timestamp("2026-05-29") not in out["Date"].values
    assert pd.Timestamp("2026-05-28") in out["Date"].values


def test_keep_today_after_close():
    from datetime import datetime

    df = pd.DataFrame({
        "Date": pd.to_datetime(["2026-05-29"]),
        "Open": [37.9], "High": [38.0], "Low": [37.7],
        "Close": [37.95], "Volume": [50.0],
    })
    out = drop_unfinished_today(df, now=datetime(2026, 5, 29, 18, 30))
    assert pd.Timestamp("2026-05-29") in out["Date"].values


def test_past_days_always_kept():
    from datetime import datetime

    df = pd.DataFrame({
        "Date": pd.to_datetime(["2026-05-27", "2026-05-28"]),
        "Open": [37.7, 37.8], "High": [37.7, 37.8], "Low": [37.5, 37.6],
        "Close": [37.5, 37.8], "Volume": [201.0, 24.0],
    })
    out = drop_unfinished_today(df, now=datetime(2026, 5, 29, 10, 0))
    assert len(out) == 2
