"""
7CRO Tracker Dashboard — Streamlit entry point.

Pokretanje:
    streamlit run app.py

Orkestrira sve slojeve:
    sidebar (kontrole) -> loaders (podaci) -> indicators/stats -> charts/metrics
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from config.settings import COLORS, ETF_ISIN, ETF_NAME, ETF_TICKER
from core.indicators import add_ema, add_sma
from core.stats import compute_stats
from data.loaders import get_data
from ui.charts import build_chart_config
from ui.metrics import render_metrics
from ui.sidebar import render_sidebar

# streamlit-lightweight-charts renderer
from streamlit_lightweight_charts import renderLightweightCharts


# --- Page config ---
st.set_page_config(
    page_title=f"{ETF_TICKER} Tracker",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)


# --- Cache: učitavanje + procesiranje podataka ---
@st.cache_data(show_spinner="Učitavam podatke…")
def _load(_uploaded, try_yf: bool):
    """Cache-irani dohvat. _uploaded ima _ prefiks da ga Streamlit ne hashira."""
    return get_data(uploaded_file=_uploaded, try_yfinance=try_yf)


def _filter_period(df: pd.DataFrame, period: str) -> pd.DataFrame:
    """Odsiječe DataFrame na odabrani vremenski raspon."""
    if period == "Sve" or df.empty:
        return df
    last_date = df["Date"].max()
    deltas = {
        "5 godina": pd.DateOffset(years=5),
        "1 godina": pd.DateOffset(years=1),
        "6 mjeseci": pd.DateOffset(months=6),
        "3 mjeseca": pd.DateOffset(months=3),
        "1 mjesec": pd.DateOffset(months=1),
    }
    cutoff = last_date - deltas[period]
    return df[df["Date"] >= cutoff].reset_index(drop=True)


def _custom_css() -> None:
    """Dark theme dorade preko Streamlita."""
    st.markdown(
        f"""
        <style>
            .stApp {{ background-color: {COLORS['background']}; }}
            section[data-testid="stSidebar"] {{ background-color: {COLORS['panel']}; }}
            h1, h2, h3, p, label {{ color: {COLORS['text']}; }}
            [data-testid="stMetricValue"] {{ color: {COLORS['text']}; }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def main() -> None:
    _custom_css()
    opts = render_sidebar()

    # 1) Podaci
    df, source = _load(opts["uploaded"], opts["try_yfinance"])
    df = _filter_period(df, opts["period"])

    # 2) Indikatori (na temelju odabira u sidebaru)
    indicators = {}
    if opts["show_sma"]:
        df = add_sma(df, opts["sma_period"])
        indicators[f"SMA_{opts['sma_period']}"] = True
    if opts["show_ema"]:
        df = add_ema(df, opts["ema_period"])
        indicators[f"EMA_{opts['ema_period']}"] = True

    # 3) Statistike
    stats = compute_stats(df)

    # --- Header ---
    st.title(f"📈 {ETF_TICKER} — {ETF_NAME}")
    st.caption(f"ISIN: {ETF_ISIN}  •  Izvor: {source}  •  Sve cijene u EUR")

    # --- Metrics ---
    render_metrics(stats)
    st.divider()

    # --- Glavni graf ---
    if df.empty:
        st.error("Nema podataka za prikaz.")
        return

    chart_config = build_chart_config(df, indicators)
    renderLightweightCharts(chart_config, key="main_chart")

    # --- Footer ---
    st.caption(
        "HRK cijene (do 31.12.2022.) konvertirane u EUR po fiksnom tečaju 7,53450. "
        "Podaci: Zagreb Stock Exchange (ZSE). Projekt nije povezan s InterCapitalom."
    )


if __name__ == "__main__":
    main()
