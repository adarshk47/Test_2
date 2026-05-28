from datetime import datetime, timedelta
from typing import Dict, List, Optional
import numpy as np
import pandas as pd


class ExpiryAnalysis:

    # NSE weekly expiry calendar (approximate - Thursday for NIFTY, Wednesday for BANKNIFTY)
    EXPIRY_WEEKDAY = {"NIFTY": 3, "NIFTY50": 3, "BANKNIFTY": 2}

    def get_next_expiry(self, symbol: str = "NIFTY") -> datetime:
        today = datetime.now()
        target_dow = self.EXPIRY_WEEKDAY.get(symbol.upper(), 3)
        days_ahead = (target_dow - today.weekday()) % 7
        if days_ahead == 0 and today.hour >= 15:
            days_ahead = 7
        return today + timedelta(days=days_ahead)

    def is_expiry_day(self, symbol: str = "NIFTY") -> bool:
        today = datetime.now()
        target_dow = self.EXPIRY_WEEKDAY.get(symbol.upper(), 3)
        return today.weekday() == target_dow

    def days_to_expiry(self, symbol: str = "NIFTY") -> int:
        today = datetime.now()
        next_expiry = self.get_next_expiry(symbol)
        return max(0, (next_expiry.date() - today.date()).days)

    def get_target_multiplier(self, symbol: str = "NIFTY") -> float:
        dte = self.days_to_expiry(symbol)
        if dte == 0:
            return 2.5  # Expiry day: 2.5x targets
        elif dte == 1:
            return 1.8
        elif dte <= 2:
            return 1.4
        return 1.0

    def iv_crush_risk(self, dte: int) -> Dict:
        """Estimate IV crush risk after events/expiry."""
        if dte == 0:
            risk = "VERY_HIGH"
            description = "Expiry day - theta decay accelerates sharply, IV collapse likely"
        elif dte == 1:
            risk = "HIGH"
            description = "Day before expiry - elevated theta decay"
        elif dte <= 3:
            risk = "MODERATE"
            description = "Near expiry - increasing time decay"
        else:
            risk = "LOW"
            description = "Far from expiry - time decay manageable"

        return {
            "dte": dte,
            "iv_crush_risk": risk,
            "description": description,
            "theta_factor": round(1 / max(dte, 0.5) * 0.5, 3),
        }

    def calculate_max_pain(self, option_chain: List[Dict]) -> Optional[float]:
        """Max pain = price where total OI value is minimized for option writers."""
        if not option_chain:
            return None

        strikes = sorted(set(o["strike"] for o in option_chain))
        call_oi = {o["strike"]: o.get("oi", 0) for o in option_chain if o.get("option_type") == "CE"}
        put_oi = {o["strike"]: o.get("oi", 0) for o in option_chain if o.get("option_type") == "PE"}

        min_pain = float("inf")
        max_pain_price = strikes[0] if strikes else 0

        for price in strikes:
            pain = 0
            for s in strikes:
                pain += max(0, s - price) * call_oi.get(s, 0)
                pain += max(0, price - s) * put_oi.get(s, 0)
            if pain < min_pain:
                min_pain = pain
                max_pain_price = price

        return max_pain_price

    def expiry_volatility_pattern(self, symbol: str = "NIFTY") -> Dict:
        """Historical expiry day volatility patterns."""
        dte = self.days_to_expiry(symbol)
        is_expiry = self.is_expiry_day(symbol)
        expiry_date = self.get_next_expiry(symbol)
        multiplier = self.get_target_multiplier(symbol)

        hour = datetime.now().hour
        if is_expiry:
            if hour < 11:
                phase = "morning_setup"
                pattern = "Typically choppy open, direction sets by 10:30"
            elif hour < 13:
                phase = "mid_morning_trend"
                pattern = "Strong directional move expected, follow breakout"
            elif hour < 14:
                phase = "lunch_consolidation"
                pattern = "Often sideways, avoid forcing trades"
            elif hour < 15:
                phase = "afternoon_squeeze"
                pattern = "Max pain magnetism - price gravitates toward max pain"
            else:
                phase = "closing_expiry_rush"
                pattern = "High volatility, avoid new entries after 15:15"
        else:
            phase = "normal_trading"
            pattern = "Standard intraday patterns apply"

        return {
            "is_expiry": is_expiry,
            "dte": dte,
            "expiry_date": expiry_date.strftime("%d-%b-%Y"),
            "target_multiplier": multiplier,
            "trading_phase": phase,
            "phase_pattern": pattern,
            "recommended_targets": f"{'30-50' if is_expiry else '10-20'} points per trade",
            **self.iv_crush_risk(dte),
        }

    def option_greeks_estimate(self, current_price: float, strike: float, dte: int, option_type: str = "CE") -> Dict:
        """Rough Black-Scholes approximation for educational purposes."""
        if dte == 0:
            dte = 0.01
        T = dte / 365.0
        sigma = 0.15  # assume 15% IV

        try:
            from scipy.stats import norm
            d1 = (np.log(current_price / strike) + (0.05 + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
            d2 = d1 - sigma * np.sqrt(T)
            if option_type == "CE":
                delta = norm.cdf(d1)
                theta = (-current_price * norm.pdf(d1) * sigma / (2 * np.sqrt(T)) - 0.05 * strike * np.exp(-0.05 * T) * norm.cdf(d2)) / 365
            else:
                delta = norm.cdf(d1) - 1
                theta = (-current_price * norm.pdf(d1) * sigma / (2 * np.sqrt(T)) + 0.05 * strike * np.exp(-0.05 * T) * norm.cdf(-d2)) / 365
            gamma = norm.pdf(d1) / (current_price * sigma * np.sqrt(T))
        except ImportError:
            delta = 0.5 if option_type == "CE" else -0.5
            theta = -5.0
            gamma = 0.005

        return {
            "delta": round(float(delta), 4),
            "theta_per_day": round(float(theta), 2),
            "gamma": round(float(gamma), 6),
            "moneyness": "ITM" if (option_type == "CE" and current_price > strike) or (option_type == "PE" and current_price < strike) else "OTM" if (option_type == "CE" and current_price < strike) or (option_type == "PE" and current_price > strike) else "ATM",
        }

    def full_analysis(self, symbol: str = "NIFTY", current_price: float = None, strike: float = None, option_type: str = "CE") -> Dict:
        result = self.expiry_volatility_pattern(symbol)
        if current_price and strike:
            greeks = self.option_greeks_estimate(current_price, strike, result["dte"], option_type)
            result["greeks"] = greeks
        return result
