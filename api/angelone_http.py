"""
Direct AngelOne REST API client using raw HTTP requests.
Works on Streamlit Cloud where smartapi-python may fail to install.
Falls back gracefully if credentials are missing.
"""
import logging
import threading
from datetime import datetime, timedelta
from typing import Optional, Tuple

import requests
import pyotp
import pandas as pd

logger = logging.getLogger(__name__)

BASE = "https://apiconnect.angelbroking.com"

_jwt: Optional[str] = None
_login_time: Optional[datetime] = None
_lock = threading.Lock()
_source = "HTTP_UNAVAILABLE"


def _headers(api_key: str, jwt: Optional[str] = None) -> dict:
    h = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "X-UserType": "USER",
        "X-SourceID": "WEB",
        "X-ClientLocalIP": "127.0.0.1",
        "X-ClientPublicIP": "106.193.147.98",
        "X-MACAddress": "fe80::1",
        "X-PrivateKey": api_key,
    }
    if jwt:
        h["Authorization"] = f"Bearer {jwt}"
    return h


def login_http(api_key: str, client_id: str, mpin: str, totp_secret: str) -> bool:
    global _jwt, _login_time, _source
    try:
        totp = pyotp.TOTP(totp_secret).now()
        r = requests.post(
            f"{BASE}/rest/auth/angelbroking/user/v1/loginByPassword",
            json={"clientcode": client_id, "password": mpin, "totp": totp},
            headers=_headers(api_key),
            timeout=15,
        )
        d = r.json()
        if d.get("status") and d.get("data", {}).get("jwtToken"):
            _jwt        = d["data"]["jwtToken"]
            _login_time = datetime.now()
            _source     = "AngelOne"
            logger.info(f"AngelOne HTTP login OK — {client_id}")
            return True
        logger.warning(f"AngelOne HTTP login failed: {d.get('message', r.text[:200])}")
    except Exception as e:
        logger.debug(f"AngelOne HTTP login error: {e}")
    return False


def get_jwt() -> Optional[str]:
    global _jwt, _login_time
    with _lock:
        expired = (
            _jwt is None or _login_time is None or
            (datetime.now() - _login_time).seconds > 21600  # 6 h
        )
        if expired:
            try:
                from config import api_config
                login_http(api_config.api_key, api_config.client_id,
                           api_config.mpin, api_config.totp_secret)
            except Exception:
                pass
        return _jwt


def fetch_candles_http(token: str, exchange: str, interval: str = "FIVE_MINUTE",
                       days_back: int = 5) -> Optional[pd.DataFrame]:
    from config import api_config
    jwt = get_jwt()
    if not jwt:
        return None
    try:
        now  = datetime.now()
        body = {
            "exchange":    exchange,
            "symboltoken": token,
            "interval":    interval,
            "fromdate":    (now - timedelta(days=days_back)).strftime("%Y-%m-%d %H:%M"),
            "todate":      now.strftime("%Y-%m-%d %H:%M"),
        }
        r = requests.post(
            f"{BASE}/rest/secure/angelbroking/historical/v1/getCandleData",
            json=body, headers=_headers(api_config.api_key, jwt), timeout=20,
        )
        d = r.json()
        if d.get("status") and d.get("data"):
            df = pd.DataFrame(d["data"],
                              columns=["timestamp", "open", "high", "low", "close", "volume"])
            df["timestamp"] = pd.to_datetime(df["timestamp"])
            df = df.set_index("timestamp").sort_index().astype(float)
            logger.info(f"AngelOne HTTP candles: {len(df)} rows")
            return df
        logger.debug(f"AngelOne HTTP candles no data: {d.get('message', '')}")
    except Exception as e:
        logger.debug(f"AngelOne HTTP candles error: {e}")
    return None


def fetch_ltp_http(token: str, exchange: str) -> Optional[float]:
    from config import api_config
    jwt = get_jwt()
    if not jwt:
        return None
    try:
        import json
        r = requests.get(
            f"{BASE}/rest/secure/angelbroking/market/v1/quote/",
            params={"mode": "LTP", "exchangeTokens": json.dumps({exchange: [token]})},
            headers=_headers(api_config.api_key, jwt), timeout=10,
        )
        d = r.json()
        fetched = d.get("data", {}).get("fetched", [])
        if fetched:
            return float(fetched[0].get("ltp", 0)) or None
    except Exception as e:
        logger.debug(f"AngelOne HTTP LTP error: {e}")
    return None


def get_http_source() -> str:
    return _source
