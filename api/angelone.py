import time
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

import pyotp
import pandas as pd

from config import api_config, INSTRUMENTS, INTERVAL_MAP

logger = logging.getLogger(__name__)


class AngelOneAPI:
    def __init__(self):
        self.obj = None
        self.auth_token: Optional[str] = None
        self.feed_token: Optional[str] = None
        self.refresh_token: Optional[str] = None
        self.connected = False
        self._session_time: Optional[datetime] = None

    def connect(self) -> bool:
        try:
            from SmartApi import SmartConnect
        except ImportError:
            logger.error("SmartAPI not installed. Run: pip install smartapi-python")
            return False

        if not all([api_config.api_key, api_config.client_id, api_config.password]):
            logger.error("Missing API credentials in .env file")
            return False

        try:
            self.obj = SmartConnect(api_key=api_config.api_key)
            totp_code = pyotp.TOTP(api_config.totp_secret).now() if api_config.totp_secret else ""
            data = self.obj.generateSession(
                api_config.client_id,
                api_config.password,
                totp_code,
            )
            if data.get("status"):
                self.auth_token = data["data"]["jwtToken"]
                self.refresh_token = data["data"]["refreshToken"]
                self.feed_token = self.obj.getfeedToken()
                self.connected = True
                self._session_time = datetime.now()
                logger.info(f"Connected to AngelOne as {api_config.client_id}")
                return True
            else:
                logger.error(f"Login failed: {data.get('message', 'Unknown error')}")
                return False
        except Exception as e:
            logger.error(f"Connection error: {e}")
            return False

    def _ensure_connected(self):
        if not self.connected:
            raise ConnectionError("Not connected to AngelOne. Call connect() first.")
        # Re-auth if session older than 8 hours
        if self._session_time and (datetime.now() - self._session_time).seconds > 28800:
            self.connect()

    def get_candle_data(
        self,
        symbol: str,
        interval: str = "FIVE_MINUTE",
        days_back: int = 10,
        from_date: str = None,
        to_date: str = None,
    ) -> pd.DataFrame:
        self._ensure_connected()
        inst = INSTRUMENTS.get(symbol.upper())
        if not inst:
            raise ValueError(f"Unknown symbol: {symbol}")

        now = datetime.now()
        if not to_date:
            to_date = now.strftime("%Y-%m-%d %H:%M")
        if not from_date:
            from_date = (now - timedelta(days=days_back)).strftime("%Y-%m-%d %H:%M")

        params = {
            "exchange": inst["exchange"],
            "symboltoken": inst["token"],
            "interval": INTERVAL_MAP.get(interval, "FIVE_MINUTE"),
            "fromdate": from_date,
            "todate": to_date,
        }

        try:
            response = self.obj.getCandleData(params)
            if response.get("status") and response.get("data"):
                candles = response["data"]
                df = pd.DataFrame(
                    candles, columns=["timestamp", "open", "high", "low", "close", "volume"]
                )
                df["timestamp"] = pd.to_datetime(df["timestamp"])
                df = df.set_index("timestamp").sort_index()
                df = df.astype({"open": float, "high": float, "low": float, "close": float, "volume": float})
                return df
            else:
                logger.warning(f"No candle data for {symbol}: {response.get('message')}")
                return pd.DataFrame()
        except Exception as e:
            logger.error(f"Candle fetch error for {symbol}: {e}")
            return pd.DataFrame()

    def get_ltp(self, symbol: str) -> Optional[float]:
        self._ensure_connected()
        inst = INSTRUMENTS.get(symbol.upper())
        if not inst:
            return None
        try:
            data = self.obj.ltpData(inst["exchange"], inst["symbol"], inst["token"])
            if data.get("status") and data.get("data"):
                return float(data["data"]["ltp"])
        except Exception as e:
            logger.error(f"LTP fetch error: {e}")
        return None

    def search_option_token(self, underlying: str, expiry: str, strike: float, option_type: str) -> Optional[str]:
        """Search for option instrument token. expiry format: DDMMMYYYY e.g. 29MAY2025"""
        self._ensure_connected()
        try:
            symbol = f"{underlying}{expiry}{int(strike)}{option_type}"
            data = self.obj.searchScrip("NFO", symbol)
            if data.get("status") and data.get("data"):
                for item in data["data"]:
                    if item.get("tradingsymbol", "").startswith(symbol):
                        return item["symboltoken"]
        except Exception as e:
            logger.error(f"Option token search error: {e}")
        return None

    def get_option_chain_strikes(self, underlying: str, expiry: str, atm: float, depth: int = 5) -> List[Dict]:
        """Get option chain data for strikes around ATM."""
        self._ensure_connected()
        step = 50 if "NIFTY" in underlying.upper() else 100
        results = []
        for offset in range(-depth, depth + 1):
            strike = int(atm) + offset * step
            for otype in ["CE", "PE"]:
                token = self.search_option_token(underlying, expiry, strike, otype)
                if token:
                    ltp = self._get_option_ltp(token)
                    results.append({
                        "underlying": underlying,
                        "strike": strike,
                        "option_type": otype,
                        "token": token,
                        "ltp": ltp,
                        "expiry": expiry,
                    })
        return results

    def _get_option_ltp(self, token: str) -> Optional[float]:
        try:
            data = self.obj.ltpData("NFO", token, token)
            if data.get("status") and data.get("data"):
                return float(data["data"]["ltp"])
        except Exception:
            pass
        return None

    def get_profile(self) -> Dict:
        self._ensure_connected()
        try:
            data = self.obj.getProfile(self.refresh_token)
            return data.get("data", {})
        except Exception as e:
            logger.error(f"Profile fetch error: {e}")
            return {}

    def disconnect(self):
        if self.obj and self.connected:
            try:
                self.obj.terminateSession(api_config.client_id)
            except Exception:
                pass
        self.connected = False
        logger.info("Disconnected from AngelOne")
