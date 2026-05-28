from typing import Dict, List
import numpy as np
import pandas as pd


class VolatilityAnalysis:

    def historical_volatility(self, df: pd.DataFrame, period: int = 20) -> float:
        log_returns = np.log(df["close"] / df["close"].shift(1)).dropna()
        hv = log_returns.rolling(period).std().iloc[-1]
        return round(float(hv * np.sqrt(252) * 100), 4)

    def current_vs_historical_vol(self, df: pd.DataFrame) -> Dict:
        hv_20 = self.historical_volatility(df, 20)
        hv_50 = self.historical_volatility(df, 50) if len(df) >= 50 else hv_20
        hv_5 = self.historical_volatility(df, 5)

        vol_ratio = round(hv_5 / hv_20, 3) if hv_20 > 0 else 1.0
        if vol_ratio > 1.5:
            vol_regime = "HIGH_VOLATILITY"
        elif vol_ratio > 1.1:
            vol_regime = "ELEVATED"
        elif vol_ratio < 0.7:
            vol_regime = "LOW_VOLATILITY"
        else:
            vol_regime = "NORMAL"

        return {
            "hv_5day": hv_5,
            "hv_20day": hv_20,
            "hv_50day": hv_50,
            "vol_ratio": vol_ratio,
            "vol_regime": vol_regime,
        }

    def atr_targets(self, df: pd.DataFrame, atr_series: pd.Series = None) -> Dict:
        if atr_series is None:
            from analysis.technical import TechnicalAnalysis
            atr_series = TechnicalAnalysis().atr(df)

        last_close = float(df["close"].iloc[-1])
        atr = float(atr_series.iloc[-1])

        return {
            "atr": round(atr, 2),
            "t1_up": round(last_close + atr * 0.5, 2),
            "t2_up": round(last_close + atr * 1.0, 2),
            "t3_up": round(last_close + atr * 1.5, 2),
            "t1_dn": round(last_close - atr * 0.5, 2),
            "t2_dn": round(last_close - atr * 1.0, 2),
            "t3_dn": round(last_close - atr * 1.5, 2),
            "daily_range_estimate": round(atr * 1.5, 2),
        }

    def volatility_zones(self, df: pd.DataFrame, num_zones: int = 5) -> List[Dict]:
        """Find high-volume/high-volatility price zones."""
        price_min = float(df["low"].min())
        price_max = float(df["high"].max())
        zone_size = (price_max - price_min) / num_zones

        zones = []
        for i in range(num_zones):
            zone_low = price_min + i * zone_size
            zone_high = zone_low + zone_size
            mask = (df["low"] <= zone_high) & (df["high"] >= zone_low)
            zone_df = df[mask]
            if len(zone_df) == 0:
                continue
            avg_range = float((zone_df["high"] - zone_df["low"]).mean())
            total_vol = float(zone_df["volume"].sum())
            zones.append({
                "low": round(zone_low, 2),
                "high": round(zone_high, 2),
                "mid": round((zone_low + zone_high) / 2, 2),
                "candle_count": len(zone_df),
                "avg_range": round(avg_range, 2),
                "total_volume": int(total_vol),
                "activity_score": round(avg_range * total_vol / 1e6, 4),
            })
        return sorted(zones, key=lambda x: x["activity_score"], reverse=True)

    def intraday_range_bias(self, df: pd.DataFrame) -> Dict:
        """Estimate intraday range based on opening gap and ATR."""
        if len(df) < 2:
            return {}

        today_open = float(df["open"].iloc[0])
        prev_close = float(df["close"].iloc[-2]) if len(df) >= 2 else today_open
        gap = today_open - prev_close
        gap_pct = gap / prev_close * 100 if prev_close > 0 else 0

        from analysis.technical import TechnicalAnalysis
        atr = float(TechnicalAnalysis().atr(df).iloc[-1])

        if abs(gap_pct) > 0.5:
            bias = "BULLISH_GAP" if gap > 0 else "BEARISH_GAP"
            expected_range = atr * 1.8
        else:
            bias = "FLAT_OPEN"
            expected_range = atr * 1.2

        return {
            "gap_points": round(gap, 2),
            "gap_pct": round(gap_pct, 3),
            "bias": bias,
            "expected_range": round(expected_range, 2),
        }

    def full_analysis(self, df: pd.DataFrame) -> Dict:
        result = {}
        result.update(self.current_vs_historical_vol(df))
        result.update(self.atr_targets(df))
        result["high_vol_zones"] = self.volatility_zones(df)[:3]
        result.update(self.intraday_range_bias(df))
        return result
