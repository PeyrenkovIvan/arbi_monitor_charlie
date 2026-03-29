# arbi_monitor/utils/pnl.py
from dataclasses import dataclass
from typing import Optional


@dataclass
class NetPnl:
    revenue_cex: float
    cost_dex: float
    fee_cex: float
    fee_dex: float
    fee_network: float
    net: float


def calc_net(
    cost_dex: float,
    revenue_cex: float,
    fee_cex_rate: float,
    fee_dex_fallback_rate: float,
    fee_network_abs: float,
    dex_fee_est: Optional[float] = None,
) -> NetPnl:
    fee_cex = revenue_cex * fee_cex_rate
    fee_dex = dex_fee_est if dex_fee_est is not None else (cost_dex * fee_dex_fallback_rate)
    net = revenue_cex - fee_cex - (cost_dex + fee_dex + fee_network_abs)
    return NetPnl(
        revenue_cex=revenue_cex,
        cost_dex=cost_dex,
        fee_cex=fee_cex,
        fee_dex=fee_dex,
        fee_network=fee_network_abs,
        net=net,
    )
