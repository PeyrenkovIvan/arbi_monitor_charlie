# arbi_monitor/datasources/jupiter.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Dict, Any
import requests


@dataclass
class DexQuote:
    token_qty_out: float       # сколько токена выйдет за budget (UI units)
    cost_dex_usd: float        # ≈ budget_usd (сколько тратим в стейбле)
    effective_price: float     # usd_per_token (budget / qty_out)
    dex_fee_est: Optional[float]  # абсолютная комиссия в $, если можем оценить
    route_url: str             # удобная ссылка на маршрут (для лога/алерта)


def get_quote_buy_for_stable(
    quote_url: str,
    mint_out: str,
    mint_stable: str,
    token_decimals: int,
    usd_amount: float,
    slippage_bps: int,
    timeout: int = 10,
) -> DexQuote:
    """
    Запрашиваем у Jupiter сколько выйдет токена (mint_out) за usd_amount стейбла (mint_stable).
    - amount передаём в минимальных единицах стейбла (USDC: 6 decimals)
    - outAmount приходит в минимальных единицах токена; делим на 10**token_decimals
    """
    stable_decimals = 6  # USDC
    in_amount_atoms = int(round(usd_amount * (10 ** stable_decimals)))

    params = {
        "inputMint": mint_stable,
        "outputMint": mint_out,
        "amount": str(in_amount_atoms),
        "slippageBps": str(slippage_bps),
        # Опциональные параметры можно добавить при необходимости:
        # "onlyDirectRoutes": "false",
        # "exactIn": "true",
    }
    r = requests.get(quote_url, params=params, timeout=timeout)
    r.raise_for_status()
    data = r.json()

    # Jupiter v6 возвращает поле "outAmount" в атомах токена
    out_amount_atoms = int(data["outAmount"])
    token_qty_out = out_amount_atoms / (10 ** token_decimals)

    # Эффективная цена в $/токен
    cost_dex_usd = usd_amount
    effective_price = cost_dex_usd / token_qty_out if token_qty_out > 0 else 0.0

    # Попытка оценить DEX fee:
    dex_fee_est = None
    # В разных маршрутах может быть "routePlan"/"marketInfos" с fee; здесь оставляем None,
    # а в PnL используем fallback из конфига.

    route_url = (
        f"https://jup.ag/swap/{mint_stable}-{mint_out}"
        f"?inputAmount={in_amount_atoms}&slippageBps={slippage_bps}"
    )

    return DexQuote(
        token_qty_out=token_qty_out,
        cost_dex_usd=cost_dex_usd,
        effective_price=effective_price,
        dex_fee_est=dex_fee_est,
        route_url=route_url,
    )
