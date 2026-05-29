"""
Inkrementalni update 7CRO podataka sa ZSE REST API-ja.

Pokrece se rucno ili preko GitHub Actions crona. Povuce zadnjih ~40 dana,
spoji sa postojecim data/sample/7cro_zse.csv (cuva povijest od 2020),
i spremi natrag u istom sirovom ZSE formatu.

Pokretanje:
    python scripts/fetch_zse.py
"""

from __future__ import annotations

import io
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config.settings import ETF_ISIN, SAMPLE_CSV  # noqa: E402
from data.zse_api import MARKET_CLOSE_HOUR, build_url  # noqa: E402

LOOKBACK_DAYS = 40


def _read_raw_zse(source) -> pd.DataFrame:
    return pd.read_csv(source, sep=";", dtype=str, quotechar='"')


def fetch_recent_raw() -> pd.DataFrame:
    import requests

    today = date.today()
    date_from = (today - timedelta(days=LOOKBACK_DAYS)).isoformat()
    date_to = today.isoformat()
    url = build_url(ETF_ISIN, date_from, date_to, fmt="csv")
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    return _read_raw_zse(io.BytesIO(resp.content))


def drop_unfinished_today_raw(df: pd.DataFrame, now=None) -> pd.DataFrame:
    if df is None or df.empty or "date" not in df.columns:
        return df
    if now is None:
        now = datetime.now()
    if now.hour < MARKET_CLOSE_HOUR:
        df = df[df["date"] != now.date().isoformat()]
    return df.reset_index(drop=True)


def merge_raw(existing: pd.DataFrame, recent: pd.DataFrame) -> pd.DataFrame:
    if recent is None or recent.empty:
        return existing
    combined = pd.concat([existing, recent], ignore_index=True)
    key = ["date", "trading_model_id"] if "trading_model_id" in combined.columns else ["date"]
    combined = combined.drop_duplicates(subset=key, keep="last")
    combined = combined.sort_values("date", ascending=False).reset_index(drop=True)
    return combined


def main() -> int:
    csv_path = Path(SAMPLE_CSV)
    existing = _read_raw_zse(csv_path)
    before = len(existing)

    try:
        recent = fetch_recent_raw()
    except Exception as exc:
        print("[fetch_zse] API greska:", exc, "- postojeci podaci ostaju.")
        return 0

    recent = drop_unfinished_today_raw(recent)
    merged = merge_raw(existing, recent)
    added = len(merged) - before

    if added <= 0:
        print("[fetch_zse] Nema novih redaka (ukupno", len(merged), ").")
        return 0

    merged.to_csv(csv_path, sep=";", index=False, quotechar='"')
    print("[fetch_zse] Dodano", added, "novih redaka (ukupno", len(merged), ").")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
