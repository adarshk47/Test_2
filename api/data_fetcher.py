"""
Universal data fetcher — tries AngelOne first, falls back to yfinance.
yfinance provides real NSE/BSE 5-min data, works on Streamlit Cloud.
"""
import logging
from datetime import datetime, timedelta
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)

# yfinance symbol map for NSE/BSE instruments
YFINANCE_SYMBOLS = {
    "NIFTY50":   "^NSEI",
    "SENSEX":    "^BSESN",
    "SBIN":      "SBIN.NS",
    "BANKNIFTY": "^NSEBANK",
}

INTERVAL_MAP_YF = {
    "FIVE_MINUTE":    "5m",
    "ONE_MINUTE":     "1m",
    "FIFTEEN_MINUTE": "15m",
    "ONE_HOUR":       "1h",
    "ONE_DAY":        "1d",
}


def fetch_yfinance(symbol: str, interval: str = "FIVE_MINUTE", days_back: int = 5) -> Optional[pd.DataFrame]:
    try:
        import yfinance as yf
    except ImportError:
        logger.error("yfinance not installed. Run: pip install yfinance")
        return None

    yf_sym = YFINANCE_SYMBOLS.get(symbol.upper())
    if not yf_sym:
        # Try direct NSE format
        yf_sym = f"{symbol.upper()}.NS"

    yf_interval = INTERVAL_MAP_YF.get(interval, "5m")
    # yfinance only supports intraday data for last 60 days, max 7 days for 5m
    period = f"{min(days_back, 5)}d"

    try:
        ticker = yf.Ticker(yf_sym)
        df = ticker.history(period=period, interval=yf_interval, auto_adjust=True)
        if df is None or df.empty:
            logger.warning(f"No yfinance data for {yf_sym}")
            return None

        df = df.rename(columns={
            "Open": "open", "High": "high",
            "Low": "low", "Close": "close", "Volume": "volume",
        })
        df = df[["open", "high", "low", "close", "volume"]].dropna()
        # Remove timezone info to keep consistent
        if hasattr(df.index, "tz") and df.index.tz is not None:
            df.index = df.index.tz_convert("Asia/Kolkata").tz_localize(None)
        df = df.astype(float)
        logger.info(f"yfinance: fetched {len(df)} candles for {yf_sym}")
        return df
    except Exception as e:
        logger.error(f"yfinance fetch error for {yf_sym}: {e}")
        return None


def fetch_angelone(symbol: str, interval: str = "FIVE_MINUTE", days_back: int = 5) -> Optional[pd.DataFrame]:
    try:
        from api.angelone import AngelOneAPI
        from config import api_config
        import pyotp
        from SmartApi import SmartConnect

        obj = SmartConnect(api_key=api_config.api_key)
        totp = pyotp.TOTP(api_config.totp_secret).now() if api_config.totp_secret else ""
        data = obj.generateSession(api_config.client_id, api_config.password, totp)
        if not data.get("status"):
            return None

        from config import INSTRUMENTS, INTERVAL_MAP
        inst = INSTRUMENTS.get(symbol.upper())
        if not inst:
            return None

        now = datetime.now()
        to_date = now.strftime("%Y-%m-%d %H:%M")
        from_date = (now - timedelta(days=days_back)).strftime("%Y-%m-%d %H:%M")

        resp = obj.getCandleData({
            "exchange": inst["exchange"],
            "symboltoken": inst["token"],
            "interval": INTERVAL_MAP.get(interval, "FIVE_MINUTE"),
            "fromdate": from_date,
            "todate": to_date,
        })
        if resp.get("status") and resp.get("data"):
            df = pd.DataFrame(resp["data"], columns=["timestamp", "open", "high", "low", "close", "volume"])
            df["timestamp"] = pd.to_datetime(df["timestamp"])
            df = df.set_index("timestamp").sort_index()
            return df.astype(float)
    except Exception as e:
        logger.debug(f"AngelOne fetch failed for {symbol}: {e}")
    return None


def get_candle_data(symbol: str, interval: str = "FIVE_MINUTE", days_back: int = 5) -> Optional[pd.DataFrame]:
    """Try AngelOne first; fall back to yfinance automatically."""
    df = fetch_angelone(symbol, interval, days_back)
    if df is not None and not df.empty:
        logger.info(f"Data source: AngelOne ({symbol})")
        return df

    df = fetch_yfinance(symbol, interval, days_back)
    if df is not None and not df.empty:
        logger.info(f"Data source: yfinance ({symbol})")
        return df

    return None


def get_ltp(symbol: str) -> Optional[float]:
    """Get last traded price — yfinance fast path."""
    try:
        import yfinance as yf
        yf_sym = YFINANCE_SYMBOLS.get(symbol.upper(), f"{symbol.upper()}.NS")
        ticker = yf.Ticker(yf_sym)
        hist = ticker.history(period="1d", interval="1m")
        if hist is not None and not hist.empty:
            return float(hist["Close"].iloc[-1])
    except Exception as e:
        logger.error(f"LTP fetch error: {e}")
    return None
