# arbi_monitor/config.py

# --- Маркет / символ ---
SYMBOL_CEX = "CHARLIE-USDT"    # BingX

# --- DEX (Jupiter) ---
DEX_CHAIN = "solana"
BASE_STABLE = "USDC"
# USDC mint (Solana, 6 decimals)
MINT_STABLE = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"

DEX_URL = "https://dexscreener.com/solana/4trcgstgaxewxqlbxscxrqhqxf1z4umjr8ejqz8mtplq"

# Целевой токен (CHARLIE) — укажи правильный mint и decimals (Solana SPL)
MINT_OUT = "CsKfV8ePhQWiyQxNJwXhKZHcmUyNWBkHFGrkZGdJpump"
TOKEN_DECIMALS = 6      # поставь верные decimals для CHARLIE (важно!)

# --- Jupiter quote ---
SLIPPAGE_TOL_BPS = 100  # 1% слippage
JUPITER_QUOTE_URL = "https://quote-api.jup.ag/v6/quote"

# --- Бюджет и цель ---
BUDGET_USD = 100.0             # покупаем на DEX на $100
TARGET_NET_USD = 10.0          # цель: NET >= $10

# --- Комиссии ---
CEX_TAKER_FEE = 0.0015         # 0.15% BingX (правь, если у тебя другая)
DEX_FEE_FALLBACK = 0.003       # 0.30% (fallback если Jupiter не вернет fee)
SOLANA_NET_FEE = 0.0005        # сеть (примерно, negligible)

# --- Интервалы ---
INTERVAL_SEC = 5
TIMEOUT_SEC  = 600
MAX_DATA_AGE_SEC = 30          # не скипаем из-за "шумного" ts

# --- Ограничения рынка BingX (пока руками) ---
TICK_SIZE = 0.00001
STEP_SIZE = 1.0
MIN_NOTIONAL = 1.0

# --- Источник depth (всегда онлайн в нашем варианте) ---
BINGX_DEPTH_LIMIT = 100

# --- Поведение монитора ---
EXIT_ON_MEET = True
