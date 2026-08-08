"""Inkrementalno osvjezavanje sluzbene CROBEX10tr povijesti sa ZSE-a."""

from __future__ import annotations

import io
import sys
import time
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config.settings import (  # noqa: E402
    BENCHMARK_CSV,
    BENCHMARK_ISIN,
    ZSE_API_BASE,
    ZSE_MIC,
)
from data.zse_api import MARKET_CLOSE_HOUR  # noqa: E402

INDEX_COLS = [
    "mic",
    "symbol",
    "isin",
    "date",
    "open_value",
    "high_value",
    "low_value",
    "last_value",
    "change_prev_close_percentage",
    "turnover",
]
DECIMAL_COLS = INDEX_COLS[4:]
LOOKBACK_DAYS = 40
FETCH_RETRIES = 3


def _read(source) -> pd.DataFrame:
    raw = source.read() if hasattr(source, "read") else Path(source).read_bytes()
    text = raw.decode("utf-8") if isinstance(raw, bytes) else raw
    first_line = text.splitlines()[0] if text else ""
    separator = ";" if ";" in first_line else ","
    return pd.read_csv(io.StringIO(text), sep=separator, dtype=str, quotechar='"')


def canonicalize(df: pd.DataFrame, *, from_api: bool) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame(columns=INDEX_COLS)
    if not set(INDEX_COLS).issubset(df.columns):
        missing = sorted(set(INDEX_COLS) - set(df.columns))
        raise ValueError(f"Index CSV nema trazene kolone: {', '.join(missing)}")
    out = df[INDEX_COLS].copy()
    if from_api:
        for col in DECIMAL_COLS:
            out[col] = out[col].fillna("").astype(str).str.replace(".", ",", regex=False)
    out = out[out["date"].notna() & (out["date"].str.strip() != "")]
    return out.reset_index(drop=True)


def serialize(df: pd.DataFrame) -> str:
    return df.to_csv(index=False, sep=";", quotechar='"')


def build_index_url(date_from: str, date_to: str) -> str:
    return (
        f"{ZSE_API_BASE}/index-history/{ZSE_MIC}/{BENCHMARK_ISIN}/"
        f"{date_from}/{date_to}/csv?language=EN"
    )


def fetch_recent() -> pd.DataFrame:
    today = date.today()
    date_from = (today - timedelta(days=LOOKBACK_DAYS)).isoformat()
    url = build_index_url(date_from, today.isoformat())
    last_error = None
    for attempt in range(1, FETCH_RETRIES + 1):
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            result = canonicalize(_read(io.BytesIO(response.content)), from_api=True)
            if result.empty:
                raise ValueError("ZSE index-history odgovor nema valjanih redaka")
            return result
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            print(f"[fetch_zse_index] Pokusaj {attempt}/{FETCH_RETRIES} pao: {exc}")
            if attempt < FETCH_RETRIES:
                time.sleep(2 ** attempt)
    raise RuntimeError(f"CROBEX10tr dohvat nije uspio: {last_error}")


def drop_unfinished_today(df: pd.DataFrame, now=None) -> pd.DataFrame:
    now = now or datetime.now()
    if now.hour < MARKET_CLOSE_HOUR:
        df = df[df["date"] != now.date().isoformat()]
    return df.reset_index(drop=True)


def merge(existing: pd.DataFrame, recent: pd.DataFrame) -> pd.DataFrame:
    combined = pd.concat([existing, recent], ignore_index=True)
    return (
        combined.drop_duplicates(subset=["date"], keep="last")
        .sort_values("date", ascending=False)
        .reset_index(drop=True)
    )


def main() -> int:
    path = Path(BENCHMARK_CSV)
    old_text = path.read_text()
    existing = canonicalize(_read(path), from_api=False)
    try:
        recent = drop_unfinished_today(fetch_recent())
    except Exception as exc:  # noqa: BLE001
        print(f"[fetch_zse_index] GRESKA: {exc}", file=sys.stderr)
        return 1

    updated = serialize(merge(existing, recent))
    if updated == old_text:
        print(f"[fetch_zse_index] Nema promjena; zadnji datum {existing['date'].max()}.")
        return 0
    path.write_text(updated)
    print(f"[fetch_zse_index] Podaci azurirani; zadnji datum {recent['date'].max()}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
