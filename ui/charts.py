"""
Chart layer — gradi konfiguraciju za streamlit-lightweight-charts.

Sve što ima veze s izgledom grafa (candlestick, volume, indikatori,
dark tema, crosshair) izolirano je ovdje. Ako ikad mijenjamo charting
biblioteku, diramo samo ovaj fajl.

lightweight-charts traži podatke kao listu dictova s 'time' poljem
(ISO string 'YYYY-MM-DD') i odgovarajućim value poljima.
"""

from __future__ import annotations

import pandas as pd

from config.settings import COLORS


def _to_time(series: pd.Series) -> pd.Series:
    """Datetime -> 'YYYY-MM-DD' string koji lightweight-charts očekuje."""
    return series.dt.strftime("%Y-%m-%d")


def _candlestick_data(df: pd.DataFrame) -> list[dict]:
    out = df.copy()
    out["time"] = _to_time(out["Date"])
    return out[["time", "Open", "High", "Low", "Close"]].rename(
        columns={"Open": "open", "High": "high", "Low": "low", "Close": "close"}
    ).to_dict("records")


def _volume_data(df: pd.DataFrame) -> list[dict]:
    out = df.copy()
    out["time"] = _to_time(out["Date"])
    # boja volumena ovisi o tome je li dan rastući ili padajući
    up = out["Close"] >= out["Open"]
    out["color"] = up.map(
        {True: COLORS["volume_up"], False: COLORS["volume_down"]}
    )
    out = out.rename(columns={"Volume": "value"})
    return out[["time", "value", "color"]].to_dict("records")


def _line_data(df: pd.DataFrame, col: str) -> list[dict]:
    """Pretvori indikatorsku kolonu u line-series podatke (preskače NaN)."""
    out = df[["Date", col]].dropna().copy()
    out["time"] = _to_time(out["Date"])
    out = out.rename(columns={col: "value"})
    return out[["time", "value"]].to_dict("records")


def build_chart_config(df: pd.DataFrame, indicators: dict | None = None) -> list[dict]:
    """
    Sastavi konfiguraciju za renderLightweightCharts().

    `indicators` je dict oblika {"SMA_20": True, "EMA_50": True} koji
    kaže koje indikatorske linije ucrtati (kolone moraju postojati u df).

    Vraća listu s jednim chart objektom (candlestick+volume+linije
    u istom panelu, volume skaliran na dno).
    """
    indicators = indicators or {}

    # Glavni candlestick series
    series = [
        {
            "type": "Candlestick",
            "data": _candlestick_data(df),
            "options": {
                "upColor": COLORS["up"],
                "downColor": COLORS["down"],
                "borderUpColor": COLORS["up"],
                "borderDownColor": COLORS["down"],
                "wickUpColor": COLORS["up"],
                "wickDownColor": COLORS["down"],
            },
        },
        # Volume kao histogram, vlastita skala stisnuta na dno (0.8-1.0)
        {
            "type": "Histogram",
            "data": _volume_data(df),
            "options": {
                "priceFormat": {"type": "volume"},
                "priceScaleId": "volume",
            },
            "priceScale": {
                "scaleMargins": {"top": 0.8, "bottom": 0.0},
            },
        },
    ]

    # Indikatorske linije (overlay preko cijene)
    line_colors = {"SMA": COLORS["sma"], "EMA": COLORS["ema"]}
    for col, enabled in indicators.items():
        if not enabled or col not in df.columns:
            continue
        prefix = col.split("_")[0]
        series.append(
            {
                "type": "Line",
                "data": _line_data(df, col),
                "options": {
                    "color": line_colors.get(prefix, COLORS["text_dim"]),
                    "lineWidth": 2,
                    "priceLineVisible": False,
                    "lastValueVisible": True,
                    "title": col,
                },
            }
        )

    chart = {
        "chart": {
            "layout": {
                "background": {"type": "solid", "color": COLORS["background"]},
                "textColor": COLORS["text"],
            },
            "grid": {
                "vertLines": {"color": COLORS["grid"]},
                "horzLines": {"color": COLORS["grid"]},
            },
            "crosshair": {
                "mode": 1,  # magnet na podatke
                "vertLine": {"color": COLORS["crosshair"], "width": 1, "style": 2},
                "horzLine": {"color": COLORS["crosshair"], "width": 1, "style": 2},
            },
            "rightPriceScale": {"borderColor": COLORS["grid"]},
            "timeScale": {
                "borderColor": COLORS["grid"],
                "timeVisible": False,
                "rightOffset": 5,
            },
            "handleScroll": True,
            "handleScale": True,
        },
        "series": series,
    }

    return [chart]
