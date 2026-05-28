"""
Metrics panel — kartice sa statistikama na vrhu dashboarda.
"""

from __future__ import annotations

import streamlit as st


def render_metrics(stats: dict) -> None:
    """Prikaže ključne metrike kao red st.metric kartica."""
    if not stats:
        st.warning("Nema podataka za prikaz statistika.")
        return

    c1, c2, c3, c4, c5 = st.columns(5)

    c1.metric(
        label="Zadnja cijena",
        value=f"{stats['last_price']:.2f} €",
        delta=f"{stats['change_abs']:+.2f} € ({stats['change_pct']:+.2f}%)",
    )
    c2.metric(
        label="52-tj. max",
        value=f"{stats['high_52w']:.2f} €",
    )
    c3.metric(
        label="52-tj. min",
        value=f"{stats['low_52w']:.2f} €",
    )
    c4.metric(
        label="Pros. volumen (30d)",
        value=f"{stats['avg_volume_30']:,.0f}",
    )
    c5.metric(
        label="Zadnji podatak",
        value=stats["last_date"].strftime("%d.%m.%Y"),
    )
