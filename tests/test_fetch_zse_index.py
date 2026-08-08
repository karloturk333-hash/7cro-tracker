import io

import pandas as pd

import scripts.fetch_zse_index as index_fetch


API_CSV = (
    '"mic","symbol","isin","date","open_value","high_value","low_value",'
    '"last_value","change_prev_close_percentage","turnover"\n'
    '"XZAG","C10TR","HRZB00ICB103","2026-08-07",3397.96,3403.57,'
    '3383.74,3390.97,-0.13,3694307.10\n'
).encode()


def test_index_api_format_is_canonicalized():
    frame = index_fetch.canonicalize(index_fetch._read(io.BytesIO(API_CSV)), from_api=True)
    assert frame.iloc[0]["last_value"] == "3390,97"
    assert list(frame.columns) == index_fetch.INDEX_COLS


def test_index_merge_replaces_same_date():
    old = pd.DataFrame([{"date": "2026-08-07", "last_value": "3390,00"}])
    new = pd.DataFrame([{"date": "2026-08-07", "last_value": "3390,97"}])
    merged = index_fetch.merge(old, new)
    assert len(merged) == 1
    assert merged.iloc[0]["last_value"] == "3390,97"


def test_index_url_uses_index_history_endpoint():
    url = index_fetch.build_index_url("2026-08-01", "2026-08-08")
    assert "/index-history/" in url
    assert index_fetch.BENCHMARK_ISIN in url
