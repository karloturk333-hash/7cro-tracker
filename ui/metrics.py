"""
Metrics panel — custom kartice sa statistikama + legenda iznad grafa.

Vlastiti HTML/CSS umjesto st.metric za precizniju tipografiju:
male prigusene labele, krupne podebljane vrijednosti (TradingView-like).
"""

from __future__ import annotations

import math

import streamlit as st

from config.settings import COLORS


def _card(label, value, *, accent=None, sub=None):
    value_color = accent or COLORS["text"]
    sub_html = (
        f'<div class="metric-sub" style="color:{accent or COLORS["text_dim"]}">{sub}</div>'
        if sub else ""
    )
    return f"""
    <div class="metric-card">
        <div class="metric-label">{label}</div>
        <div class="metric-value" style="color:{value_color}">{value}</div>
        {sub_html}
    </div>
    """


def render_metrics(stats: dict) -> None:
    """Kljucne metrike kao red custom kartica."""
    if not stats:
        st.warning("Nema podataka za prikaz statistika.")
        return

    up = stats["change_abs"] >= 0
    accent = COLORS["up"] if up else COLORS["down"]
    arrow = "▲" if up else "▼"

    cards = [
        _card("ZADNJA CIJENA", f"{stats['last_price']:.2f} €", accent=accent,
              sub=f"{arrow} {stats['change_abs']:+.2f} € ({stats['change_pct']:+.2f}%)"),
        _card("52-TJ. MAKSIMUM", f"{stats['high_52w']:.2f} €"),
        _card("52-TJ. MINIMUM", f"{stats['low_52w']:.2f} €"),
        _card("PROS. VOLUMEN · 30D", f"{stats['avg_volume_30']:,.0f}"),
        _card("ZADNJI PODATAK", stats["last_date"].strftime("%d.%m.%Y"), accent=COLORS["text"]),
    ]

    css = f"""
    <style>
        .metric-row {{ display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 8px; }}
        .metric-card {{
            flex: 1; min-width: 150px; background: {COLORS['panel']};
            border: 1px solid {COLORS['grid']}; border-radius: 10px; padding: 14px 16px;
        }}
        .metric-label {{
            font-size: 11px; font-weight: 500; letter-spacing: 0.6px;
            color: {COLORS['text_dim']}; text-transform: uppercase; margin-bottom: 6px;
        }}
        .metric-value {{
            font-size: 26px; font-weight: 800; line-height: 1.1;
            font-variant-numeric: tabular-nums;
        }}
        .metric-sub {{
            font-size: 13px; font-weight: 600; margin-top: 4px;
            font-variant-numeric: tabular-nums;
        }}
    </style>
    """
    st.markdown(css + f'<div class="metric-row">{"".join(cards)}</div>', unsafe_allow_html=True)


def render_chart_legend(legend: dict) -> None:
    """TradingView-style legenda iznad grafa: OHLC + Volume + %change, buy/sell boja."""
    if not legend:
        return

    accent = COLORS["up"] if legend["is_buy"] else COLORS["down"]
    arrow = "▲" if legend["is_buy"] else "▼"

    def item(label, value, color=COLORS["text"]):
        return (
            f'<span class="leg-item"><span class="leg-k">{label}</span>'
            f'<span class="leg-v" style="color:{color}">{value}</span></span>'
        )

    html = f"""
    <style>
        .chart-legend {{
            display: flex; flex-wrap: wrap; align-items: center; gap: 16px;
            background: {COLORS['panel']}; border: 1px solid {COLORS['grid']};
            border-radius: 8px; padding: 8px 14px; margin-bottom: 6px;
            font-variant-numeric: tabular-nums;
        }}
        .leg-title {{ font-weight: 800; color: {COLORS['text']}; font-size: 14px; }}
        .leg-item {{ display: inline-flex; gap: 5px; align-items: baseline; }}
        .leg-k {{ font-size: 11px; color: {COLORS['text_dim']}; font-weight: 600; }}
        .leg-v {{ font-size: 14px; font-weight: 700; }}
        .leg-badge {{
            font-size: 11px; font-weight: 800; padding: 2px 8px;
            border-radius: 5px; color: #fff; background: {accent};
        }}
    </style>
    <div class="chart-legend">
        <span class="leg-title">7CRO · {legend['date']}</span>
        {item("O", f"{legend['open']:.2f}")}
        {item("H", f"{legend['high']:.2f}")}
        {item("L", f"{legend['low']:.2f}")}
        {item("C", f"{legend['close']:.2f}", accent)}
        {item("Vol", f"{legend['volume']:,.0f}")}
        {item("Promjena", f"{arrow} {legend['change_pct']:+.2f}%", accent)}
        <span class="leg-badge">{legend['direction']}</span>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


def render_market_intelligence(benchmark: dict, liquidity: dict) -> None:
    """Kartice relativnog prinosa i ZSE likvidnosti."""
    st.subheader("ZSE market intelligence")

    if benchmark:
        correlation = benchmark["correlation"]
        corr_text = f"{correlation:.2f}" if math.isfinite(correlation) else "n/a"
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("7CRO prinos", f"{benchmark['asset_return_pct']:+.2f}%")
        c2.metric("CROBEX10tr prinos", f"{benchmark['benchmark_return_pct']:+.2f}%")
        c3.metric(
            "Tracking razlika",
            f"{benchmark['tracking_difference_pct']:+.2f} p.p.",
            help="7CRO prinos minus prinos sluzbenog CROBEX10tr benchmarka.",
        )
        c4.metric("Dnevna korelacija", corr_text, help=f"{benchmark['sessions']} zajednickih sesija")

    if liquidity:
        l1, l2, l3, l4 = st.columns(4)
        premium = liquidity["close_vs_vwap_pct"]
        l1.metric(
            "Zadnji VWAP",
            f"{liquidity['last_vwap']:.2f} €",
            delta=f"{premium:+.2f}% close vs VWAP" if premium is not None else None,
        )
        l2.metric("Promet · 30D prosjek", f"{liquidity['avg_turnover_30']:,.0f} €")
        l3.metric("Transakcije · 30D prosjek", f"{liquidity['avg_trades_30']:.1f}")
        l4.metric("Prosj. vrijednost transakcije", f"{liquidity['avg_trade_value_30']:,.0f} €")
