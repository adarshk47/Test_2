from typing import Dict, List, Optional, Tuple
import numpy as np
import pandas as pd

from config import TA_DEFAULTS


class TechnicalAnalysis:
    def __init__(self, cfg: Dict = None):
        self.cfg = cfg or TA_DEFAULTS

    # ── Indicators ──────────────────────────────────────────────────────────

    def rsi(self, closes: pd.Series, period: int = None) -> pd.Series:
        period = period or self.cfg["rsi_period"]
        delta = closes.diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        avg_gain = gain.ewm(com=period - 1, min_periods=period).mean()
        avg_loss = loss.ewm(com=period - 1, min_periods=period).mean()
        rs = avg_gain / avg_loss.replace(0, np.nan)
        return 100 - (100 / (1 + rs))

    def macd(
        self, closes: pd.Series, fast: int = None, slow: int = None, signal: int = None
    ) -> Tuple[pd.Series, pd.Series, pd.Series]:
        fast = fast or self.cfg["macd_fast"]
        slow = slow or self.cfg["macd_slow"]
        signal = signal or self.cfg["macd_signal"]
        ema_fast = closes.ewm(span=fast, adjust=False).mean()
        ema_slow = closes.ewm(span=slow, adjust=False).mean()
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()
        histogram = macd_line - signal_line
        return macd_line, signal_line, histogram

    def bollinger_bands(
        self, closes: pd.Series, period: int = None, std_dev: float = None
    ) -> Tuple[pd.Series, pd.Series, pd.Series]:
        period = period or self.cfg["bb_period"]
        std_dev = std_dev or self.cfg["bb_std"]
        middle = closes.rolling(period).mean()
        std = closes.rolling(period).std(ddof=0)
        upper = middle + std_dev * std
        lower = middle - std_dev * std
        return upper, middle, lower

    def atr(self, df: pd.DataFrame, period: int = None) -> pd.Series:
        period = period or self.cfg["atr_period"]
        high, low, close = df["high"], df["low"], df["close"]
        tr = pd.concat(
            [high - low, (high - close.shift()).abs(), (low - close.shift()).abs()],
            axis=1,
        ).max(axis=1)
        return tr.ewm(com=period - 1, min_periods=period).mean()

    def vwap(self, df: pd.DataFrame) -> pd.Series:
        typical_price = (df["high"] + df["low"] + df["close"]) / 3
        cumvol = df["volume"].cumsum()
        cumtpvol = (typical_price * df["volume"]).cumsum()
        return cumtpvol / cumvol

    def ema(self, closes: pd.Series, span: int) -> pd.Series:
        return closes.ewm(span=span, adjust=False).mean()

    # ── Support / Resistance ─────────────────────────────────────────────────

    def support_resistance(self, df: pd.DataFrame, lookback: int = None) -> Dict:
        lookback = lookback or self.cfg["sr_lookback"]
        recent = df.tail(lookback)
        highs = recent["high"].values
        lows = recent["low"].values

        # Find pivot highs (local maxima)
        resistance_levels = []
        support_levels = []
        window = 3
        for i in range(window, len(highs) - window):
            if all(highs[i] >= highs[i - j] for j in range(1, window + 1)) and all(
                highs[i] >= highs[i + j] for j in range(1, window + 1)
            ):
                resistance_levels.append(round(highs[i], 2))
            if all(lows[i] <= lows[i - j] for j in range(1, window + 1)) and all(
                lows[i] <= lows[i + j] for j in range(1, window + 1)
            ):
                support_levels.append(round(lows[i], 2))

        # Cluster nearby levels
        def cluster(levels: List[float], tolerance_pct: float = 0.003) -> List[float]:
            if not levels:
                return []
            levels = sorted(set(levels))
            clustered = [levels[0]]
            for lvl in levels[1:]:
                if abs(lvl - clustered[-1]) / clustered[-1] > tolerance_pct:
                    clustered.append(lvl)
                else:
                    clustered[-1] = (clustered[-1] + lvl) / 2
            return [round(l, 2) for l in clustered]

        current_price = float(df["close"].iloc[-1])
        all_resistance = [r for r in cluster(resistance_levels) if r > current_price]
        all_support = [s for s in cluster(support_levels) if s < current_price]

        return {
            "resistance": sorted(all_resistance)[:3],
            "support": sorted(all_support, reverse=True)[:3],
            "nearest_resistance": min(all_resistance, key=lambda x: x - current_price) if all_resistance else None,
            "nearest_support": max(all_support, key=lambda x: x) if all_support else None,
        }

    # ── Trend Identification ─────────────────────────────────────────────────

    def identify_trend(self, df: pd.DataFrame) -> Dict:
        closes = df["close"]
        ema9 = self.ema(closes, 9)
        ema21 = self.ema(closes, 21)
        ema50 = self.ema(closes, 50)

        last_close = float(closes.iloc[-1])
        e9 = float(ema9.iloc[-1])
        e21 = float(ema21.iloc[-1])
        e50 = float(ema50.iloc[-1])

        # Trend based on EMA alignment
        if last_close > e9 > e21 > e50:
            trend = "STRONG_UPTREND"
            strength = 3
        elif last_close > e9 and e9 > e21:
            trend = "UPTREND"
            strength = 2
        elif last_close < e9 < e21 < e50:
            trend = "STRONG_DOWNTREND"
            strength = -3
        elif last_close < e9 and e9 < e21:
            trend = "DOWNTREND"
            strength = -2
        else:
            trend = "SIDEWAYS"
            strength = 0

        # Higher highs / higher lows check (last 10 candles)
        recent = df.tail(10)
        hh = recent["high"].iloc[-1] > recent["high"].iloc[-5]
        hl = recent["low"].iloc[-1] > recent["low"].iloc[-5]
        lh = recent["high"].iloc[-1] < recent["high"].iloc[-5]
        ll = recent["low"].iloc[-1] < recent["low"].iloc[-5]

        if hh and hl:
            structure = "BULLISH"
        elif lh and ll:
            structure = "BEARISH"
        else:
            structure = "NEUTRAL"

        return {
            "trend": trend,
            "strength": strength,
            "structure": structure,
            "ema9": round(e9, 2),
            "ema21": round(e21, 2),
            "ema50": round(e50, 2),
        }

    # ── Full Analysis ────────────────────────────────────────────────────────

    def full_analysis(self, df: pd.DataFrame) -> Dict:
        if len(df) < 30:
            return {"error": "Insufficient data (need 30+ candles)"}

        closes = df["close"]
        rsi_series = self.rsi(closes)
        macd_line, signal_line, hist = self.macd(closes)
        bb_upper, bb_mid, bb_lower = self.bollinger_bands(closes)
        atr_series = self.atr(df)
        vwap_series = self.vwap(df)

        last_rsi = round(float(rsi_series.iloc[-1]), 2)
        last_macd = round(float(macd_line.iloc[-1]), 4)
        last_signal = round(float(signal_line.iloc[-1]), 4)
        last_hist = round(float(hist.iloc[-1]), 4)
        prev_hist = round(float(hist.iloc[-2]), 4)
        last_close = round(float(closes.iloc[-1]), 2)
        last_atr = round(float(atr_series.iloc[-1]), 2)
        last_bb_upper = round(float(bb_upper.iloc[-1]), 2)
        last_bb_lower = round(float(bb_lower.iloc[-1]), 2)
        last_bb_mid = round(float(bb_mid.iloc[-1]), 2)
        last_vwap = round(float(vwap_series.iloc[-1]), 2)

        bb_position = (last_close - last_bb_lower) / (last_bb_upper - last_bb_lower) * 100 if (last_bb_upper - last_bb_lower) > 0 else 50
        bb_squeeze = (last_bb_upper - last_bb_lower) / last_bb_mid * 100

        # RSI signal
        if last_rsi < 30:
            rsi_signal = "OVERSOLD_BULLISH"
        elif last_rsi < 40:
            rsi_signal = "NEAR_OVERSOLD"
        elif last_rsi > 70:
            rsi_signal = "OVERBOUGHT_BEARISH"
        elif last_rsi > 60:
            rsi_signal = "NEAR_OVERBOUGHT"
        else:
            rsi_signal = "NEUTRAL"

        # MACD signal
        macd_bullish = last_macd > last_signal
        macd_cross_up = last_hist > 0 and prev_hist <= 0
        macd_cross_dn = last_hist < 0 and prev_hist >= 0
        if macd_cross_up:
            macd_signal_str = "BULLISH_CROSSOVER"
        elif macd_cross_dn:
            macd_signal_str = "BEARISH_CROSSOVER"
        elif macd_bullish:
            macd_signal_str = "BULLISH"
        else:
            macd_signal_str = "BEARISH"

        trend_data = self.identify_trend(df)
        sr_data = self.support_resistance(df)

        return {
            "price": last_close,
            "rsi": last_rsi,
            "rsi_signal": rsi_signal,
            "macd": last_macd,
            "macd_signal": last_signal,
            "macd_histogram": last_hist,
            "macd_signal_str": macd_signal_str,
            "bb_upper": last_bb_upper,
            "bb_middle": last_bb_mid,
            "bb_lower": last_bb_lower,
            "bb_position_pct": round(bb_position, 1),
            "bb_squeeze_pct": round(bb_squeeze, 2),
            "atr": last_atr,
            "vwap": last_vwap,
            "above_vwap": last_close > last_vwap,
            **trend_data,
            **sr_data,
        }
