"""
Universal data fetcher — tries AngelOne SmartAPI first, falls back to yfinance.
yfinance provides real NSE/BSE 5-min data and works on Streamlit Cloud.
"""
import logging
from datetime import datetime, timedelta
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)

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


# ── AngelOne (smartapi-python) ────────────────────────────────────────────────

def fetch_angelone(symbol: str, interval: str = "FIVE_MINUTE", days_back: int = 5) -> Optional[pd.DataFrame]:
    """Connect via SmartAPI using mpin + TOTP, fetch 5-min candles."""
    try:
        from SmartApi import SmartConnect          # optional dependency
        import pyotp
        from config import api_config, INSTRUMENTS, INTERVAL_MAP

        cfg = api_config
        totp = pyotp.TOTP(cfg.totp_secret).now() if cfg.totp_secret else ""

        smart = SmartConnect(api_key=cfg.api_key)
        data  = smart.generateSession(cfg.client_id, cfg.mpin, totp)  # ← mpin

        if not data.get("status"):
            logger.warning(f"AngelOne login failed: {data.get('message','')}")
            return None

        inst = INSTRUMENTS.get(symbol.upper())
        if not inst:
            return None

        now       = datetime.now()
        to_date   = now.strftime("%Y-%m-%d %H:%M")
        from_date = (now - timedelta(days=days_back)).strftime("%Y-%m-%d %H:%M")

        resp = smart.getCandleData({
            "exchange":    inst["exchange"],
            "symboltoken": inst["token"],
            "interval":    INTERVAL_MAP.get(interval, "FIVE_MINUTE"),
            "fromdate":    from_date,
            "todate":      to_date,
        })

        if resp.get("status") and resp.get("data"):
            df = pd.DataFrame(resp["data"],
                              columns=["timestamp","open","high","low","close","volume"])
            df["timestamp"] = pd.to_datetime(df["timestamp"])
            df = df.set_index("timestamp").sort_index().astype(float)
            logger.info(f"AngelOne: {len(df)} candles for {symbol}")
            return df

    except ImportError:
        logger.debug("smartapi-python not installed — skipping AngelOne")
    except Exception as e:
        logger.debug(f"AngelOne fetch error for {symbol}: {e}")

    return None


# ── yfinance fallback ─────────────────────────────────────────────────────────

def fetch_yfinance(symbol: str, interval: str = "FIVE_MINUTE", days_back: int = 5) -> Optional[pd.DataFrame]:
    """Real NSE/BSE data via yfinance — works everywhere including Streamlit Cloud."""
    try:
        import yfinance as yf
    except ImportError:
        logger.error("yfinance not installed: pip install yfinance")
        return None

    yf_sym   = YFINANCE_SYMBOLS.get(symbol.upper(), f"{symbol.upper()}.NS")
    yf_int   = INTERVAL_MAP_YF.get(interval, "5m")
    period   = f"{min(days_back, 5)}d"

    try:
        ticker = yf.Ticker(yf_sym)
        df = ticker.history(period=period, interval=yf_int, auto_adjust=True)
        if df is None or df.empty:
            logger.warning(f"yfinance: no data for {yf_sym}")
            return None

        df = df.rename(columns={"Open":"open","High":"high","Low":"low",
                                 "Close":"close","Volume":"volume"})
        df = df[["open","high","low","close","volume"]].dropna()

        if hasattr(df.index, "tz") and df.index.tz is not None:
            df.index = df.index.tz_convert("Asia/Kolkata").tz_localize(None)

        df = df.astype(float)
        logger.info(f"yfinance: {len(df)} candles for {yf_sym}")
        return df

    except Exception as e:
        logger.error(f"yfinance error for {yf_sym}: {e}")
        return None


# ── Public API ────────────────────────────────────────────────────────────────

def get_candle_data(symbol: str, interval: str = "FIVE_MINUTE", days_back: int = 5) -> Optional[pd.DataFrame]:
    """AngelOne first → yfinance fallback. Transparent to caller."""
    df = fetch_angelone(symbol, interval, days_back)
    if df is not None and not df.empty:
        return df

    return fetch_yfinance(symbol, interval, days_back)


def get_ltp(symbol: str) -> Optional[float]:
    """Latest price — yfinance 1-min bar."""
    try:
        import yfinance as yf
        yf_sym = YFINANCE_SYMBOLS.get(symbol.upper(), f"{symbol.upper()}.NS")
        hist = yf.Ticker(yf_sym).history(period="1d", interval="1m")
        if hist is not None and not hist.empty:
            return float(hist["Close"].iloc[-1])
    except Exception as e:
        logger.error(f"LTP error: {e}")
    return None
