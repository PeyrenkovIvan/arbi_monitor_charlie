from __future__ import annotations

import json
import logging
from pathlib import Path
from datetime import datetime, timezone
import requests
from html import escape

log = logging.getLogger("notifier.telegram")

TG_CFG_PATH = Path(__file__).resolve().parents[1] / "tg.json"
TG_API_BASE = "https://api.telegram.org/bot{token}/sendMessage"


def _load_tg_cfg():
    with open(TG_CFG_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    token = data["TELEGRAM_TOKEN"]
    chat_id = data["TELEGRAM_CHAT_ID"]
    topic_id = data.get("TELEGRAM_TOPIC_ID")
    return token, chat_id, topic_id


def _a(text: str, url: str) -> str:
    # безопасная <a> ссылка (HTML)
    return f'<a href="{escape(url, quote=True)}">{escape(text)}</a>'


def send_alert(
    symbol_cex: str,
    qty: float,
    vwap: float,
    req_vwap: float,
    gap_pct: float,
    revenue_usd: float,
    cost_dex_usd: float,
    fee_cex_usd: float,
    fee_dex_usd: float,
    fee_net_usd: float,
    net_usd: float,
    dex_url: str,
    jupiter_route_url: str,
    eff_price_dex: float,
    top_bid_price: float,
    top_bid_qty: float,
) -> bool:
    """
    Сообщение в «чистом» стиле B, но со ссылками-кликами прямо в строке.
    Формат: обычный текст + <a href="...">текст</a>. parse_mode="HTML".
    """
    try:
        token, chat_id, topic_id = _load_tg_cfg()
    except Exception as e:
        log.exception("TG config read failed: %s", e)
        return False

    # Чистые URL для ссылок
    pair_clean = symbol_cex.replace(" [ТЕСТ]", "")
    bingx_spot_url = "https://bingx.com/en/spot/CHARLIEUSDT"

    # Кликабельные тексты
    l_bingx = _a("BingX (спот)", bingx_spot_url)   # <— меняем текст и URL
    l_dex   = _a("Dexscreener (Solana)", dex_url)
    l_jup   = _a("Маршрут (Jupiter)", jupiter_route_url)

    # Тело сообщения (без жирного/преформата; только кликабельные <a>)
    lines = []
    lines.append(f"🔥 Арбитраж {escape(symbol_cex)} — NET = {net_usd:+.4f} $")
    lines.append("")
    lines.append(
        "Q = {q:.4f} | VWAP = {v:.8f} | Требуется = {r:.8f} (gap = {g:+.2f}%)"
        .format(q=qty, v=vwap, r=req_vwap, g=gap_pct)
    )
    lines.append(
        "Доход = {rev:.4f} $ | Затраты DEX = {cost:.4f} $"
        .format(rev=revenue_usd, cost=cost_dex_usd)
    )
    lines.append(
        "Комиссии: CEX = {c:.4f} $ · DEX = {d:.4f} $ · сеть = {n:.4f} $"
        .format(c=fee_cex_usd, d=fee_dex_usd, n=fee_net_usd)
    )
    lines.append("")
    # ССЫЛКИ В ТЕКСТЕ, КЛИКАБЕЛЬНЫЕ (одна строка)
    lines.append(f"🔗 Ссылки: {l_bingx} · {l_dex} · {l_jup}")
    lines.append("")
    # Время (UTC)
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    lines.append(f"🕒 {ts}")

    text_html = "\n".join(lines)

    url = TG_API_BASE.format(token=token)
    payload = {
        "chat_id": chat_id,
        "text": text_html,
        "parse_mode": "HTML",            # ВАЖНО: HTML, чтобы <a> были кликабельны
        "disable_web_page_preview": True
    }
    if topic_id:
        payload["message_thread_id"] = topic_id

    try:
        resp = requests.post(url, json=payload, timeout=15)
        if not resp.ok:
            log.error("TG send failed: %s | %s", resp.status_code, resp.text)
            return False
        return True
    except Exception as e:
        log.exception("TG HTTP error: %s", e)
        return False
