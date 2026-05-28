"""
Pytest fixtures — zajednički test podaci.
"""

import io

import pandas as pd
import pytest


@pytest.fixture
def raw_zse_csv() -> io.BytesIO:
    """
    Minimalni ZSE CSV: par CT redova (HRK i EUR) + jedan OTC red.
    Replicira pravi ZSE format (sep=';', decimalni zarez, navodnici).
    """
    text = (
        '"mic";"symbol";"isin";"date";"trading_model_id";"open_price";'
        '"high_price";"low_price";"last_price";"vwap_price";'
        '"change_prev_close_percentage";"num_trades";"volume";"turnover";'
        '"price_currency";"turnover_currency"\n'
        # EUR red
        '"XZAG";"7CRO";"HRICAMFCR102";"2026-05-28";"CT";37,90;37,90;37,61;'
        '37,61;37,77;-0,50;4;115,00000;4344,60;"EUR";"EUR"\n'
        # OTC red (treba biti FILTRIRAN van)
        '"XZAG";"7CRO";"HRICAMFCR102";"2026-05-28";"OTC";;37,63;37,56;'
        '37,63;37,61;;2;679,00000;25542,30;"EUR";"EUR"\n'
        # HRK red (treba biti KONVERTIRAN u EUR)
        '"XZAG";"7CRO";"HRICAMFCR102";"2020-11-17";"CT";100,20;101,70;100,10;'
        '101,70;100,38;;39;33715,00000;3384521,40;"HRK";"HRK"\n'
    )
    return io.BytesIO(text.encode("utf-8"))


@pytest.fixture
def ohlcv_df() -> pd.DataFrame:
    """Čisti normalizirani OHLCV DataFrame za testiranje indikatora/statistika."""
    dates = pd.date_range("2024-01-01", periods=60, freq="D")
    close = pd.Series(range(10, 70), dtype=float)  # rastući trend 10..69
    return pd.DataFrame(
        {
            "Date": dates,
            "Open": close - 0.5,
            "High": close + 1.0,
            "Low": close - 1.0,
            "Close": close,
            "Volume": pd.Series(range(100, 160), dtype=float),
        }
    )
