"""
Inkrementalni update 7CRO podataka sa ZSE REST API-ja.

Pokrece se rucno ili preko GitHub Actions crona. Povuce zadnjih ~40 dana,
spoji sa postojecim data/sample/7cro_zse.csv (cuva povijest od 2020),
i spremi natrag u istom sirovom ZSE formatu.

Promjena se detektira po STVARNOM sadrzaju (ne samo broju redaka), pa se
update zapise i kad se postojeci redak korigira (npr. zavrsni close).
Prava API/parsiranje greska vraca non-zero exit da workflow padne (crveno)
i da staro "tiho zastarijevanje" podataka bude vidljivo.

Pokretanje:
    python scripts/fetch_zse.py
"""

from __future__ import annotations

import io
import sys
import time
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config.settings import ETF_ISIN, SAMPLE_CSV  # noqa: E402
from data.zse_api import MARKET_CLOSE_HOUR, build_url  # noqa: E402

LOOKBACK_DAYS = 40
FETCH_RETRIES = 3
RETRY_BACKOFF_S = 2  # 2s, 4s, 8s ...

CSV_KWARGS = dict(sep=";", quotechar='"')


def _read_raw_zse(source) -> pd.DataFrame:
    return pd.read_csv(source, dtype=str, **CSV_KWARGS)


def serialize_raw(df: pd.DataFrame) -> str:
    """Serijaliziraj df u isti sirovi ZSE CSV format koji drzimo u repou."""
    return df.to_csv(index=False, **CSV_KWARGS)


def fetch_recent_raw() -> pd.DataFrame:
    """Dohvati zadnjih LOOKBACK_DAYS s API-ja. Retry uz backoff; baca iznimku
    ako i nakon svih pokusaja ne uspije (da pozivatelj zna da je PRAVA greska)."""
    import requests

    today = date.today()
    date_from = (today - timedelta(days=LOOKBACK_DAYS)).isoformat()
    date_to = today.isoformat()
    url = build_url(ETF_ISIN, date_from, date_to, fmt="csv")
    print(f"[fetch_zse] Dohvacam {date_from} -> {date_to}")

    last_exc: Exception | None = None
    for attempt in range(1, FETCH_RETRIES + 1):
        try:
            resp = requests.get(url, timeout=30)
            resp.raise_for_status()
            df = _read_raw_zse(io.BytesIO(resp.content))
            print(f"[fetch_zse] API vratio {len(df)} redaka.")
            return df
        except Exception as exc:  # noqa: BLE001 - zelimo retryati sve
            last_exc = exc
            print(f"[fetch_zse] Pokusaj {attempt}/{FETCH_RETRIES} pao: {exc}")
            if attempt < FETCH_RETRIES:
                time.sleep(RETRY_BACKOFF_S * (2 ** (attempt - 1)))

    raise RuntimeError(f"ZSE API nedostupan nakon {FETCH_RETRIES} pokusaja: {last_exc}")


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


def _max_date(df: pd.DataFrame) -> str:
    if df is None or df.empty or "date" not in df.columns:
        return "n/a"
    col = df["date"].dropna()
    return col.max() if not col.empty else "n/a"


def main() -> int:
    csv_path = Path(SAMPLE_CSV)
    old_text = csv_path.read_text()
    existing = _read_raw_zse(csv_path)
    print(f"[fetch_zse] CSV ima {len(existing)} redaka, zadnji datum {_max_date(existing)}.")

    try:
        recent = fetch_recent_raw()
    except Exception as exc:  # noqa: BLE001
        # PRAVA greska (mreza / API / format) -> padni glasno (crveno u CI-ju),
        # ne tretiraj kao "nema promjena". Stari podaci ostaju netaknuti.
        print("[fetch_zse] GRESKA pri dohvatu:", exc, file=sys.stderr)
        return 1

    recent = drop_unfinished_today_raw(recent)
    print(f"[fetch_zse] Nakon API-ja zadnji datum je {_max_date(recent)}.")

    merged = merge_raw(existing, recent)
    new_text = serialize_raw(merged)

    if new_text == old_text:
        print(f"[fetch_zse] Nema promjena u podacima (ukupno {len(merged)} redaka).")
        return 0

    csv_path.write_text(new_text)
    delta = len(merged) - len(existing)
    print(
        f"[fetch_zse] Podaci azurirani: {len(merged)} redaka "
        f"({delta:+d}), zadnji datum {_max_date(merged)}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
