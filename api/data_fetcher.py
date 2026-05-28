"""
Universal data fetcher — 3-tier: smartapi-python → AngelOne HTTP → yfinance.
smartapi-python:  fastest, works locally.
AngelOne HTTP:    works on Streamlit Cloud where smartapi-python fails to install.
yfinance:         always works, slightly delayed data.
AngelOne session created ONCE and reused to avoid TOTP expiry.
"""
import logging
import threading
from datetime import datetime, timedelta
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)

YFINANCE_SYMBOLS = {
    "NIFTY50":   "^NSEI",
    "SENSEX":    "^BSESN",
    "SBIN":      "SBIN.NS",
    "BANKNIFTY": "^NSEBANK",
    "NIFTYIT":   "^CNXIT",
}
INTERVAL_MAP_YF = {
    "FIVE_MINUTE":    "5m",
    "ONE_MINUTE":     "1m",
    "FIFTEEN_MINUTE": "15m",
    "ONE_HOUR":       "1h",
    "ONE_DAY":        "1d",
}

# ── Tier-1: smartapi-python singleton ─────────────────────────────────────────
_smart       = None
_login_time: Optional[datetime] = None
_lock        = threading.Lock()
_source      = "yfinance"


def _login() -> bool:
    """Try smartapi-python first, then direct HTTP fallback."""
    global _smart, _login_time, _source

    # — Tier 1: smartapi-python —
    try:
        from SmartApi import SmartConnect
        import pyotp
        from config import api_config
        cfg  = api_config
        totp = pyotp.TOTP(cfg.totp_secret).now()
        obj  = SmartConnect(api_key=cfg.api_key)
        data = obj.generateSession(cfg.client_id, cfg.mpin, totp)
        if data.get("status"):
            _smart      = obj
            _login_time = datetime.now()
            _source     = "AngelOne"
            logger.info(f"AngelOne (smartapi) OK — {cfg.client_id}")
            return True
        logger.warning(f"SmartAPI login failed: {data.get('message', '')}")
    except ImportError:
        logger.debug("smartapi-python not installed — trying HTTP client")
    except Exception as e:
        logger.debug(f"SmartAPI login error: {e}")

    # — Tier 2: direct HTTP —
    try:
        from api.angelone_http import login_http
        from config import api_config
        cfg = api_config
        ok  = login_http(cfg.api_key, cfg.client_id, cfg.mpin, cfg.totp_secret)
        if ok:
            _source = "AngelOne"
            logger.info("AngelOne (HTTP) login OK")
            return True
    except Exception as e:
        logger.debug(f"AngelOne HTTP login error: {e}")

    return False


def _reset_session():
    global _smart, _login_time
    _smart, _login_time = None, None


def _get_session():
    """Return a valid SmartConnect object or None if unavailable."""
    global _smart, _login_time
    with _lock:
        expired = (
            _smart is None or _login_time is None or
            (datetime.now() - _login_time).seconds > 25200
        )
        if expired:
            _login()
        return _smart


def get_data_source() -> str:
    return _source


# ── Tier-1 AngelOne fetch (smartapi) ──────────────────────────────────────────

def fetch_angelone(symbol: str, interval: str = "FIVE_MINUTE",
                   days_back: int = 5) -> Optional[pd.DataFrame]:
    smart = _get_session()
    if smart is None:
        return None
    try:
        from config import INSTRUMENTS, INTERVAL_MAP
        inst = INSTRUMENTS.get(symbol.upper())
        if not inst:
            return None
        now  = datetime.now()
        resp = smart.getCandleData({
            "exchange":    inst["exchange"],
            "symboltoken": inst["token"],
            "interval":    INTERVAL_MAP.get(interval, "FIVE_MINUTE"),
            "fromdate":    (now - timedelta(days=days_back)).strftime("%Y-%m-%d %H:%M"),
            "todate":      now.strftime("%Y-%m-%d %H:%M"),
        })
        if resp.get("status") and resp.get("data"):
            df = pd.DataFrame(resp["data"],
                              columns=["timestamp","open","high","low","close","volume"])
            df["timestamp"] = pd.to_datetime(df["timestamp"])
            df = df.set_index("timestamp").sort_index().astype(float)
            logger.info(f"AngelOne: {len(df)} candles — {symbol}")
            return df
        _reset_session()
    except Exception as e:
        logger.debug(f"AngelOne fetch error ({symbol}): {e}")
        _reset_session()
    return None


# ── Tier-2 AngelOne fetch (direct HTTP) ───────────────────────────────────────

def fetch_angelone_http(symbol: str, interval: str = "FIVE_MINUTE",
                        days_back: int = 5) -> Optional[pd.DataFrame]:
    try:
        from config import INSTRUMENTS, INTERVAL_MAP
        from api.angelone_http import fetch_candles_http
        inst = INSTRUMENTS.get(symbol.upper())
        if not inst:
            return None
        df = fetch_candles_http(inst["token"], inst["exchange"],
                                INTERVAL_MAP.get(interval, "FIVE_MINUTE"), days_back)
        if df is not None and not df.empty:
            return df
    except Exception as e:
        logger.debug(f"AngelOne HTTP candle fetch error ({symbol}): {e}")
    return None


# ── Tier-3 yfinance fallback ───────────────────────────────────────────────────

def fetch_yfinance(symbol: str, interval: str = "FIVE_MINUTE",
                   days_back: int = 5) -> Optional[pd.DataFrame]:
    try:
        import yfinance as yf
    except ImportError:
        logger.error("yfinance not installed")
        return None

    yf_sym = YFINANCE_SYMBOLS.get(symbol.upper(), f"{symbol.upper()}.NS")
    yf_int = INTERVAL_MAP_YF.get(interval, "5m")
    period = f"{min(days_back, 5)}d"
    try:
        df = yf.Ticker(yf_sym).history(period=period, interval=yf_int, auto_adjust=True)
        if df is None or df.empty:
            return None
        df = df.rename(columns={"Open":"open","High":"high","Low":"low",
                                 "Close":"close","Volume":"volume"})
        df = df[["open","high","low","close","volume"]].dropna()
        if hasattr(df.index, "tz") and df.index.tz is not None:
            df.index = df.index.tz_convert("Asia/Kolkata").tz_localize(None)
        return df.astype(float)
    except Exception as e:
        logger.error(f"yfinance error ({yf_sym}): {e}")
        return None


# ── Public API ────────────────────────────────────────────────────────────────

def get_candle_data(symbol: str, interval: str = "FIVE_MINUTE",
                    days_back: int = 5) -> Optional[pd.DataFrame]:
    """smartapi → HTTP → yfinance. Transparent to caller."""
    global _source

    # Tier 1: smartapi-python
    df = fetch_angelone(symbol, interval, days_back)
    if df is not None and not df.empty:
        _source = "AngelOne"
        return df

    # Tier 2: direct HTTP (for Streamlit Cloud)
    df = fetch_angelone_http(symbol, interval, days_back)
    if df is not None and not df.empty:
        _source = "AngelOne"
        return df

    # Tier 3: yfinance
    _source = "yfinance"
    return fetch_yfinance(symbol, interval, days_back)


def get_ltp(symbol: str) -> Optional[float]:
    """LTP: smartapi → HTTP → yfinance 1-min."""
    # Tier 1
    smart = _get_session()
    if smart:
        try:
            from config import INSTRUMENTS
            inst = INSTRUMENTS.get(symbol.upper())
            if inst:
                resp = smart.ltpData(inst["exchange"], inst["symbol"], inst["token"])
                if resp.get("status") and resp.get("data"):
                    return float(resp["data"]["ltp"])
        except Exception:
            pass

    # Tier 2
    try:
        from config import INSTRUMENTS
        from api.angelone_http import fetch_ltp_http
        inst = INSTRUMENTS.get(symbol.upper())
        if inst:
            ltp = fetch_ltp_http(inst["token"], inst["exchange"])
            if ltp:
                return ltp
    except Exception:
        pass

    # Tier 3
    try:
        import yfinance as yf
        yf_sym = YFINANCE_SYMBOLS.get(symbol.upper(), f"{symbol.upper()}.NS")
        hist = yf.Ticker(yf_sym).history(period="1d", interval="1m")
        if hist is not None and not hist.empty:
            return float(hist["Close"].iloc[-1])
    except Exception as e:
        logger.error(f"LTP error: {e}")
    return None
