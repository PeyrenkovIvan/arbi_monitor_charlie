import argparse
import logging
import time

from config import (
    SYMBOL_CEX, BUDGET_USD, TARGET_NET_USD,
    CEX_TAKER_FEE, DEX_FEE_FALLBACK, SOLANA_NET_FEE,
    INTERVAL_SEC, TIMEOUT_SEC, MAX_DATA_AGE_SEC,
    TICK_SIZE, STEP_SIZE, MIN_NOTIONAL,
    BINGX_DEPTH_LIMIT, EXIT_ON_MEET,
    JUPITER_QUOTE_URL, MINT_OUT, MINT_STABLE, TOKEN_DECIMALS, SLIPPAGE_TOL_BPS, DEX_URL
)

from datasources.bingx import get_depth
from datasources.jupiter import get_quote_buy_for_stable
from utils.orderbook import simulate_aggressive_sell
from utils.pnl import calc_net
from utils.common import is_fresh, fmt_money, fmt_qty
from utils.logging_conf import setup_logging

log = logging.getLogger("monitor")
alog = logging.getLogger("alerts")


def required_revenue_for_target(cost_dex, fee_cex_rate, fee_dex_abs, fee_network_abs, target_net):
    rhs = cost_dex + fee_dex_abs + fee_network_abs + target_net
    denom = (1.0 - fee_cex_rate)
    return rhs / denom if denom > 0 else float("inf")


def run_once(args) -> bool:
    # 1) Jupiter / qty
    if args.use_jupiter:
        try:
            q = get_quote_buy_for_stable(
                quote_url=JUPITER_QUOTE_URL,
                mint_out=MINT_OUT, mint_stable=MINT_STABLE,
                token_decimals=TOKEN_DECIMALS,
                usd_amount=args.budget_usd,
                slippage_bps=args.slippage_bps,
                timeout=10,
            )
            qty_token = q.token_qty_out
            cost_dex = q.cost_dex_usd
            dex_fee_est = q.dex_fee_est
            route_url = q.route_url
            log.info("DEX quote: qty=%s | effPrice=$%.8f | route=%s",
                     fmt_qty(qty_token), q.effective_price, route_url)
        except Exception as e:
            log.exception("Jupiter quote failed, fallback to --dex-out-qty: %s", e)
            qty_token = args.dex_out_qty
            cost_dex = args.budget_usd
            dex_fee_est = None
            route_url = "(fallback)"
    else:
        qty_token = args.dex_out_qty
        cost_dex = args.budget_usd
        dex_fee_est = None
        route_url = "(manual)"

    if qty_token <= 0:
        log.warning("SKIP: qty_token<=0")
        return False

    # 2) BingX depth
    depth = get_depth(SYMBOL_CEX, limit=BINGX_DEPTH_LIMIT)
    fresh = is_fresh(depth.ts_ms, MAX_DATA_AGE_SEC)
    if not fresh:
        log.warning("STALE depth")

    top_bid = depth.bids[0] if depth.bids else None

    # 3) simulate sell
    exec_res = simulate_aggressive_sell(
        qty_token=qty_token, bids=depth.bids,
        step_size=STEP_SIZE, tick_size=TICK_SIZE, min_notional=MIN_NOTIONAL,
    )
    if not exec_res.liquidity_ok:
        log.info("NO-LIQ: requested=%s, filled=%s", fmt_qty(exec_res.requested_qty), fmt_qty(exec_res.filled_qty))
        return False

    # 4) PnL
    pnl = calc_net(
        cost_dex=cost_dex, revenue_cex=exec_res.revenue_usd,
        fee_cex_rate=args.cex_fee, fee_dex_fallback_rate=args.dex_fee, fee_network_abs=args.network_fee,
        dex_fee_est=dex_fee_est,
    )

    # 5) req vwap / gap
    fee_dex_abs = (dex_fee_est if dex_fee_est is not None else cost_dex * args.dex_fee)
    revenue_req = required_revenue_for_target(cost_dex, args.cex_fee, fee_dex_abs, args.network_fee, args.target_net)
    req_vwap = revenue_req / exec_res.filled_qty if exec_res.filled_qty > 0 else float("inf")
    gap = (exec_res.vwap / req_vwap - 1.0) * 100.0

    # 6) condition
    meet = (pnl.net >= args.target_net) or args.force_meet
    if meet and args.tg_enabled:
        from notifier.telegram import send_alert
        symbol_for_msg = f"{SYMBOL_CEX} [ТЕСТ]" if args.force_meet else SYMBOL_CEX
        eff_price_dex = (cost_dex / qty_token) if qty_token > 0 else 0.0
        top_bid_price = getattr(top_bid, "price", 0.0)
        top_bid_qty   = getattr(top_bid, "qty", 0.0)

        send_alert(
            symbol_cex=symbol_for_msg,
            qty=exec_res.filled_qty,
            vwap=exec_res.vwap,
            req_vwap=req_vwap,
            gap_pct=gap,
            revenue_usd=pnl.revenue_cex,
            cost_dex_usd=pnl.cost_dex,
            fee_cex_usd=pnl.fee_cex,
            fee_dex_usd=pnl.fee_dex,
            fee_net_usd=pnl.fee_network,
            net_usd=pnl.net,
            dex_url=DEX_URL,
            jupiter_route_url=route_url,
            eff_price_dex=eff_price_dex,
            top_bid_price=top_bid_price,
            top_bid_qty=top_bid_qty,
        )
    return meet


def main():
    setup_logging()
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--use-jupiter", action="store_true")
    parser.add_argument("--dex-out-qty", type=float, default=0.0)
    parser.add_argument("--budget-usd", type=float, default=BUDGET_USD)
    parser.add_argument("--target-net", type=float, default=TARGET_NET_USD)
    parser.add_argument("--cex-fee", type=float, default=CEX_TAKER_FEE)
    parser.add_argument("--dex-fee", type=float, default=DEX_FEE_FALLBACK)
    parser.add_argument("--network-fee", type=float, default=SOLANA_NET_FEE)
    parser.add_argument("--slippage-bps", type=int, default=SLIPPAGE_TOL_BPS)
    parser.add_argument("--interval", type=int, default=INTERVAL_SEC)
    parser.add_argument("--timeout", type=int, default=TIMEOUT_SEC)
    parser.add_argument("--exit-on-meet", action=argparse.BooleanOptionalAction, default=EXIT_ON_MEET,
                    help="Остановиться при первом MEET (или --no-exit-on-meet)")
    parser.add_argument("--tg-enabled", action="store_true")
    parser.add_argument("--force-meet", action="store_true")
    args = parser.parse_args()

    if args.once:
        run_once(args)
        return

    deadline = time.time() + args.timeout
    while time.time() < deadline:
        try:
            meet = run_once(args)
            if meet and args.exit_on_meet:
                break
        except Exception:
            log.exception("Iteration failed")
        time.sleep(args.interval)

    log.info("Done")


if __name__ == "__main__":
    main()
