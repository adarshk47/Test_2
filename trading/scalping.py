from datetime import datetime
from typing import Dict, List, Optional

import pandas as pd

from analysis.technical import TechnicalAnalysis
from analysis.expiry import ExpiryAnalysis
from config import trading_config


class ScalpingEngine:
    """Generates scalping signals with entry, target, and stop-loss levels."""

    def __init__(self):
        self.ta = TechnicalAnalysis()
        self.ea = ExpiryAnalysis()

    def generate_signal(self, df: pd.DataFrame, symbol: str = "NIFTY50") -> Dict:
        if len(df) < 30:
            return {"signal": "NO_DATA", "reason": "Insufficient candles"}

        ta = self.ta.full_analysis(df)
        if "error" in ta:
            return {"signal": "ERROR", "reason": ta["error"]}

        price = ta["price"]
        rsi = ta["rsi"]
        macd_sig = ta["macd_signal_str"]
        trend = ta["trend"]
        structure = ta["structure"]
        above_vwap = ta["above_vwap"]
        atr = ta["atr"]

        # ── Signal conditions ──────────────────────────────────────────────
        bull_conditions = {
            "rsi_not_overbought": rsi < 65,
            "macd_bullish": macd_sig in ("BULLISH", "BULLISH_CROSSOVER"),
            "uptrend": trend in ("UPTREND", "STRONG_UPTREND"),
            "above_vwap": above_vwap,
            "bullish_structure": structure == "BULLISH",
        }
        bear_conditions = {
            "rsi_not_oversold": rsi > 35,
            "macd_bearish": macd_sig in ("BEARISH", "BEARISH_CROSSOVER"),
            "downtrend": trend in ("DOWNTREND", "STRONG_DOWNTREND"),
            "below_vwap": not above_vwap,
            "bearish_structure": structure == "BEARISH",
        }

        bull_score = sum(bull_conditions.values())
        bear_score = sum(bear_conditions.values())

        # Strong signal requires at least 3 conditions
        if bull_score >= 3 and bull_score > bear_score:
            signal_type = "BUY"
            quality = "STRONG" if bull_score >= 4 else "MODERATE"
            met_conditions = [k for k, v in bull_conditions.items() if v]
        elif bear_score >= 3 and bear_score > bull_score:
            signal_type = "SELL"
            quality = "STRONG" if bear_score >= 4 else "MODERATE"
            met_conditions = [k for k, v in bear_conditions.items() if v]
        else:
            signal_type = "WAIT"
            quality = "WEAK"
            met_conditions = []

        # ── Targets & Stop Loss ────────────────────────────────────────────
        is_expiry = self.ea.is_expiry_day(symbol.replace("50", ""))
        multiplier = self.ea.get_target_multiplier(symbol.replace("50", ""))

        t_min = trading_config.normal_target_min * multiplier
        t_max = trading_config.normal_target_max * multiplier
        sl_pts = (t_min + t_max) / 2 * trading_config.stop_loss_ratio

        if signal_type == "BUY":
            entry = price
            targets = [
                round(price + t_min, 2),
                round(price + (t_min + t_max) / 2, 2),
                round(price + t_max, 2),
            ]
            stop_loss = round(price - sl_pts, 2)
        elif signal_type == "SELL":
            entry = price
            targets = [
                round(price - t_min, 2),
                round(price - (t_min + t_max) / 2, 2),
                round(price - t_max, 2),
            ]
            stop_loss = round(price + sl_pts, 2)
        else:
            entry = price
            targets = []
            stop_loss = None

        # Risk/Reward ratio
        if targets and stop_loss:
            risk = abs(entry - stop_loss)
            reward = abs(targets[1] - entry)
            rr_ratio = round(reward / risk, 2) if risk > 0 else 0
        else:
            rr_ratio = 0

        # Time-based warnings
        now = datetime.now()
        time_warnings = []
        if now.hour == 15 and now.minute >= 15:
            time_warnings.append("AVOID: Too close to market close")
        elif now.hour == 9 and now.minute < 20:
            time_warnings.append("CAUTION: Opening volatility - wait for price discovery")
        if is_expiry and now.hour >= 14:
            time_warnings.append("EXPIRY: High gamma risk after 2 PM, use smaller qty")

        return {
            "symbol": symbol,
            "signal": signal_type,
            "quality": quality,
            "entry": entry,
            "targets": targets,
            "stop_loss": stop_loss,
            "risk_reward": rr_ratio,
            "atr": atr,
            "is_expiry": is_expiry,
            "target_multiplier": multiplier,
            "conditions_met": met_conditions,
            "bull_score": bull_score,
            "bear_score": bear_score,
            "time_warnings": time_warnings,
            "generated_at": datetime.now().strftime("%H:%M:%S"),
            "ta": ta,
        }

    def should_exit(self, entry_price: float, current_price: float, targets: List[float], stop_loss: float, trade_type: str) -> Dict:
        """Check if an open position should be exited."""
        now = datetime.now()
        pnl = current_price - entry_price if trade_type == "BUY" else entry_price - current_price

        # Time-based exit
        if now.hour > 15 or (now.hour == 15 and now.minute >= 45):
            return {"exit": True, "reason": "EOD_EXIT", "pnl": pnl}

        if trade_type == "BUY":
            if stop_loss and current_price <= stop_loss:
                return {"exit": True, "reason": "STOP_LOSS_HIT", "pnl": pnl}
            if targets and current_price >= targets[-1]:
                return {"exit": True, "reason": "TARGET_3_HIT", "pnl": pnl}
            if targets and current_price >= targets[0]:
                return {"exit": False, "reason": "TARGET_1_HIT_TRAIL", "pnl": pnl}
        else:
            if stop_loss and current_price >= stop_loss:
                return {"exit": True, "reason": "STOP_LOSS_HIT", "pnl": pnl}
            if targets and current_price <= targets[-1]:
                return {"exit": True, "reason": "TARGET_3_HIT", "pnl": pnl}
            if targets and current_price <= targets[0]:
                return {"exit": False, "reason": "TARGET_1_HIT_TRAIL", "pnl": pnl}

        return {"exit": False, "reason": "HOLDING", "pnl": pnl}

    def scan_all_instruments(self, data_map: Dict[str, pd.DataFrame]) -> List[Dict]:
        """Scan multiple instruments and return ranked signals."""
        signals = []
        for symbol, df in data_map.items():
            if df is not None and not df.empty:
                sig = self.generate_signal(df, symbol)
                if sig.get("signal") != "WAIT":
                    signals.append(sig)
        return sorted(signals, key=lambda x: x.get("bull_score", 0) + x.get("bear_score", 0), reverse=True)
