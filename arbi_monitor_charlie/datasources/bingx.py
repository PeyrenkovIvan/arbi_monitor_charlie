# arbi_monitor/datasources/bingx.py
from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import List, Optional, Tuple

import requests
from tenacity import retry, stop_after_attempt, wait_exponential


BINGX_DEPTH_URL = "https://open-api.bingx.com/openApi/spot/v1/market/depth"


@dataclass
class Level:
    price: float
    qty: float


@dataclass
class OrderBook:
    bids: List[Level]
    asks: List[Level]
    ts_ms: int
    last_update_id: Optional[int] = None

    def top(self) -> Tuple[Optional[Level], Optional[Level]]:
        return (self.bids[0] if self.bids else None,
                self.asks[0] if self.asks else None)


def _parse_levels(raw: list) -> List[Level]:
    # API и depth.json отдают строки: [["0.00906","4653.49"], ...]
    return [Level(price=float(p), qty=float(q)) for p, q in raw]


def load_depth_from_file(path: str) -> OrderBook:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    ts = data.get("ts") or data.get("timestamp")
    # если ts отсутствует — используем текущее время (считаем свежим)
    ts_ms = int(ts) if ts is not None else int(time.time() * 1000)

    return OrderBook(
        bids=_parse_levels(data.get("bids", [])),
        asks=_parse_levels(data.get("asks", [])),
        ts_ms=ts_ms,
        last_update_id=data.get("lastUpdateId"),
    )


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=0.5, min=0.5, max=2))
def fetch_depth_online(symbol: str, limit: int = 100) -> OrderBook:
    params = {"symbol": symbol, "limit": str(limit)}
    r = requests.get(BINGX_DEPTH_URL, params=params, timeout=10)
    r.raise_for_status()
    data = r.json()
    # Нормализуем формат
    if "data" in data and isinstance(data["data"], dict) and "bids" in data["data"]:
        data = data["data"]
    return OrderBook(
        bids=_parse_levels(data.get("bids", [])),
        asks=_parse_levels(data.get("asks", [])),
        ts_ms=int(data.get("ts") or int(time.time() * 1000)),
        last_update_id=data.get("lastUpdateId"),
    )


def get_depth(symbol: str, limit: int = 100, depth_file: Optional[str] = None) -> OrderBook:
    # Всегда онлайн, офлайн-режим убрали
    return fetch_depth_online(symbol, limit)
