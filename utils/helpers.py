import re
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple


def get_date_range(days_back: int = 30) -> Tuple[str, str]:
    now = datetime.now()
    from_dt = now - timedelta(days=days_back)
    return (
        from_dt.strftime("%Y-%m-%d %H:%M"),
        now.strftime("%Y-%m-%d %H:%M"),
    )


def format_currency(value: float) -> str:
    if abs(value) >= 1_00_000:
        return f"₹{value/1_00_000:.2f}L"
    if abs(value) >= 1_000:
        return f"₹{value/1_000:.1f}K"
    return f"₹{value:.2f}"


def format_pnl(value: float) -> str:
    prefix = "+" if value >= 0 else ""
    return f"{prefix}{format_currency(value)}"


def calculate_lot_value(price: float, lot_size: int) -> float:
    return price * lot_size


def is_market_hours() -> bool:
    now = datetime.now()
    if now.weekday() >= 5:
        return False
    open_t = now.replace(hour=9, minute=15, second=0, microsecond=0)
    close_t = now.replace(hour=15, minute=30, second=0, microsecond=0)
    return open_t <= now <= close_t


def time_to_close() -> int:
    """Returns minutes left until market close."""
    now = datetime.now()
    close_t = now.replace(hour=15, minute=30, second=0, microsecond=0)
    delta = (close_t - now).total_seconds() / 60
    return max(0, int(delta))


def parse_query(query: str) -> Dict:
    """Parse natural language trading queries into structured intent."""
    query_lower = query.lower()
    result = {
        "intent": "analysis",
        "symbol": None,
        "option_type": None,
        "strike": None,
        "target_price": None,
        "timeframe": None,
        "raw": query,
    }

    # Symbol detection
    symbol_patterns = {
        "NIFTY50": r"\bnifty\b|\bnifty\s*50\b",
        "BANKNIFTY": r"\bbank\s*nifty\b|\bbanknifty\b",
        "SENSEX": r"\bsensex\b",
        "SBIN": r"\bsbin\b|\bstate\s*bank\b",
    }
    for symbol, pattern in symbol_patterns.items():
        if re.search(pattern, query_lower):
            result["symbol"] = symbol
            break

    # Option type
    if re.search(r"\bcall\b|\bce\b", query_lower):
        result["option_type"] = "CE"
    elif re.search(r"\bput\b|\bpe\b", query_lower):
        result["option_type"] = "PE"

    # Strike / target price
    price_match = re.search(r"(\d{4,6}(?:\.\d+)?)", query)
    if price_match:
        result["strike"] = float(price_match.group(1))
        result["target_price"] = float(price_match.group(1))

    # Intent detection
    if any(w in query_lower for w in ["should i", "shall i", "can i take", "entry"]):
        result["intent"] = "trade_recommendation"
    elif any(w in query_lower for w in ["probability", "chances", "moving to", "reach"]):
        result["intent"] = "probability"
    elif any(w in query_lower for w in ["analysis", "show me", "analyse", "what's happening"]):
        result["intent"] = "analysis"
    elif any(w in query_lower for w in ["good setup", "good entry", "setup quality"]):
        result["intent"] = "setup_quality"

    # Timeframe
    tf_match = re.search(r"(\d+)\s*(min|hour|hr|day)", query_lower)
    if tf_match:
        result["timeframe"] = f"{tf_match.group(1)}{tf_match.group(2)}"

    return result


def nearest_strike(price: float, step: int = 50) -> int:
    return round(price / step) * step


def strikes_around_price(price: float, count: int = 5, step: int = 50) -> list:
    atm = nearest_strike(price, step)
    return [atm + i * step for i in range(-count, count + 1)]


def is_expiry_day(symbol: str = "NIFTY") -> bool:
    today = datetime.now()
    if symbol in ("NIFTY", "NIFTY50"):
        return today.weekday() == 3  # Thursday
    if symbol == "BANKNIFTY":
        return today.weekday() == 2  # Wednesday
    return False


def get_session_phase() -> str:
    now = datetime.now()
    hour, minute = now.hour, now.minute
    t = hour * 60 + minute
    if t < 9 * 60 + 15:
        return "pre_market"
    if t <= 10 * 60:
        return "opening_volatility"
    if t <= 11 * 60 + 30:
        return "morning_trend"
    if t <= 13 * 60:
        return "consolidation"
    if t <= 14 * 60 + 30:
        return "afternoon_trend"
    if t <= 15 * 60 + 30:
        return "closing_volatility"
    return "post_market"
