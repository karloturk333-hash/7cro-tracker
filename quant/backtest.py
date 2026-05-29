"""
Mini backtest engine — SMA crossover strategija.

Najjednostavniji "hello world" kvanta:
  - signal KUPI kad brza SMA prijede IZNAD spore SMA (zlatni krizic)
  - signal PRODAJ kad brza SMA padne ISPOD spore (mrtvi krizic)
  - usporedba s buy & hold

Reusa OHLCV df iz postojeceg loadera. Bez look-ahead bias-a:
trguje se na SLJEDECI dan nakon signala (shift), ne na isti.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def generate_signals(df: pd.DataFrame, fast: int = 20, slow: int = 50) -> pd.DataFrame:
    """
    Dodaj kolonu 'position' (1 = u trzistu, 0 = van) na temelju SMA crossovera.

    'position' je pomaknut za 1 dan unaprijed (shift) da izbjegnemo
    look-ahead bias — odluku donosimo na zatvaranju, trgujemo sljedeci dan.
    """
    out = df.copy()
    out["sma_fast"] = out["Close"].rolling(fast).mean()
    out["sma_slow"] = out["Close"].rolling(slow).mean()

    # signal: 1 kad je brza iznad spore
    out["signal"] = (out["sma_fast"] > out["sma_slow"]).astype(int)
    # pozicija: jucerasnji signal (trgujemo sljedeci dan)
    out["position"] = out["signal"].shift(1).fillna(0).astype(int)
    return out


def run_backtest(df: pd.DataFrame, fast: int = 20, slow: int = 50) -> dict:
    """
    Pokreni SMA-crossover backtest i vrati metrike.

    Vraca dict:
        strategy_return — ukupni povrat strategije (%)
        buyhold_return  — ukupni povrat buy & hold (%)
        n_trades        — broj ulazaka u poziciju
        max_drawdown    — najveci pad equity krivulje strategije (%)
        win             — je li strategija nadmasila buy & hold (bool)
    """
    data = generate_signals(df, fast, slow)

    # dnevni postotni povrat cijene
    data["daily_ret"] = data["Close"].pct_change().fillna(0)
    # povrat strategije = dnevni povrat * jesmo li bili u trzistu
    data["strat_ret"] = data["daily_ret"] * data["position"]

    # equity krivulje (kumulativ)
    data["strat_equity"] = (1 + data["strat_ret"]).cumprod()
    data["bh_equity"] = (1 + data["daily_ret"]).cumprod()

    strategy_return = (data["strat_equity"].iloc[-1] - 1) * 100
    buyhold_return = (data["bh_equity"].iloc[-1] - 1) * 100

    # broj trejdova = koliko puta pozicija prijede iz 0 u 1
    n_trades = int(((data["position"] == 1) & (data["position"].shift(1) == 0)).sum())

    # max drawdown strategije
    running_max = data["strat_equity"].cummax()
    drawdown = (data["strat_equity"] - running_max) / running_max
    max_drawdown = drawdown.min() * 100

    return {
        "strategy_return": float(strategy_return),
        "buyhold_return": float(buyhold_return),
        "n_trades": n_trades,
        "max_drawdown": float(max_drawdown),
        "win": bool(strategy_return > buyhold_return),
    }
