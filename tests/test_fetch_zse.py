"""
Testovi za scripts/fetch_zse.py — inkrementalni auto-pull.

Fokus: detekcija promjene po SADRZAJU (ne broju redaka) i glasan pad
na pravu API gresku (da workflow padne umjesto da tiho zastari).
Mreza se ne dira (mock / monkeypatch).
"""

import io

import pandas as pd

import scripts.fetch_zse as f


def _raw(rows):
    return pd.DataFrame(rows, dtype=str)


API_HEADER = (
    'mic,"symbol","isin","date","trading_model_id","open_price","high_price",'
    '"low_price","last_price","vwap_price","change_prev_close_percentage",'
    '"num_trades","volume","turnover","price_currency","turnover_currency"\n'
)


def test_reads_comma_separated_dot_decimal_api_format():
    """ZSE REST API vraca CSV sa ZAREZOM i TOCKOM-decimalom; mora se ispravno
    parsirati (povijesni bug: parsiralo se kao `;` pa je cijeli redak postao
    jedan string)."""
    api = (
        API_HEADER
        + 'XZAG,"7CRO","HRICAMFCR102","2026-06-12","CT",38.10,38.20,38.05,38.15,'
        '38.12,0.66,5,300.00000,11445.00,"EUR","EUR"\n'
    ).encode("utf-8")
    df = f.canonicalize(f._read_raw_zse(io.BytesIO(api)), from_api=True)
    assert list(df.columns) == f.CANONICAL_COLS
    assert df.iloc[0]["date"] == "2026-06-12"
    # tocka -> zarez konverzija decimala
    assert df.iloc[0]["last_price"] == "38,15"
    assert df.iloc[0]["volume"] == "300,00000"


def test_canonicalize_drops_phantom_column_and_junk_rows():
    """Postojeci repo CSV ima 'phantom' 17. kolonu i prazan junk redak
    (artefakt starog buga) — canonicalize ih mora ocistiti."""
    existing = f.canonicalize(f._read_raw_zse(f.SAMPLE_CSV), from_api=False)
    assert list(existing.columns) == f.CANONICAL_COLS
    assert (existing["date"].fillna("").str.strip() == "").sum() == 0


def test_api_data_merges_as_new_rows_end_to_end():
    existing = f.canonicalize(f._read_raw_zse(f.SAMPLE_CSV), from_api=False)
    before = len(existing)
    api = (
        API_HEADER
        + 'XZAG,"7CRO","HRICAMFCR102","2026-06-12","CT",38.10,38.20,38.05,38.15,'
        '38.12,0.66,5,300.00000,11445.00,"EUR","EUR"\n'
    ).encode("utf-8")
    recent = f.canonicalize(f._read_raw_zse(io.BytesIO(api)), from_api=True)
    merged = f.merge_raw(existing, recent)
    assert len(merged) == before + 1
    assert f._max_date(merged) == "2026-06-12"


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
