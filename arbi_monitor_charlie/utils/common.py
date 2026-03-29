# arbi_monitor/utils/common.py
import time


def is_fresh(ts_ms: int, max_age_sec: int) -> bool:
    """
    Нормализуем ts: если сек, умножаем на 1000; если нет ts, считаем свежим.
    """
    if ts_ms is None:
        return True
    if ts_ms < 1_000_000_000_000:  # секунды → миллисекунды
        ts_ms *= 1000
    now_ms = int(time.time() * 1000)
    age_ms = now_ms - ts_ms
    return age_ms <= max_age_sec * 1000 + 500  # +0.5с запас

def fmt_money(x: float) -> str:
    return f"${x:,.4f}"

def fmt_qty(x: float) -> str:
    return f"{x:,.4f}"
