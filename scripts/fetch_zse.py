"""
Inkrementalni update 7CRO podataka sa ZSE REST API-ja.

Pokrece se rucno ili preko GitHub Actions crona. Povuce zadnjih ~40 dana,
spoji sa postojecim data/sample/7cro_zse.csv (cuva povijest od 2020),
i spremi natrag u kanonskom ZSE formatu (`;` separator, decimalni zarez).

VAZNO o formatu:
    ZSE REST API vraca CSV sa ZAREZOM kao separatorom i TOCKOM kao decimalom
    (npr. `XZAG,"7CRO",...,36.70,...`), dok repo CSV koristi `;` separator i
    decimalni ZAREZ (npr. `XZAG;7CRO;...;36,70;...`). Zato ovdje detektiramo
    separator i konvertiramo decimale, inace bi se cijeli API redak parsirao
    kao jedan string (povijesni bug: podaci su se "skidali" ali nikad nisu
    ispravno mergeani -> graf je tiho zastarijevao).

Promjena se detektira po STVARNOM sadrzaju (ne samo broju redaka), pa se
update zapise i kad se postojeci redak korigira. Prava API/parsiranje greska
vraca non-zero exit da workflow padne (crveno) umjesto tihog zastarijevanja.

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

# Kanonske kolone ZSE exporta (redoslijed bitan za stabilan diff).
CANONICAL_COLS = [
    "mic", "symbol", "isin", "date", "trading_model_id",
    "open_price", "high_price", "low_price", "last_price", "vwap_price",
    "change_prev_close_percentage", "num_trades", "volume", "turnover",
    "price_currency", "turnover_currency",
]
# Kolone u kojima je u repo formatu decimalni ZAREZ (API ih salje s tockom).
DECIMAL_COLS = [
    "open_price", "high_price", "low_price", "last_price", "vwap_price",
    "change_prev_close_percentage", "volume", "turnover",
]

CSV_KWARGS = dict(sep=";", quotechar='"')


def _read_raw_zse(source) -> pd.DataFrame:
    """Procitaj sirovi ZSE CSV. Auto-detektira separator (`;` repo / `,` API)."""
    if hasattr(source, "read"):
        raw = source.read()
    else:
        raw = Path(source).read_bytes()
    text = raw.decode("utf-8") if isinstance(raw, bytes) else raw
    first_line = text.splitlines()[0] if text else ""
    sep = ";" if ";" in first_line else ","
    return pd.read_csv(io.StringIO(text), sep=sep, dtype=str, quotechar='"')


def canonicalize(df: pd.DataFrame, from_api: bool) -> pd.DataFrame:
    """Privedi df na kanonski repo oblik: samo poznate kolone, decimalni zarez,
    bez praznih (date == NaN) redaka. `from_api` => konvertiraj tocku u zarez."""
    if df is None or df.empty:
        return pd.DataFrame(columns=CANONICAL_COLS)
    cols = [c for c in CANONICAL_COLS if c in df.columns]
    out = df[cols].copy()
    if from_api:
        for col in DECIMAL_COLS:
            if col in out.columns:
                out[col] = out[col].fillna("").astype(str).str.replace(".", ",", regex=False)
    # Makni prazne/junk retke bez datuma.
    if "date" in out.columns:
        out = out[out["date"].notna() & (out["date"].astype(str).str.strip() != "")]
    return out.reset_index(drop=True)


def serialize_raw(df: pd.DataFrame) -> str:
    """Serijaliziraj df u kanonski repo CSV (`;`, decimalni zarez)."""
    return df.to_csv(index=False, **CSV_KWARGS)


def fetch_recent_raw() -> pd.DataFrame:
    """Dohvati i kanonikaliziraj zadnjih LOOKBACK_DAYS s API-ja. Retry uz
    backoff; baca iznimku ako i nakon svih pokusaja ne uspije."""
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
            raw = _read_raw_zse(io.BytesIO(resp.content))
            df = canonicalize(raw, from_api=True)
            print(f"[fetch_zse] API vratio {len(raw)} redaka, {len(df)} valjanih.")
            if df.empty:
                # 200 ali bez ijednog parsabilnog retka -> format se promijenio.
                raise ValueError("API odgovor nema valjanih redaka (format?).")
            return df
        except Exception as exc:  # noqa: BLE001 - zelimo retryati sve
            last_exc = exc
            print(f"[fetch_zse] Pokusaj {attempt}/{FETCH_RETRIES} pao: {exc}")
            if attempt < FETCH_RETRIES:
                time.sleep(RETRY_BACKOFF_S * (2 ** (attempt - 1)))

    raise RuntimeError(f"ZSE API nedostupan/neispravan nakon {FETCH_RETRIES} pokusaja: {last_exc}")


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
        return existing.reset_index(drop=True)
    combined = pd.concat([existing, recent], ignore_index=True)
    key = ["date", "trading_model_id"] if "trading_model_id" in combined.columns else ["date"]
    combined = combined.drop_duplicates(subset=key, keep="last")
    # Deterministican poredak: datum silazno, pa model uzlazno (stabilan diff).
    sort_keys = [k for k in ["date", "trading_model_id"] if k in combined.columns]
    ascending = [False] + [True] * (len(sort_keys) - 1)
    combined = combined.sort_values(sort_keys, ascending=ascending).reset_index(drop=True)
    return combined


def _max_date(df: pd.DataFrame) -> str:
    if df is None or df.empty or "date" not in df.columns:
        return "n/a"
    col = df["date"].dropna()
    return col.max() if not col.empty else "n/a"


def main() -> int:
    csv_path = Path(SAMPLE_CSV)
    old_text = csv_path.read_text()
    existing = canonicalize(_read_raw_zse(csv_path), from_api=False)
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
