"""Osvjezi zadanu kosaricu likvidnih ZSE dionica za usporedni prikaz."""

from __future__ import annotations

import io
import sys
import time
from datetime import date, timedelta
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config.settings import COMPARISON_INSTRUMENTS  # noqa: E402
from data.zse_api import build_url  # noqa: E402
from scripts.fetch_zse import (  # noqa: E402
    FETCH_RETRIES,
    LOOKBACK_DAYS,
    _read_raw_zse,
    canonicalize,
    drop_unfinished_today_raw,
    merge_raw,
    serialize_raw,
)


def fetch_recent(isin: str):
    today = date.today()
    date_from = (today - timedelta(days=LOOKBACK_DAYS)).isoformat()
    url = build_url(isin, date_from, today.isoformat(), fmt="csv")
    last_error = None
    for attempt in range(1, FETCH_RETRIES + 1):
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            frame = canonicalize(_read_raw_zse(io.BytesIO(response.content)), from_api=True)
            if frame.empty:
                raise ValueError("API odgovor nema valjanih redaka")
            return frame
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            print(f"[fetch_zse_instruments] Pokusaj {attempt}/{FETCH_RETRIES} pao: {exc}")
            if attempt < FETCH_RETRIES:
                time.sleep(2 ** attempt)
    raise RuntimeError(f"ZSE dohvat nije uspio: {last_error}")


def update_instrument(symbol: str, metadata: dict) -> bool:
    path = Path(metadata["path"])
    old_text = path.read_text()
    existing = canonicalize(_read_raw_zse(path), from_api=False)
    recent = drop_unfinished_today_raw(fetch_recent(metadata["isin"]))
    new_text = serialize_raw(merge_raw(existing, recent))
    if new_text == old_text:
        print(f"[fetch_zse_instruments] {symbol}: nema promjena.")
        return False
    path.write_text(new_text)
    print(f"[fetch_zse_instruments] {symbol}: osvjezen do {recent['date'].max()}.")
    return True


def main() -> int:
    failures = []
    for symbol, metadata in COMPARISON_INSTRUMENTS.items():
        try:
            update_instrument(symbol, metadata)
        except Exception as exc:  # noqa: BLE001
            failures.append(f"{symbol}: {exc}")
    if failures:
        for failure in failures:
            print(f"[fetch_zse_instruments] GRESKA: {failure}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
