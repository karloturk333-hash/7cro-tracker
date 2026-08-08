"""
Chart layer — gradi konfiguraciju za streamlit-lightweight-charts.

Sve sto ima veze s izgledom grafa (candlestick, volume, indikatori,
dark tema, crosshair) izolirano je ovdje. Ako mijenjamo charting
biblioteku, diramo samo ovaj fajl.
"""

from __future__ import annotations

import pandas as pd

from config.settings import COLORS


def _to_time(series: pd.Series) -> pd.Series:
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
    up = out["Close"] >= out["Open"]
    out["color"] = up.map({True: COLORS["volume_up"], False: COLORS["volume_down"]})
    out = out.rename(columns={"Volume": "value"})
    return out[["time", "value", "color"]].to_dict("records")


def _line_data(df: pd.DataFrame, col: str) -> list[dict]:
    out = df[["Date", col]].dropna().copy()
    out["time"] = _to_time(out["Date"])
    out = out.rename(columns={col: "value"})
    return out[["time", "value"]].to_dict("records")


def hover_legend_data(df: pd.DataFrame) -> dict:
    """Podaci za hover-legendu (zadnji candle): OHLC, volumen, %change, smjer."""
    if df.empty:
        return {}
    last = df.iloc[-1]
    prev_close = df.iloc[-2]["Close"] if len(df) >= 2 else last["Close"]
    change_abs = last["Close"] - prev_close
    change_pct = (change_abs / prev_close * 100) if prev_close else 0.0
    is_buy = last["Close"] >= last["Open"]
    return {
        "date": last["Date"].strftime("%d.%m.%Y"),
        "open": float(last["Open"]),
        "high": float(last["High"]),
        "low": float(last["Low"]),
        "close": float(last["Close"]),
        "volume": float(last["Volume"]),
        "change_pct": float(change_pct),
        "direction": "BUY" if is_buy else "SELL",
        "is_buy": bool(is_buy),
    }


def _base_chart_layout() -> dict:
    return {
        "layout": {
            "background": {"type": "solid", "color": COLORS["background"]},
            "textColor": COLORS["text"],
        },
        "grid": {
            "vertLines": {"color": COLORS["grid"]},
            "horzLines": {"color": COLORS["grid"]},
        },
        "crosshair": {
            "mode": 1,
            "vertLine": {"color": COLORS["crosshair"], "width": 1, "style": 2},
            "horzLine": {"color": COLORS["crosshair"], "width": 1, "style": 2},
        },
        "rightPriceScale": {"borderColor": COLORS.get("border", COLORS["grid"]), "borderVisible": True},
        "timeScale": {"borderColor": COLORS.get("border", COLORS["grid"]), "borderVisible": True, "timeVisible": False, "rightOffset": 5},
        "handleScroll": True,
        "handleScale": True,
    }


def _candle_series(df: pd.DataFrame, indicators: dict) -> list[dict]:
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
        {
            "type": "Histogram",
            "data": _volume_data(df),
            "options": {"priceFormat": {"type": "volume"}, "priceScaleId": "volume"},
            "priceScale": {"scaleMargins": {"top": 0.8, "bottom": 0.0}},
        },
    ]
    line_colors = {"SMA": COLORS["sma"], "EMA": COLORS["ema"]}
    for col, enabled in indicators.items():
        if not enabled or col not in df.columns:
            continue
        prefix = col.split("_")[0]
        if prefix == "BB":
            is_middle = col.startswith("BB_middle")
            series.append({
                "type": "Line",
                "data": _line_data(df, col),
                "options": {
                    "color": COLORS["bollinger"],
                    "lineWidth": 1 if not is_middle else 2,
                    "lineStyle": 2 if is_middle else 0,
                    "priceLineVisible": False,
                    "lastValueVisible": False,
                    "title": col,
                },
            })
            continue
        if prefix not in line_colors:
            continue
        series.append({
            "type": "Line",
            "data": _line_data(df, col),
            "options": {
                "color": line_colors[prefix],
                "lineWidth": 2,
                "priceLineVisible": False,
                "lastValueVisible": True,
                "title": col,
            },
        })
    return series


def _rsi_pane(df: pd.DataFrame, height: int):
    rsi_col = next((c for c in df.columns if c.startswith("RSI_")), None)
    if rsi_col is None:
        return None
    layout = _base_chart_layout()
    layout["height"] = height
    return {
        "chart": layout,
        "series": [{
            "type": "Line",
            "data": _line_data(df, rsi_col),
            "options": {"color": "#b388ff", "lineWidth": 2, "priceLineVisible": False, "title": rsi_col},
        }],
    }


def _macd_pane(df: pd.DataFrame, height: int):
    if "MACD" not in df.columns:
        return None
    layout = _base_chart_layout()
    layout["height"] = height

    def _hist(col):
        out = df[["Date", col]].dropna().copy()
        out["time"] = _to_time(out["Date"])
        out["color"] = out[col].apply(lambda v: COLORS["volume_up"] if v >= 0 else COLORS["volume_down"])
        out = out.rename(columns={col: "value"})
        return out[["time", "value", "color"]].to_dict("records")

    return {
        "chart": layout,
        "series": [
            {"type": "Histogram", "data": _hist("MACD_hist"), "options": {"title": "MACD hist"}},
            {"type": "Line", "data": _line_data(df, "MACD"), "options": {"color": COLORS["sma"], "lineWidth": 2, "title": "MACD"}},
            {"type": "Line", "data": _line_data(df, "MACD_signal"), "options": {"color": COLORS["ema"], "lineWidth": 2, "title": "Signal"}},
        ],
    }


def _single_line_pane(df: pd.DataFrame, prefix: str, color: str, height: int):
    col = next((name for name in df.columns if name.startswith(prefix)), None)
    if col is None:
        return None
    layout = _base_chart_layout()
    layout["height"] = height
    return {
        "chart": layout,
        "series": [{
            "type": "Line",
            "data": _line_data(df, col),
            "options": {
                "color": color,
                "lineWidth": 2,
                "priceLineVisible": False,
                "title": col,
            },
        }],
    }


def _stochastic_pane(df: pd.DataFrame, height: int):
    k_col = next((name for name in df.columns if name.startswith("STOCH_K_")), None)
    d_col = next((name for name in df.columns if name.startswith("STOCH_D_")), None)
    if k_col is None or d_col is None:
        return None
    layout = _base_chart_layout()
    layout["height"] = height
    return {
        "chart": layout,
        "series": [
            {
                "type": "Line",
                "data": _line_data(df, k_col),
                "options": {
                    "color": COLORS["stochastic_k"],
                    "lineWidth": 2,
                    "priceLineVisible": False,
                    "title": "%K",
                },
            },
            {
                "type": "Line",
                "data": _line_data(df, d_col),
                "options": {
                    "color": COLORS["stochastic_d"],
                    "lineWidth": 2,
                    "priceLineVisible": False,
                    "title": "%D",
                },
            },
        ],
    }


def build_chart_config(df, indicators=None, main_height=480, sub_height=160):
    """SMA/EMA overlay na glavni pane; RSI i MACD zasebni paneli ispod."""
    indicators = indicators or {}
    main_layout = _base_chart_layout()
    main_layout["height"] = main_height
    charts = [{"chart": main_layout, "series": _candle_series(df, indicators)}]
    if indicators.get("RSI"):
        pane = _rsi_pane(df, sub_height)
        if pane:
            charts.append(pane)
    if indicators.get("MACD"):
        pane = _macd_pane(df, sub_height)
        if pane:
            charts.append(pane)
    if indicators.get("ATR"):
        pane = _single_line_pane(df, "ATR_", COLORS["atr"], sub_height)
        if pane:
            charts.append(pane)
    if indicators.get("Stochastic"):
        pane = _stochastic_pane(df, sub_height)
        if pane:
            charts.append(pane)
    if indicators.get("OBV"):
        pane = _single_line_pane(df, "OBV", COLORS["obv"], sub_height)
        if pane:
            charts.append(pane)
    return charts


def build_comparison_chart_config(comparison: pd.DataFrame, height: int = 260):
    """Normalizirani 7CRO i CROBEX10tr prinos, obje serije sa startom 100."""
    layout = _base_chart_layout()
    layout["height"] = height
    layout["rightPriceScale"]["scaleMargins"] = {"top": 0.15, "bottom": 0.15}
    return [{
        "chart": layout,
        "series": [
            {
                "type": "Line",
                "data": _line_data(comparison, "7CRO"),
                "options": {
                    "color": COLORS["sma"],
                    "lineWidth": 2,
                    "priceLineVisible": False,
                    "title": "7CRO",
                },
            },
            {
                "type": "Line",
                "data": _line_data(comparison, "CROBEX10tr"),
                "options": {
                    "color": COLORS["benchmark"],
                    "lineWidth": 2,
                    "priceLineVisible": False,
                    "title": "CROBEX10tr",
                },
            },
        ],
    }]


def build_multi_comparison_chart_config(comparison: pd.DataFrame, height: int = 340):
    """Dinamicki line chart za vise normaliziranih ZSE instrumenata."""
    palette = [
        COLORS["sma"],
        COLORS["benchmark"],
        COLORS["ema"],
        COLORS["up"],
        COLORS["obv"],
        COLORS["atr"],
    ]
    layout = _base_chart_layout()
    layout["height"] = height
    layout["rightPriceScale"]["scaleMargins"] = {"top": 0.12, "bottom": 0.12}
    series = []
    for index, col in enumerate(name for name in comparison.columns if name != "Date"):
        series.append(
            {
                "type": "Line",
                "data": _line_data(comparison, col),
                "options": {
                    "color": palette[index % len(palette)],
                    "lineWidth": 2,
                    "priceLineVisible": False,
                    "title": col,
                },
            }
        )
    return [{"chart": layout, "series": series}]
