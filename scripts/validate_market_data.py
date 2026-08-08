"""Fail-fast provjere podataka prije nego GitHub Actions commita promjene."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config.settings import BENCHMARK_CSV, COMPARISON_INSTRUMENTS, SAMPLE_CSV  # noqa: E402
from core.market_intelligence import freshness_status  # noqa: E402
from data.loaders import load_benchmark_sample, load_comparison_samples, load_zse_sample  # noqa: E402


def validate_frame(name: str, frame: pd.DataFrame, *, minimum_rows: int = 100) -> list[str]:
    errors = []
    if frame.empty:
        return [f"{name}: dataset je prazan"]
    if len(frame) < minimum_rows:
        errors.append(f"{name}: samo {len(frame)} redaka (minimum {minimum_rows})")
    if frame["Date"].duplicated().any():
        errors.append(f"{name}: postoje dupli datumi")
    if not frame["Date"].is_monotonic_increasing:
        errors.append(f"{name}: datumi nisu sortirani")
    if frame[["Open", "High", "Low", "Close"]].isna().any().any():
        errors.append(f"{name}: OHLC sadrzi prazne vrijednosti")
    freshness = freshness_status(frame["Date"].max(), stale_after=5)
    if freshness["is_stale"]:
        errors.append(
            f"{name}: zadnji podatak kasni {freshness['business_days_stale']} radnih dana"
        )
    return errors


def main() -> int:
    errors = []
    try:
        asset = load_zse_sample()
        benchmark = load_benchmark_sample()
        errors.extend(validate_frame("7CRO", asset))
        errors.extend(validate_frame("CROBEX10tr", benchmark))
        comparison = load_comparison_samples()
        for symbol, frame in comparison.items():
            errors.extend(validate_frame(symbol, frame))
        if abs((asset["Date"].max() - benchmark["Date"].max()).days) > 5:
            errors.append("7CRO i CROBEX10tr zadnji datumi razlikuju se vise od 5 dana")
    except Exception as exc:  # noqa: BLE001
        errors.append(f"Ne mogu ucitati podatke: {exc}")

    if errors:
        for error in errors:
            print(f"[validate_market_data] GRESKA: {error}", file=sys.stderr)
        return 1
    print(
        f"[validate_market_data] OK: {SAMPLE_CSV.name}, {BENCHMARK_CSV.name} i "
        f"{len(COMPARISON_INSTRUMENTS)} usporedna instrumenta su potpuni i svjezi."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
