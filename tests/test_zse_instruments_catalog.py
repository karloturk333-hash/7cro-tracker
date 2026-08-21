"""Katalog InterCapital/ZSE instrumenata mora ostati konzistentan za AI agente."""

from __future__ import annotations

import json
from pathlib import Path

from config.settings import ETF_ISIN, ETF_TICKER, ZSE_API_BASE, ZSE_MIC

CATALOG = Path(__file__).resolve().parent.parent / "config" / "zse_instruments.json"


def _load() -> dict:
    return json.loads(CATALOG.read_text(encoding="utf-8"))


def test_catalog_exists_and_parses():
    data = _load()
    assert data["meta"]["auth"] == "none"
    assert "Bvt9fe2peQ7pwpyYqODM" in data["api"]["zse_base"]
    assert data["api"]["zse_base"] == ZSE_API_BASE
    assert data["api"]["zse_mic"] == ZSE_MIC


def test_regional_mix_weights_sum_to_one():
    weights = _load()["regional_mix"]["weights"]
    symbols = [row["symbol"] for row in weights]
    assert symbols == ["7POL", "7BET", "7CRO", "7SLO"]
    assert abs(sum(row["weight"] for row in weights) - 1.0) < 1e-9


def test_every_etf_has_isin_and_listing_date():
    etfs = {row["symbol"]: row for row in _load()["intercapital_etfs"]}
    required = {"7CRO", "7SLO", "7BET", "7POL", "7CASH", "7GROM"}
    assert required <= set(etfs)
    for symbol, row in etfs.items():
        assert len(row["isin"]) == 12, symbol
        assert row["first_trading_day"][4] == "-", symbol
        assert row["zse_page"].endswith(row["isin"]), symbol


def test_7cro_matches_app_settings():
    etfs = {row["symbol"]: row for row in _load()["intercapital_etfs"]}
    assert ETF_TICKER == "7CRO"
    assert etfs["7CRO"]["isin"] == ETF_ISIN
    assert etfs["7POL"]["newest_listing"] is True
    assert etfs["7POL"]["isin"] == "HRICAMFPWIG3"


def test_catalog_declares_no_auth():
    data = _load()
    assert data["meta"]["auth"] == "none"
    assert "api_key" not in json.dumps(data["api"])
    docs = (Path(__file__).resolve().parent.parent / "docs" / "AGENT_ZSE_API.md").read_text(
        encoding="utf-8"
    )
    assert "bez api ključa" in docs.lower()
