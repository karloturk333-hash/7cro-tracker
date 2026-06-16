"""
Testovi za scripts/fetch_zse.py — inkrementalni auto-pull.

Fokus: detekcija promjene po SADRZAJU (ne broju redaka) i glasan pad
na pravu API gresku (da workflow padne umjesto da tiho zastari).
Mreza se ne dira (mock / monkeypatch).
"""

import pandas as pd
import pytest

import scripts.fetch_zse as f


def _raw(rows):
    return pd.DataFrame(rows, dtype=str)


def test_merge_adds_new_date():
    existing = _raw([{"date": "2026-05-27", "trading_model_id": "CT", "last_price": "37,80"}])
    recent = _raw([{"date": "2026-05-28", "trading_model_id": "CT", "last_price": "37,61"}])
    merged = f.merge_raw(existing, recent)
    assert len(merged) == 2
    # sortirano silazno -> najnoviji prvi
    assert merged.iloc[0]["date"] == "2026-05-28"


def test_updated_existing_row_changes_content_even_without_new_row():
    """Kljucni regresijski test: korigirana vrijednost na POSTOJECEM datumu
    ne mijenja broj redaka, ali MORA promijeniti serijalizirani sadrzaj
    (stari kod bi to preskocio i nista ne bi pushao)."""
    existing = _raw([{"date": "2026-05-28", "trading_model_id": "CT", "last_price": "37,61"}])
    corrected = _raw([{"date": "2026-05-28", "trading_model_id": "CT", "last_price": "99,99"}])
    merged = f.merge_raw(existing, corrected)
    assert len(merged) == len(existing)  # broj redaka isti
    assert f.serialize_raw(merged) != f.serialize_raw(existing)  # sadrzaj razlicit
    assert merged.iloc[0]["last_price"] == "99,99"


def test_no_change_serializes_identically():
    existing = _raw([{"date": "2026-05-28", "trading_model_id": "CT", "last_price": "37,61"}])
    merged = f.merge_raw(existing, pd.DataFrame())  # prazan API odgovor
    assert f.serialize_raw(merged) == f.serialize_raw(existing)


def test_main_returns_nonzero_on_api_error(monkeypatch):
    """Prava API greska -> exit 1 (workflow crveno), ne tiho 'nema promjena'."""
    def boom():
        raise RuntimeError("ZSE API nedostupan")

    monkeypatch.setattr(f, "fetch_recent_raw", boom)
    assert f.main() == 1


def test_main_returns_zero_and_leaves_file_when_no_new_data(monkeypatch, tmp_path):
    """API uspije ali nema nove podatke -> exit 0, datoteka nepromijenjena."""
    csv = tmp_path / "7cro_zse.csv"
    existing = _raw([{"date": "2026-05-28", "trading_model_id": "CT", "last_price": "37,61"}])
    csv.write_text(f.serialize_raw(existing))
    before = csv.read_text()

    monkeypatch.setattr(f, "SAMPLE_CSV", str(csv))
    monkeypatch.setattr(f, "fetch_recent_raw", lambda: pd.DataFrame())

    assert f.main() == 0
    assert csv.read_text() == before  # nista nije zapisano


def test_main_writes_when_content_changes(monkeypatch, tmp_path):
    csv = tmp_path / "7cro_zse.csv"
    existing = _raw([{"date": "2026-05-28", "trading_model_id": "CT", "last_price": "37,61"}])
    csv.write_text(f.serialize_raw(existing))

    new = _raw([{"date": "2026-05-29", "trading_model_id": "CT", "last_price": "38,00"}])
    monkeypatch.setattr(f, "SAMPLE_CSV", str(csv))
    monkeypatch.setattr(f, "fetch_recent_raw", lambda: new)
    # ne odbacuj "danasnji" redak u testu
    monkeypatch.setattr(f, "drop_unfinished_today_raw", lambda df, now=None: df)

    assert f.main() == 0
    after = f._read_raw_zse(str(csv))
    assert "2026-05-29" in set(after["date"])
