"""
Testovi za data layer — najvažniji dio (rukovanje pravim ZSE formatom).
"""

import pandas as pd

from config.settings import HRK_TO_EUR, OHLCV_COLUMNS
from data.loaders import _read_zse_csv, _read_zse_index_csv, _read_zse_market_csv, normalize_df


def test_zse_columns_standardized(raw_zse_csv):
    """Nakon učitavanja, kolone moraju biti točno standardni OHLCV set."""
    df = _read_zse_csv(raw_zse_csv)
    assert list(df.columns) == OHLCV_COLUMNS


def test_otc_rows_filtered_out(raw_zse_csv):
    """OTC redovi se izbacuju — ostaju samo CT (2 reda u fixtureu)."""
    df = _read_zse_csv(raw_zse_csv)
    assert len(df) == 2  # 1 EUR CT + 1 HRK CT, OTC izbačen


def test_no_duplicate_dates(raw_zse_csv):
    """Ne smije biti duplih datuma (OTC je dijelio datum s CT redom)."""
    df = _read_zse_csv(raw_zse_csv)
    assert df["Date"].duplicated().sum() == 0


def test_hrk_converted_to_eur(raw_zse_csv):
    """HRK cijena (101,70) mora biti podijeljena fiksnim tečajem."""
    df = _read_zse_csv(raw_zse_csv)
    hrk_row = df[df["Date"] == pd.Timestamp("2020-11-17")].iloc[0]
    expected = 101.70 / HRK_TO_EUR
    assert abs(hrk_row["Close"] - expected) < 0.001


def test_eur_rows_unchanged(raw_zse_csv):
    """EUR cijena (37,61) ostaje nepromijenjena."""
    df = _read_zse_csv(raw_zse_csv)
    eur_row = df[df["Date"] == pd.Timestamp("2026-05-28")].iloc[0]
    assert abs(eur_row["Close"] - 37.61) < 0.001


def test_sorted_ascending(raw_zse_csv):
    """Podaci moraju biti sortirani uzlazno po datumu."""
    df = _read_zse_csv(raw_zse_csv)
    assert df["Date"].is_monotonic_increasing


def test_no_nan_in_ohlc(raw_zse_csv):
    """Nakon normalizacije nema NaN u OHLC kolonama."""
    df = _read_zse_csv(raw_zse_csv)
    assert df[["Open", "High", "Low", "Close"]].isna().sum().sum() == 0


def test_normalize_handles_missing_volume():
    """normalize_df: nedostajući volumen postaje 0, ne ruši se."""
    df = pd.DataFrame(
        {
            "Date": ["2024-01-01"],
            "Open": [10.0],
            "High": [11.0],
            "Low": [9.0],
            "Close": [10.5],
            "Volume": [None],
        }
    )
    out = normalize_df(df)
    assert out["Volume"].iloc[0] == 0


def test_market_loader_keeps_vwap_turnover_and_trades(raw_zse_csv):
    market = _read_zse_market_csv(raw_zse_csv)
    eur = market[market["Date"] == pd.Timestamp("2026-05-28")].iloc[0]
    assert eur["VWAP"] == 37.77
    assert eur["Turnover"] == 4344.60
    assert eur["NumTrades"] == 4


def test_market_loader_converts_hrk_turnover(raw_zse_csv):
    market = _read_zse_market_csv(raw_zse_csv)
    hrk = market[market["Date"] == pd.Timestamp("2020-11-17")].iloc[0]
    assert abs(hrk["Turnover"] - 3384521.40 / HRK_TO_EUR) < 0.01


def test_index_loader_accepts_api_csv():
    import io

    raw = (
        '"mic","symbol","isin","date","open_value","high_value","low_value",'
        '"last_value","change_prev_close_percentage","turnover"\n'
        '"XZAG","C10TR","HRZB00ICB103","2026-08-07",3397.96,3403.57,'
        '3383.74,3390.97,-0.13,3694307.10\n'
    ).encode()
    benchmark = _read_zse_index_csv(io.BytesIO(raw))
    assert list(benchmark.columns) == OHLCV_COLUMNS
    assert benchmark.iloc[0]["Close"] == 3390.97
