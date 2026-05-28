import threading
import logging
import time
from datetime import datetime
from typing import Callable, Dict, List, Optional

from config import INSTRUMENTS, EXCHANGE_TYPE

logger = logging.getLogger(__name__)


class MarketDataStream:
    """Real-time market data via AngelOne SmartWebSocketV2."""

    def __init__(self, auth_token: str, api_key: str, client_id: str, feed_token: str):
        self.auth_token = auth_token
        self.api_key = api_key
        self.client_id = client_id
        self.feed_token = feed_token
        self.sws = None
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._tick_callbacks: List[Callable] = []
        self._latest_ticks: Dict[str, Dict] = {}
        self._subscribed_tokens: List[Dict] = []

    def add_tick_callback(self, fn: Callable):
        self._tick_callbacks.append(fn)

    def subscribe_instruments(self, symbols: List[str]):
        nse_tokens = []
        nfo_tokens = []
        for sym in symbols:
            inst = INSTRUMENTS.get(sym.upper())
            if inst:
                if inst["exchange"] == "NSE":
                    nse_tokens.append(inst["token"])
                elif inst["exchange"] == "NFO":
                    nfo_tokens.append(inst["token"])

        self._subscribed_tokens = []
        if nse_tokens:
            self._subscribed_tokens.append({"exchangeType": EXCHANGE_TYPE["NSE"], "tokens": nse_tokens})
        if nfo_tokens:
            self._subscribed_tokens.append({"exchangeType": EXCHANGE_TYPE["NFO"], "tokens": nfo_tokens})

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run_stream, daemon=True)
        self._thread.start()
        logger.info("Market data stream started")

    def stop(self):
        self._running = False
        if self.sws:
            try:
                self.sws.close_connection()
            except Exception:
                pass
        logger.info("Market data stream stopped")

    def get_latest(self, symbol: str) -> Optional[Dict]:
        return self._latest_ticks.get(symbol.upper())

    def _run_stream(self):
        try:
            from SmartApi.SmartWebSocketV2 import SmartWebSocketV2
        except ImportError:
            logger.error("SmartAPI WebSocket not available")
            return

        self.sws = SmartWebSocketV2(
            self.auth_token, self.api_key, self.client_id, self.feed_token
        )

        def on_data(wsapp, message):
            self._handle_tick(message)

        def on_open(wsapp):
            if self._subscribed_tokens:
                self.sws.subscribe("scalper_bot", 3, self._subscribed_tokens)
            logger.info("WebSocket connected and subscribed")

        def on_error(wsapp, error):
            logger.error(f"WebSocket error: {error}")

        def on_close(wsapp):
            logger.warning("WebSocket closed")
            if self._running:
                time.sleep(5)
                self._run_stream()

        self.sws.on_data = on_data
        self.sws.on_open = on_open
        self.sws.on_error = on_error
        self.sws.on_close = on_close
        self.sws.connect()

    def _handle_tick(self, message: Dict):
        try:
            token = str(message.get("token", ""))
            # Reverse lookup token → symbol
            symbol = None
            for sym, inst in INSTRUMENTS.items():
                if inst["token"] == token:
                    symbol = sym
                    break
            if not symbol:
                return

            tick = {
                "symbol": symbol,
                "ltp": message.get("last_traded_price", 0) / 100,
                "open": message.get("open_price_of_the_day", 0) / 100,
                "high": message.get("high_price_of_the_day", 0) / 100,
                "low": message.get("low_price_of_the_day", 0) / 100,
                "close": message.get("closed_price", 0) / 100,
                "volume": message.get("volume_trade_for_the_day", 0),
                "timestamp": datetime.now(),
            }
            self._latest_ticks[symbol] = tick
            for cb in self._tick_callbacks:
                try:
                    cb(tick)
                except Exception as e:
                    logger.error(f"Tick callback error: {e}")
        except Exception as e:
            logger.error(f"Tick processing error: {e}")
