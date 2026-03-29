# arbi_monitor/utils/orderbook.py
from __future__ import annotations

from dataclasses import dataclass
from typing import List

from datasources.bingx import Level


@dataclass
class ExecResult:
    requested_qty: float
    filled_qty: float
    revenue_usd: float
    vwap: float
    levels_used: int
    liquidity_ok: bool


def simulate_aggressive_sell(
    qty_token: float,
    bids: List[Level],
    step_size: float,
    tick_size: float,
    min_notional: float,
) -> ExecResult:
    """
    Симуляция рыночной продажи qty_token в bids сверху вниз.
    Возвращает выручку, VWAP, и флаг исполнимости (полное исполнение).
    """
    remain = qty_token
    revenue = 0.0
    used = 0

    for lvl in bids:
        if remain <= 0:
            break
        take = min(lvl.qty, remain)
        revenue += take * lvl.price
        remain -= take
        used += 1

    filled = qty_token - remain
    vwap = (revenue / filled) if filled > 0 else 0.0
    liquidity_ok = filled > 0 and revenue >= min_notional and (filled >= qty_token - 1e-12)

    return ExecResult(
        requested_qty=qty_token,
        filled_qty=filled,
        revenue_usd=revenue,
        vwap=vwap,
        levels_used=used,
        liquidity_ok=liquidity_ok,
    )
