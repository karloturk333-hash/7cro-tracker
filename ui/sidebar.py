"""
Sidebar kontrole — upload, izbor izvora, indikatori, vremenski raspon.
Vraća dict s odabranim postavkama koje app.py prosljeđuje dalje.
"""

from __future__ import annotations

import streamlit as st

from config.settings import (
    DEFAULT_EMA_PERIOD,
    DEFAULT_SMA_PERIOD,
    ETF_NAME,
    ETF_TICKER,
)


def render_sidebar() -> dict:
    st.sidebar.title(f"⚙️ {ETF_TICKER} Tracker")
    st.sidebar.caption(ETF_NAME)

    st.sidebar.divider()

    # --- Izvor podataka ---
    st.sidebar.subheader("Podaci")
    uploaded = st.sidebar.file_uploader(
        "Uploadaj ZSE CSV (ili ostavi prazno za ugrađene podatke)",
        type=["csv"],
    )
    try_yf = st.sidebar.checkbox("Pokušaj yfinance (eksperimentalno)", value=False)
    refresh = st.sidebar.button("🔄 Osvježi podatke", use_container_width=True)

    st.sidebar.divider()

    # --- Vremenski raspon ---
    st.sidebar.subheader("Razdoblje")
    period = st.sidebar.selectbox(
        "Prikaži",
        options=["Sve", "5 godina", "1 godina", "6 mjeseci", "3 mjeseca", "1 mjesec"],
        index=0,
    )

    st.sidebar.divider()

    # --- Indikatori ---
    st.sidebar.subheader("Indikatori")
    show_sma = st.sidebar.checkbox("SMA", value=True)
    sma_period = st.sidebar.number_input(
        "SMA period", min_value=2, max_value=200, value=DEFAULT_SMA_PERIOD, step=1
    )
    show_ema = st.sidebar.checkbox("EMA", value=True)
    ema_period = st.sidebar.number_input(
        "EMA period", min_value=2, max_value=200, value=DEFAULT_EMA_PERIOD, step=1
    )

    # Oscilatori u zasebnim panelima (v2)
    show_rsi = st.sidebar.checkbox("RSI (zaseban panel)", value=True)
    show_macd = st.sidebar.checkbox("MACD (zaseban panel)", value=True)

    st.sidebar.divider()

    # --- Prikaz ---
    st.sidebar.subheader("Prikaz")
    fullscreen = st.sidebar.toggle(
        "🖥️ Fullscreen graf",
        value=False,
        help="Sakrij statistike i proširi graf preko cijelog ekrana",
    )

    return {
        "uploaded": uploaded,
        "try_yfinance": try_yf,
        "refresh": refresh,
        "period": period,
        "show_sma": show_sma,
        "sma_period": int(sma_period),
        "show_ema": show_ema,
        "ema_period": int(ema_period),
        "show_rsi": show_rsi,
        "show_macd": show_macd,
    }
