"""
Data layer — jedina točka koja zna ODAKLE podaci dolaze.

Svaki izvor (uploadani CSV, ZSE sample CSV, yfinance) prolazi kroz
`normalize_df()` koji garantira identičan oblik podataka:
kolone [Date, Open, High, Low, Close, Volume], sortirano uzlazno,
bez NaN u OHLC, cijene u EUR.

Tako ostatak aplikacije (indikatori, statistike, graf) nikad ne
mora brinuti o formatu izvora.
"""

from __future__ import annotations

import io
from pathlib import Path

import pandas as pd

from config.settings import (
    HRK_TO_EUR,
    OHLCV_COLUMNS,
    SAMPLE_CSV,
    YFINANCE_TICKER,
)

# ZSE export koristi ove nazive kolona (mala slova, snake_case).
_ZSE_RENAME = {
    "date": "Date",
    "open_price": "Open",
    "high_price": "High",
    "low_price": "Low",
    "last_price": "Close",  # ZSE "last_price" = dnevni close
    "volume": "Volume",
}


def normalize_df(df: pd.DataFrame) -> pd.DataFrame:
    """
    Privede bilo koji DataFrame na standardni OHLCV oblik.

    Pretpostavlja da kolone već postoje pod standardnim imenima
    (Date, Open, High, Low, Close, Volume). Čisti NaN, sortira,
    uklanja duple datume.
    """
    df = df.copy()

    # Date u datetime
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")

    # Numeričke kolone u float
    for col in ["Open", "High", "Low", "Close", "Volume"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # OHLC mora biti potpun; volumen koji fali tretiramo kao 0
    df = df.dropna(subset=["Date", "Open", "High", "Low", "Close"])
    df["Volume"] = df["Volume"].fillna(0)

    # Sortiraj uzlazno i makni duple datume (zadrži zadnji)
    df = df.sort_values("Date").drop_duplicates(subset="Date", keep="last")

    df = df[OHLCV_COLUMNS].reset_index(drop=True)
    return df


def _read_zse_csv(source) -> pd.DataFrame:
    """
    Učita sirovi ZSE CSV (sep=';', decimalni zarez, navodnici)
    i privede ga na standardni OHLCV oblik s HRK->EUR konverzijom.

    `source` može biti putanja ili file-like objekt (Streamlit upload).
    """
    raw = pd.read_csv(
        source,
        sep=";",
        decimal=",",
        thousands=None,
        quotechar='"',
        dtype=str,  # čitamo kao string pa sami konvertiramo (sigurnije za zarez)
    )

    # ZSE ima i CT (continuous trading) i OTC (blok poslovi) redove.
    # Za graf koristimo samo CT — OTC nemaju open i dupliciraju datume.
    if "trading_model_id" in raw.columns:
        raw = raw[raw["trading_model_id"] == "CT"].copy()

    # Pretvori decimalni zarez u točku za cijene/volumen
    price_cols = ["open_price", "high_price", "low_price", "last_price", "volume"]
    for col in price_cols:
        if col in raw.columns:
            raw[col] = (
                raw[col]
                .astype(str)
                .str.replace(".", "", regex=False)   # makni eventualni separator tisuća
                .str.replace(",", ".", regex=False)   # zarez -> točka
            )
            raw[col] = pd.to_numeric(raw[col], errors="coerce")

    # HRK -> EUR konverzija po fiksnom tečaju.
    # ZSE označava valutu po retku u koloni price_currency.
    if "price_currency" in raw.columns:
        hrk_mask = raw["price_currency"] == "HRK"
        for col in ["open_price", "high_price", "low_price", "last_price"]:
            raw.loc[hrk_mask, col] = raw.loc[hrk_mask, col] / HRK_TO_EUR

    # Preimenuj u standardna imena i normaliziraj
    df = raw.rename(columns=_ZSE_RENAME)
    return normalize_df(df)


def load_zse_sample() -> pd.DataFrame:
    """Učita ugrađeni ZSE sample CSV (uvijek dostupan)."""
    return _read_zse_csv(SAMPLE_CSV)


def load_uploaded_csv(uploaded_file) -> pd.DataFrame:
    """
    Učita CSV koji je korisnik uploadao kroz Streamlit.

    Prvo pokuša ZSE format; ako padne, pokuša generički OHLCV CSV
    (standardni format s engleskim/točka-decimal).
    """
    content = uploaded_file.getvalue()
    try:
        return _read_zse_csv(io.BytesIO(content))
    except Exception:
        # Fallback: generički CSV s kolonama Date,Open,High,Low,Close,Volume
        df = pd.read_csv(io.BytesIO(content))
        df.columns = [c.strip().capitalize() for c in df.columns]
        return normalize_df(df)


def load_yfinance(ticker: str = YFINANCE_TICKER) -> pd.DataFrame | None:
    """
    Pokuša dohvatiti podatke s yfinance.
    Vraća None ako nema podataka ili dođe do greške
    (za 7CRO je pokrivenost slaba, pa je ovo samo bonus).
    """
    try:
        import yfinance as yf

        data = yf.download(ticker, period="max", progress=False, auto_adjust=False)
        if data is None or data.empty:
            return None
        data = data.reset_index()
        # yfinance ume vratiti MultiIndex kolone — splošti ih
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = [c[0] for c in data.columns]
        return normalize_df(data)
    except Exception:
        return None


def get_data(uploaded_file=None, try_yfinance: bool = False) -> tuple[pd.DataFrame, str]:
    """
    Glavni orkestrator. Prioritet izvora:
        1. Uploadani CSV (ako postoji)
        2. yfinance (samo ako je eksplicitno traženo i uspije)
        3. Ugrađeni ZSE sample (uvijek radi)

    Vraća (DataFrame, opis_izvora).
    """
    if uploaded_file is not None:
        df = load_uploaded_csv(uploaded_file)
        if not df.empty:
            return df, f"Uploadani CSV ({uploaded_file.name})"

    if try_yfinance:
        df = load_yfinance()
        if df is not None and not df.empty:
            return df, f"yfinance ({YFINANCE_TICKER})"

    return load_zse_sample(), "ZSE sample (ugrađeni)"
