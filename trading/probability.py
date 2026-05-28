from typing import Dict, Optional
import numpy as np
import pandas as pd

from analysis.technical import TechnicalAnalysis
from analysis.volatility import VolatilityAnalysis
from utils.helpers import get_session_phase, is_expiry_day


class ProbabilityCalculator:
    """Multi-factor trade entry probability model."""

    def __init__(self):
        self.ta = TechnicalAnalysis()
        self.va = VolatilityAnalysis()

    # ── Factor Scoring ───────────────────────────────────────────────────────

    def _rsi_score(self, rsi: float, direction: str) -> float:
        """0-100 score based on RSI position for given direction."""
        if direction == "BUY":
            if rsi < 25:
                return 95
            if rsi < 35:
                return 80
            if rsi < 45:
                return 65
            if rsi < 55:
                return 50
            if rsi < 65:
                return 35
            if rsi < 75:
                return 20
            return 10
        else:  # SELL
            return 100 - self._rsi_score(rsi, "BUY")

    def _macd_score(self, macd: float, macd_signal: float, histogram: float, prev_histogram: float, direction: str) -> float:
        bullish_cross = histogram > 0 and prev_histogram <= 0
        bearish_cross = histogram < 0 and prev_histogram >= 0
        if direction == "BUY":
            if bullish_cross:
                return 85
            if histogram > 0 and macd > macd_signal:
                return 70
            if macd > macd_signal:
                return 55
            if histogram < 0 and abs(histogram) < abs(prev_histogram):
                return 45  # momentum slowing
            return 25
        else:
            if bearish_cross:
                return 85
            if histogram < 0 and macd < macd_signal:
                return 70
            if macd < macd_signal:
                return 55
            return 25

    def _bollinger_score(self, price: float, bb_upper: float, bb_lower: float, bb_mid: float, direction: str) -> float:
        bb_range = bb_upper - bb_lower
        if bb_range <= 0:
            return 50
        pos = (price - bb_lower) / bb_range

        if direction == "BUY":
            if pos < 0.1:
                return 90  # near lower band - bounce setup
            if pos < 0.25:
                return 75
            if 0.45 < pos < 0.55:
                return 55  # near midband
            if pos > 0.85:
                return 20  # near upper - overbought
            return 50
        else:
            if pos > 0.9:
                return 90
            if pos > 0.75:
                return 75
            if 0.45 < pos < 0.55:
                return 55
            if pos < 0.15:
                return 20
            return 50

    def _trend_score(self, trend: str, structure: str, direction: str) -> float:
        trend_alignment = {
            ("STRONG_UPTREND", "BUY"): 90, ("UPTREND", "BUY"): 75,
            ("SIDEWAYS", "BUY"): 50, ("DOWNTREND", "BUY"): 30, ("STRONG_DOWNTREND", "BUY"): 15,
            ("STRONG_DOWNTREND", "SELL"): 90, ("DOWNTREND", "SELL"): 75,
            ("SIDEWAYS", "SELL"): 50, ("UPTREND", "SELL"): 30, ("STRONG_UPTREND", "SELL"): 15,
        }
        struct_boost = {"BULLISH": 5, "BEARISH": -5, "NEUTRAL": 0}
        base = trend_alignment.get((trend, direction), 50)
        if direction == "SELL":
            adj = {"BEARISH": 5, "BULLISH": -5, "NEUTRAL": 0}
        else:
            adj = struct_boost
        return min(95, max(5, base + adj.get(structure, 0)))

    def _time_factor_score(self) -> float:
        """Best trading windows for intraday scalping."""
        phase = get_session_phase()
        scores = {
            "pre_market": 0,
            "opening_volatility": 60,
            "morning_trend": 80,
            "consolidation": 45,
            "afternoon_trend": 75,
            "closing_volatility": 65,
            "post_market": 0,
        }
        return scores.get(phase, 50)

    def _volatility_score(self, vol_regime: str, direction: str) -> float:
        """Optimal volatility conditions for scalping."""
        scores = {
            "NORMAL": 75,
            "ELEVATED": 65,
            "HIGH_VOLATILITY": 50,
            "LOW_VOLATILITY": 40,
        }
        return scores.get(vol_regime, 60)

    def _vwap_score(self, above_vwap: bool, direction: str) -> float:
        if direction == "BUY" and above_vwap:
            return 70
        if direction == "SELL" and not above_vwap:
            return 70
        if direction == "BUY" and not above_vwap:
            return 40
        return 40

    # ── Main Calculator ──────────────────────────────────────────────────────

    def calculate(
        self,
        df: pd.DataFrame,
        direction: str = "BUY",
        symbol: str = "NIFTY50",
    ) -> Dict:
        ta = self.ta.full_analysis(df)
        if "error" in ta:
            return {"error": ta["error"], "probability": 50}

        vol_data = self.va.current_vs_historical_vol(df)

        prev_hist = float(
            (self.ta.macd(df["close"])[2]).iloc[-2]
        ) if len(df) >= 2 else 0

        # Factor scores with weights
        factors = {
            "rsi": (self._rsi_score(ta["rsi"], direction), 0.20),
            "macd": (self._macd_score(ta["macd"], ta["macd_signal"], ta["macd_histogram"], prev_hist, direction), 0.20),
            "bollinger": (self._bollinger_score(ta["price"], ta["bb_upper"], ta["bb_lower"], ta["bb_middle"], direction), 0.15),
            "trend": (self._trend_score(ta["trend"], ta["structure"], direction), 0.20),
            "time_factor": (self._time_factor_score(), 0.10),
            "volatility": (self._volatility_score(vol_data["vol_regime"], direction), 0.10),
            "vwap": (self._vwap_score(ta["above_vwap"], direction), 0.05),
        }

        weighted_prob = sum(score * weight for score, weight in factors.values())
        # Confidence: how aligned all factors are
        scores = [s for s, _ in factors.values()]
        std_dev = float(np.std(scores))
        confidence = max(0, min(100, 100 - std_dev * 0.8))

        # Session phase label
        phase = get_session_phase()
        expiry_bonus = 1.2 if is_expiry_day(symbol.replace("50", "")) else 1.0

        # Interpret probability
        prob = round(weighted_prob, 1)
        if prob >= 75:
            verdict = "HIGH_PROBABILITY"
            recommendation = "BUY" if direction == "BUY" else "SELL"
        elif prob >= 60:
            verdict = "MODERATE_PROBABILITY"
            recommendation = "BUY" if direction == "BUY" else "SELL"
        elif prob >= 50:
            verdict = "BORDERLINE"
            recommendation = "WAIT"
        else:
            verdict = "LOW_PROBABILITY"
            recommendation = "AVOID"

        return {
            "direction": direction,
            "symbol": symbol,
            "probability": prob,
            "confidence": round(confidence, 1),
            "verdict": verdict,
            "recommendation": recommendation,
            "session_phase": phase,
            "factor_breakdown": {
                "rsi_score": round(factors["rsi"][0], 1),
                "macd_score": round(factors["macd"][0], 1),
                "bollinger_score": round(factors["bollinger"][0], 1),
                "trend_score": round(factors["trend"][0], 1),
                "time_score": round(factors["time_factor"][0], 1),
                "volatility_score": round(factors["volatility"][0], 1),
                "vwap_score": round(factors["vwap"][0], 1),
            },
            "ta_snapshot": {
                "price": ta["price"],
                "rsi": ta["rsi"],
                "macd_signal": ta["macd_signal_str"],
                "trend": ta["trend"],
                "bb_position_pct": ta["bb_position_pct"],
            },
        }

    def quick_probability(self, df: pd.DataFrame, symbol: str = "NIFTY50") -> Dict:
        """Run both BUY and SELL probabilities and return the higher one."""
        buy_result = self.calculate(df, "BUY", symbol)
        sell_result = self.calculate(df, "SELL", symbol)

        if buy_result.get("probability", 0) > sell_result.get("probability", 0):
            best = buy_result
        else:
            best = sell_result

        best["buy_probability"] = buy_result.get("probability", 50)
        best["sell_probability"] = sell_result.get("probability", 50)
        return best

    def target_reach_probability(self, df: pd.DataFrame, current_price: float, target_price: float) -> Dict:
        """Probability of price reaching a specific target."""
        atr = float(TechnicalAnalysis().atr(df).iloc[-1])
        distance = abs(target_price - current_price)
        atr_multiples = distance / atr if atr > 0 else 1

        direction = "BUY" if target_price > current_price else "SELL"
        base_prob = self.calculate(df, direction)["probability"]

        # Adjust for distance: farther targets = lower probability
        distance_penalty = min(40, atr_multiples * 10)
        adjusted_prob = max(5, base_prob - distance_penalty)

        return {
            "target": target_price,
            "current": current_price,
            "distance": round(abs(target_price - current_price), 2),
            "atr_multiples": round(atr_multiples, 2),
            "probability": round(adjusted_prob, 1),
            "direction": direction,
        }
