"""
Backtest stranica — SMA crossover strategija vs Buy & Hold.

Vizualno prikazuje equity krivulje i kljucne metrike.
Pristupa se iz sidebara (Streamlit multi-page).
"""

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config.settings import COLORS, ETF_TICKER  # noqa: E402
from data.loaders import get_data  # noqa: E402
from quant.backtest import equity_curves, run_backtest  # noqa: E402

st.set_page_config(page_title=f"{ETF_TICKER} Backtest", page_icon="📊", layout="wide")

st.markdown(
    f"<style>.stApp {{background-color:{COLORS['background']};}}</style>",
    unsafe_allow_html=True,
)

st.title("📊 Backtest — SMA Crossover")
st.caption(
    "Strategija: kupi kad brza SMA prijede iznad spore, prodaj kad padne ispod. "
    "Usporedba s Buy & Hold. Bez look-ahead bias-a (trguje se sljedeci dan)."
)

# --- Kontrole ---
c1, c2 = st.columns(2)
fast = c1.slider("Brza SMA (dana)", 5, 100, 20, step=5)
slow = c2.slider("Spora SMA (dana)", 20, 250, 50, step=10)

if fast >= slow:
    st.warning("Brza SMA mora biti manja od spore.")
    st.stop()

# --- Podaci + backtest ---
df, source = get_data()
res = run_backtest(df, fast=fast, slow=slow)
curves = equity_curves(df, fast=fast, slow=slow).set_index("Date")

# --- Metrike ---
m1, m2, m3, m4 = st.columns(4)
m1.metric("Strategija", f"{res['strategy_return']:+.1f}%")
m2.metric("Buy & Hold", f"{res['buyhold_return']:+.1f}%")
m3.metric("Broj trejdova", res["n_trades"])
m4.metric("Max drawdown", f"{res['max_drawdown']:.1f}%")

winner = "✅ Strategija je nadmasila Buy & Hold" if res["win"] else "ℹ️ Buy & Hold je bio bolji u ovom razdoblju"
st.info(winner)

# --- Equity krivulje ---
st.subheader("Equity krivulje (start = 100)")
st.line_chart(curves, color=[COLORS["ema"], COLORS["sma"]])

st.caption(
    f"Izvor: {source}. Edukativni primjer — proslost ne garantira buducnost. "
    "Backtest ne ukljucuje provizije ni slippage."
)
