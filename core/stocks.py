"""
core/stocks.py
────────────────
반도체 소재 공급망 관련 종목(칩메이커/소재/장비)의 실시간 시세를 조회한다.
"""
import concurrent.futures
import logging

import pandas as pd
import yfinance as yf

logger = logging.getLogger(__name__)

STOCK_GROUPS = {
    "🏭 Chipmakers": {
        "SK Hynix": "000660.KS", "Samsung": "005930.KS", "Micron": "MU",
        "TSMC": "TSM", "Intel": "INTC", "SMIC": "0981.HK",
    },
    "🧪 Materials": {
        "Soulbrain": "357780.KQ", "Dongjin": "005290.KQ", "Hana Mat": "166090.KQ",
        "Wonik Mat": "104830.KQ", "TCK": "064760.KQ", "Foosung": "093370.KS",
        "ENF": "102710.KQ", "Shin-Etsu": "4063.T", "Sumco": "3436.T",
        "Merck": "MRK.DE", "Entegris": "ENTG", "TOK": "4186.T",
        "Resonac": "4004.T", "Nissan Chem": "4021.T", "Air Prod": "APD", "Linde": "LIN",
    },
    "⚙️ Equipment": {
        "ASML": "ASML", "AMAT": "AMAT", "Lam Res": "LRCX", "TEL": "8035.T",
        "KLA": "KLAC", "Advantest": "6857.T", "Hanmi": "042700.KS",
        "Wonik IPS": "240810.KQ", "PSK": "319660.KQ", "Zeus": "079370.KQ",
    },
}

_CURRENCY_BY_SUFFIX = {".KS": "₩", ".KQ": "₩", ".T": "¥", ".HK": "HK$", ".DE": "€"}


def _currency_for(symbol):
    for suffix, sym in _CURRENCY_BY_SUFFIX.items():
        if symbol.endswith(suffix):
            return sym
    return "$"


def fetch_stock(name, symbol):
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="5d")
        if hist.empty:
            return name, None

        prev = hist["Close"].iloc[-2] if len(hist) >= 2 else hist["Close"].iloc[-1]
        current = hist["Close"].iloc[-1]

        try:
            live = ticker.history(period="1d", interval="2m")
            if not live.empty:
                current = live["Close"].iloc[-1]
        except Exception as e:
            logger.warning(f"실시간 시세 조회 실패 [{symbol}]: {e}")

        if current is None or pd.isna(current):
            return name, None

        change = current - prev
        pct = (change / prev) * 100 if prev else 0
        return name, {
            "symbol": symbol,
            "price": float(current),
            "change": float(change),
            "pct": float(pct),
            "currency": _currency_for(symbol),
        }
    except Exception as e:
        logger.warning(f"시세 조회 오류 [{symbol}]: {e}")
        return name, None


def fetch_all():
    """그룹별 {name: quote_dict} 형태로 전 종목 시세를 병렬 조회한다."""
    all_tickers = [(name, symbol) for group in STOCK_GROUPS.values() for name, symbol in group.items()]
    result = {}
    max_workers = min(32, len(all_tickers)) or 1
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(fetch_stock, name, symbol): name for name, symbol in all_tickers}
        for future in concurrent.futures.as_completed(futures):
            try:
                name, quote = future.result()
                if quote:
                    result[name] = quote
            except Exception as e:
                logger.warning(f"시세 future 오류: {e}")
    return result
