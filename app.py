"""
7CRO Tracker Dashboard — Streamlit entry point.

Pokretanje:
    streamlit run app.py
"""

from __future__ import annotations

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from config.settings import COLORS, ETF_ISIN, ETF_NAME, ETF_TICKER
from core.indicators import add_ema, add_macd, add_rsi, add_sma
from core.stats import compute_stats
from data.loaders import get_data
from ui.charts import build_chart_config, hover_legend_data
from ui.metrics import render_chart_legend, render_metrics
from ui.sidebar import render_sidebar

from streamlit_lightweight_charts import renderLightweightCharts


st.set_page_config(
    page_title=f"{ETF_TICKER} Tracker",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)


@st.cache_data(show_spinner="Ucitavam podatke...")
def _load(_uploaded, try_yf: bool):
    return get_data(uploaded_file=_uploaded, try_yfinance=try_yf)


def _filter_period(df: pd.DataFrame, period: str) -> pd.DataFrame:
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


def _base_css() -> None:
    st.markdown(
        f"""
        <style>
            .stApp {{ background-color: {COLORS['background']}; }}
            section[data-testid="stSidebar"] {{ background-color: {COLORS['panel']}; }}
            h1, h2, h3, p, label {{ color: {COLORS['text']}; }}
            iframe {{
                border: 1px solid {COLORS.get('border', COLORS['grid'])} !important;
                border-radius: 10px !important;
            }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def _fullscreen_css() -> None:
    """Sakrij SVE osim grafa i razvuci ga preko cijelog prozora."""
    st.markdown(
        """
        <style>
            #MainMenu, header, footer {visibility: hidden;}
            section[data-testid="stSidebar"] {display: none !important;}
            div[data-testid="stToolbar"] {display: none !important;}
            .block-container {
                padding: 0.5rem !important;
                max-width: 100% !important;
            }
            iframe { border: none !important; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _request_browser_fullscreen() -> None:
    """Pozovi browserov Fullscreen API na cijelu Streamlit stranicu."""
    components.html(
        """
        <script>
            const doc = window.parent.document;
            const el = doc.documentElement;
            if (!doc.fullscreenElement && el.requestFullscreen) {
                el.requestFullscreen().catch(() => {});
            }
        </script>
        """,
        height=0,
    )


def main() -> None:
    if "fullscreen" not in st.session_state:
        st.session_state.fullscreen = False
    fs = st.session_state.fullscreen

    _base_css()
    if fs:
        _fullscreen_css()

    opts = render_sidebar()

    df, source = _load(opts["uploaded"], opts["try_yfinance"])
    df = _filter_period(df, opts["period"])

    indicators = {}
    if opts["show_sma"]:
        df = add_sma(df, opts["sma_period"])
        indicators[f"SMA_{opts['sma_period']}"] = True
    if opts["show_ema"]:
        df = add_ema(df, opts["ema_period"])
        indicators[f"EMA_{opts['ema_period']}"] = True
    if opts["show_rsi"]:
        df = add_rsi(df)
        indicators["RSI"] = True
    if opts["show_macd"]:
        df = add_macd(df)
        indicators["MACD"] = True

    stats = compute_stats(df)

    if df.empty:
        st.error("Nema podataka za prikaz.")
        return

    legend = hover_legend_data(df)

    if not fs:
        st.title(f"📈 {ETF_TICKER} — {ETF_NAME}")
        st.caption(f"ISIN: {ETF_ISIN}  •  Izvor: {source}  •  Sve cijene u EUR")
        render_metrics(stats)
        st.divider()

    legend_col, btn_col = st.columns([5, 1])
    with legend_col:
        render_chart_legend(legend)
    with btn_col:
        label = "↙ Izlaz" if fs else "⛶ Fullscreen"
        if st.button(label, use_container_width=True):
            st.session_state.fullscreen = not fs
            st.rerun()

    if fs:
        chart_config = build_chart_config(df, indicators, main_height=760, sub_height=200)
    else:
        chart_config = build_chart_config(df, indicators, main_height=500, sub_height=170)
    renderLightweightCharts(chart_config, key="main_chart")

    # Pravi browser fullscreen kad je mod ukljucen
    if fs:
        _request_browser_fullscreen()
    else:
        st.caption(
            "HRK cijene (do 31.12.2022.) konvertirane u EUR po fiksnom tecaju 7,53450. "
            "Podaci: Zagreb Stock Exchange (ZSE). Projekt nije povezan s InterCapitalom."
        )


if __name__ == "__main__":
    main()
