import os
from dataclasses import dataclass, field
from dotenv import load_dotenv

load_dotenv()


@dataclass
class APIConfig:
    api_key: str = field(default_factory=lambda: os.getenv("ANGELONE_API_KEY", ""))
    client_id: str = field(default_factory=lambda: os.getenv("ANGELONE_CLIENT_ID", ""))
    password: str = field(default_factory=lambda: os.getenv("ANGELONE_PASSWORD", ""))
    totp_secret: str = field(default_factory=lambda: os.getenv("ANGELONE_TOTP_SECRET", ""))


@dataclass
class TradingConfig:
    candle_interval: str = "FIVE_MINUTE"
    update_interval: int = 5

    normal_target_min: int = 10
    normal_target_max: int = 20
    expiry_target_min: int = 30
    expiry_target_max: int = 50

    stop_loss_ratio: float = 0.5
    max_hold_time: str = "15:45"
    market_open: str = "09:15"
    market_close: str = "15:30"

    default_capital: float = float(os.getenv("DEFAULT_CAPITAL", "100000"))
    risk_per_trade: float = float(os.getenv("RISK_PER_TRADE", "1.0"))


# AngelOne instrument token map
INSTRUMENTS = {
    "NIFTY50": {
        "token": "99926000",
        "exchange": "NSE",
        "symbol": "Nifty 50",
        "type": "INDEX",
        "lot_size": 50,
        "tick_size": 0.05,
    },
    "SENSEX": {
        "token": "99919000",
        "exchange": "BSE",
        "symbol": "SENSEX",
        "type": "INDEX",
        "lot_size": 20,
        "tick_size": 0.01,
    },
    "SBIN": {
        "token": "3045",
        "exchange": "NSE",
        "symbol": "SBIN",
        "type": "STOCK",
        "lot_size": 1500,
        "tick_size": 0.05,
    },
    "BANKNIFTY": {
        "token": "99926009",
        "exchange": "NSE",
        "symbol": "Nifty Bank",
        "type": "INDEX",
        "lot_size": 15,
        "tick_size": 0.05,
    },
}

# Options instruments (tokens fetched dynamically)
OPTIONS_INSTRUMENTS = {
    "NIFTY50-WK": {"underlying": "NIFTY", "exchange": "NFO", "expiry_type": "weekly"},
    "NIFTY50-MO": {"underlying": "NIFTY", "exchange": "NFO", "expiry_type": "monthly"},
    "BANKNIFTY-WK": {"underlying": "BANKNIFTY", "exchange": "NFO", "expiry_type": "weekly"},
}

# Exchange type codes for WebSocket
EXCHANGE_TYPE = {
    "NSE": 1,
    "NFO": 2,
    "BSE": 3,
    "BSE_FO": 4,
    "MCX": 5,
}

# Interval codes for AngelOne API
INTERVAL_MAP = {
    "ONE_MINUTE": "ONE_MINUTE",
    "THREE_MINUTE": "THREE_MINUTE",
    "FIVE_MINUTE": "FIVE_MINUTE",
    "TEN_MINUTE": "TEN_MINUTE",
    "FIFTEEN_MINUTE": "FIFTEEN_MINUTE",
    "THIRTY_MINUTE": "THIRTY_MINUTE",
    "ONE_HOUR": "ONE_HOUR",
    "ONE_DAY": "ONE_DAY",
}

# Technical analysis defaults
TA_DEFAULTS = {
    "rsi_period": 14,
    "macd_fast": 12,
    "macd_slow": 26,
    "macd_signal": 9,
    "bb_period": 20,
    "bb_std": 2.0,
    "atr_period": 14,
    "volume_ma_period": 20,
    "sr_lookback": 50,
}

api_config = APIConfig()
trading_config = TradingConfig()
