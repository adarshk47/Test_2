from typing import Dict, List
import numpy as np
import pandas as pd


class VolumeAnalysis:

    def volume_profile(self, df: pd.DataFrame, bins: int = 20) -> List[Dict]:
        """Price levels sorted by trading volume (POC analysis)."""
        price_min = float(df["low"].min())
        price_max = float(df["high"].max())
        if price_max <= price_min:
            return []
        bin_size = (price_max - price_min) / bins
        profile = []
        for i in range(bins):
            lvl_low = price_min + i * bin_size
            lvl_high = lvl_low + bin_size
            lvl_mid = (lvl_low + lvl_high) / 2
            mask = (df["low"] <= lvl_high) & (df["high"] >= lvl_low)
            vol = float(df.loc[mask, "volume"].sum())
            profile.append({"price": round(lvl_mid, 2), "volume": int(vol), "low": round(lvl_low, 2), "high": round(lvl_high, 2)})

        total_vol = sum(p["volume"] for p in profile) or 1
        for p in profile:
            p["vol_pct"] = round(p["volume"] / total_vol * 100, 2)

        profile.sort(key=lambda x: x["volume"], reverse=True)

        poc = profile[0]["price"] if profile else None
        high_vol = [p for p in profile if p["vol_pct"] > 10]
        low_vol = [p for p in profile if p["vol_pct"] < 2]

        return {
            "poc": poc,
            "high_volume_nodes": [p["price"] for p in high_vol[:3]],
            "low_volume_nodes": [p["price"] for p in low_vol[:3]],
            "profile": sorted(profile, key=lambda x: x["price"]),
        }

    def vwap_bands(self, df: pd.DataFrame) -> Dict:
        typical = (df["high"] + df["low"] + df["close"]) / 3
        cumvol = df["volume"].cumsum()
        cumtpvol = (typical * df["volume"]).cumsum()
        vwap = cumtpvol / cumvol

        # VWAP standard deviation bands
        vwap_sq = ((typical ** 2 * df["volume"]).cumsum() / cumvol)
        variance = (vwap_sq - vwap ** 2).clip(lower=0)
        std_dev = np.sqrt(variance)

        last_vwap = round(float(vwap.iloc[-1]), 2)
        last_std = round(float(std_dev.iloc[-1]), 2)
        last_close = round(float(df["close"].iloc[-1]), 2)

        return {
            "vwap": last_vwap,
            "vwap_std": last_std,
            "upper_1std": round(last_vwap + last_std, 2),
            "lower_1std": round(last_vwap - last_std, 2),
            "upper_2std": round(last_vwap + 2 * last_std, 2),
            "lower_2std": round(last_vwap - 2 * last_std, 2),
            "price_vs_vwap": "ABOVE" if last_close > last_vwap else "BELOW",
            "distance_from_vwap": round(last_close - last_vwap, 2),
        }

    def momentum(self, df: pd.DataFrame, period: int = 10) -> Dict:
        closes = df["close"]
        mom = closes - closes.shift(period)
        mom_pct = (mom / closes.shift(period) * 100).round(4)
        roc = mom_pct
        last_mom = float(mom.iloc[-1])
        last_roc = float(roc.iloc[-1])
        # Momentum acceleration
        mom_accel = float(mom.diff().iloc[-1])

        if last_roc > 1.0:
            signal = "STRONG_BULLISH"
        elif last_roc > 0.3:
            signal = "BULLISH"
        elif last_roc < -1.0:
            signal = "STRONG_BEARISH"
        elif last_roc < -0.3:
            signal = "BEARISH"
        else:
            signal = "NEUTRAL"

        return {
            "momentum": round(last_mom, 2),
            "roc_pct": round(last_roc, 4),
            "momentum_signal": signal,
            "acceleration": round(mom_accel, 2),
            "accelerating": mom_accel > 0 if last_roc > 0 else mom_accel < 0,
        }

    def volume_momentum_divergence(self, df: pd.DataFrame) -> Dict:
        """Detect price-volume divergence (warning signs)."""
        recent = df.tail(10)
        price_up = float(recent["close"].iloc[-1]) > float(recent["close"].iloc[0])
        vol_trend = recent["volume"].iloc[-5:].mean() - recent["volume"].iloc[:5].mean()
        vol_increasing = vol_trend > 0

        if price_up and vol_increasing:
            divergence = "CONFIRMED_BULLISH"
        elif price_up and not vol_increasing:
            divergence = "BEARISH_DIVERGENCE"
        elif not price_up and not vol_increasing:
            divergence = "CONFIRMED_BEARISH"
        else:
            divergence = "BULLISH_DIVERGENCE"

        return {
            "divergence": divergence,
            "avg_vol_recent": round(float(recent["volume"].iloc[-5:].mean()), 0),
            "avg_vol_prior": round(float(recent["volume"].iloc[:5].mean()), 0),
            "vol_increasing": vol_increasing,
        }

    def relative_volume(self, df: pd.DataFrame, ma_period: int = 20) -> Dict:
        vol_ma = df["volume"].rolling(ma_period).mean()
        last_vol = float(df["volume"].iloc[-1])
        last_vol_ma = float(vol_ma.iloc[-1]) if not vol_ma.iloc[-1] != vol_ma.iloc[-1] else 1
        rvol = last_vol / last_vol_ma if last_vol_ma > 0 else 1.0

        if rvol > 2.0:
            vol_signal = "VERY_HIGH"
        elif rvol > 1.5:
            vol_signal = "HIGH"
        elif rvol < 0.5:
            vol_signal = "LOW"
        else:
            vol_signal = "NORMAL"

        return {
            "current_volume": int(last_vol),
            "avg_volume": int(last_vol_ma),
            "relative_volume": round(rvol, 2),
            "volume_signal": vol_signal,
        }

    def full_analysis(self, df: pd.DataFrame) -> Dict:
        result = {}
        vp = self.volume_profile(df)
        if isinstance(vp, dict):
            result["volume_profile"] = vp
        result.update(self.vwap_bands(df))
        result.update(self.momentum(df))
        result.update(self.volume_momentum_divergence(df))
        result.update(self.relative_volume(df))
        return result
