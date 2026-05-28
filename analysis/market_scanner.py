"""
NSE Market Scanner — scans 100+ NSE stocks at once.
One-click: top gainers, top losers, volume spikes, best trade opportunities.
Uses yfinance batch download for speed (~15-25 seconds for 100 stocks).
"""
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

# ── NSE universe: Nifty 50 + Nifty Next 50 + popular mid-caps ─────────────────
NSE_UNIVERSE = {
    # ── Nifty 50 ─────────────────────────────────────────────
    "RELIANCE":   "Reliance Industries",
    "TCS":        "Tata Consultancy Services",
    "HDFCBANK":   "HDFC Bank",
    "INFY":       "Infosys",
    "ICICIBANK":  "ICICI Bank",
    "HINDUNILVR": "Hindustan Unilever",
    "KOTAKBANK":  "Kotak Mahindra Bank",
    "SBIN":       "State Bank of India",
    "BHARTIARTL": "Bharti Airtel",
    "ITC":        "ITC",
    "ASIANPAINT": "Asian Paints",
    "AXISBANK":   "Axis Bank",
    "LT":         "Larsen & Toubro",
    "BAJFINANCE": "Bajaj Finance",
    "MARUTI":     "Maruti Suzuki",
    "HCLTECH":    "HCL Technologies",
    "SUNPHARMA":  "Sun Pharma",
    "TITAN":      "Titan Company",
    "WIPRO":      "Wipro",
    "ULTRACEMCO": "UltraTech Cement",
    "NESTLEIND":  "Nestle India",
    "TATAMOTORS": "Tata Motors",
    "POWERGRID":  "Power Grid Corp",
    "NTPC":       "NTPC",
    "TECHM":      "Tech Mahindra",
    "JSWSTEEL":   "JSW Steel",
    "ONGC":       "ONGC",
    "TATASTEEL":  "Tata Steel",
    "BAJAJFINSV": "Bajaj Finserv",
    "GRASIM":     "Grasim Industries",
    "DRREDDY":    "Dr Reddy's Labs",
    "ADANIENT":   "Adani Enterprises",
    "BPCL":       "BPCL",
    "COALINDIA":  "Coal India",
    "HDFCLIFE":   "HDFC Life",
    "SBILIFE":    "SBI Life",
    "BRITANNIA":  "Britannia",
    "DIVISLAB":   "Divi's Labs",
    "APOLLOHOSP": "Apollo Hospitals",
    "EICHERMOT":  "Eicher Motors",
    "HEROMOTOCO": "Hero MotoCorp",
    "HINDALCO":   "Hindalco",
    "INDUSINDBK": "IndusInd Bank",
    "TATACONSUM": "Tata Consumer",
    "CIPLA":      "Cipla",
    "UPL":        "UPL",
    "BAJAJ-AUTO": "Bajaj Auto",
    "ADANIPORTS": "Adani Ports",
    # M&M uses special char, skip for yfinance simplicity
    # ── Nifty Next 50 / Popular ───────────────────────────────
    "SIEMENS":    "Siemens India",
    "PIDILITIND": "Pidilite Industries",
    "BERGEPAINT": "Berger Paints",
    "MARICO":     "Marico",
    "GODREJCP":   "Godrej Consumer",
    "DABUR":      "Dabur India",
    "COLPAL":     "Colgate-Palmolive",
    "HAVELLS":    "Havells India",
    "VOLTAS":     "Voltas",
    "BALKRISIND": "Balkrishna Industries",
    "AMBUJACEM":  "Ambuja Cements",
    "SHREECEM":   "Shree Cement",
    "TRENT":      "Trent",
    "NYKAA":      "FSN E-Commerce (Nykaa)",
    "ZOMATO":     "Zomato",
    "IRCTC":      "IRCTC",
    "DIXON":      "Dixon Technologies",
    "MPHASIS":    "Mphasis",
    "LTIM":       "LTIMindtree",
    "COFORGE":    "Coforge",
    "PERSISTENT": "Persistent Systems",
    "KPITTECH":   "KPIT Technologies",
    "TATAELXSI":  "Tata Elxsi",
    "CHOLAFIN":   "Cholamandalam Finance",
    "TORNTPHARM": "Torrent Pharma",
    "AUROPHARMA": "Aurobindo Pharma",
    "BIOCON":     "Biocon",
    "LUPIN":      "Lupin",
    "GLENMARK":   "Glenmark Pharma",
    "RBLBANK":    "RBL Bank",
    "AUBANK":     "AU Small Finance Bank",
    "IDFCFIRSTB": "IDFC First Bank",
    "FEDERALBNK": "Federal Bank",
    "BANDHANBNK": "Bandhan Bank",
    "YESBANK":    "Yes Bank",
    "PNB":        "Punjab National Bank",
    "BANKBARODA": "Bank of Baroda",
    "CANBK":      "Canara Bank",
    "UNIONBANK":  "Union Bank",
    "TATAPOWER":  "Tata Power",
    "ADANIGREEN": "Adani Green Energy",
    "TORNTPOWER": "Torrent Power",
    "RECLTD":     "REC Ltd",
    "PFC":        "Power Finance Corp",
    "DLF":        "DLF",
    "GODREJPROP": "Godrej Properties",
    "PRESTIGE":   "Prestige Estates",
    "OBEROIRLTY": "Oberoi Realty",
    "IOC":        "Indian Oil Corp",
    "HINDPETRO":  "HPCL",
    "GAIL":       "GAIL India",
    "IGL":        "Indraprastha Gas",
    "ZEEL":       "Zee Entertainment",
    "PVRINOX":    "PVR INOX",
    "INFOEDGE":   "Info Edge",
    "PAYTM":      "One97 Communications (Paytm)",
    "NAUKRI":     "Info Edge",
    "ALKEM":      "Alkem Labs",
    "IPCALAB":    "IPCA Laboratories",
    "MUTHOOTFIN": "Muthoot Finance",
    "BAJAJHFL":   "Bajaj Housing Finance",
    "LICHSGFIN":  "LIC Housing Finance",
    "HDFCAMC":    "HDFC AMC",
    "NHPC":       "NHPC",
    "SJVN":       "SJVN",
    "IREDA":      "IREDA",
}

# yfinance special mappings for symbols that don't follow standard .NS convention
_YF_OVERRIDES = {
    "BAJAJ-AUTO": "BAJAJ-AUTO.NS",
    "M&M":        "M&M.NS",
}

INDEX_EXTRAS = {
    "NIFTY50":   "^NSEI",
    "BANKNIFTY": "^NSEBANK",
    "NIFTYIT":   "^CNXIT",
    "SENSEX":    "^BSESN",
}


def _to_yf(sym: str) -> str:
    if sym in INDEX_EXTRAS:
        return INDEX_EXTRAS[sym]
    if sym in _YF_OVERRIDES:
        return _YF_OVERRIDES[sym]
    return f"{sym}.NS"


def scan_market(universe: str = "nifty100", progress_cb=None) -> Dict[str, Any]:
    """
    Scan NSE stocks and return ranked results.

    universe: "nifty50" | "nifty100" | "all"
    progress_cb: optional callable(message: str) for progress updates

    Returns dict with keys: gainers, losers, volume_leaders, opportunities, all, meta
    """
    try:
        import yfinance as yf
    except ImportError:
        return {"error": "yfinance not installed"}

    syms = list(NSE_UNIVERSE.keys())
    if universe == "nifty50":
        # First 48 keys = Nifty 50
        syms = syms[:48]
    elif universe == "nifty100":
        syms = syms[:100]
    # else "all" uses the full list

    if progress_cb:
        progress_cb(f"Fetching {len(syms)} stocks from NSE…")

    yf_syms = [_to_yf(s) for s in syms]
    sym_map  = {_to_yf(s): s for s in syms}

    try:
        # Batch download: 1 day of 5-min data gives real-time intraday info
        raw = yf.download(
            yf_syms,
            period="5d",
            interval="1d",
            group_by="ticker",
            auto_adjust=True,
            progress=False,
            threads=True,
        )
        # Also get today's intraday for volume/momentum (period=1d interval=5m)
        intra_raw = yf.download(
            yf_syms,
            period="1d",
            interval="5m",
            group_by="ticker",
            auto_adjust=True,
            progress=False,
            threads=True,
        )
    except Exception as e:
        return {"error": f"Download failed: {e}"}

    if progress_cb:
        progress_cb("Calculating scores…")

    results = []
    multi   = len(yf_syms) > 1

    for yf_sym, sym in sym_map.items():
        try:
            # Daily OHLCV
            if multi:
                lvl0 = raw.columns.get_level_values(0)
                if yf_sym not in lvl0:
                    continue
                df_d = raw[yf_sym].dropna(how="all")
            else:
                df_d = raw.dropna(how="all")

            if df_d is None or df_d.empty or len(df_d) < 2:
                continue

            today   = df_d.iloc[-1]
            prev    = df_d.iloc[-2]
            close   = float(today["Close"])
            prev_c  = float(prev["Close"])
            open_   = float(today["Open"])
            high    = float(today["High"])
            low     = float(today["Low"])
            vol     = float(today["Volume"])
            avg_vol = float(df_d["Volume"].tail(5).mean())
            vol_ratio = vol / avg_vol if avg_vol > 0 else 1.0

            day_chg_pct = (close - prev_c) / prev_c * 100 if prev_c else 0
            day_range   = high - low
            gap_pct     = (open_ - prev_c) / prev_c * 100 if prev_c else 0

            # ATR (5-day avg range)
            recent_d = df_d.tail(5)
            atr      = float((recent_d["High"] - recent_d["Low"]).mean())
            atr_pct  = atr / close * 100 if close else 0

            # Intraday momentum: last 5-min close vs open
            intra_momentum = 0.0
            intra_vol_spike = 1.0
            try:
                if multi:
                    if yf_sym in intra_raw.columns.get_level_values(0):
                        df_i = intra_raw[yf_sym].dropna(how="all")
                    else:
                        df_i = pd.DataFrame()
                else:
                    df_i = intra_raw.dropna(how="all")

                if not df_i.empty and len(df_i) >= 5:
                    last5 = df_i.iloc[-5:]
                    intra_momentum = (float(last5["Close"].iloc[-1]) - float(last5["Close"].iloc[0])) / float(last5["Close"].iloc[0]) * 100
                    last_vol  = float(last5["Volume"].mean())
                    avg_i_vol = float(df_i["Volume"].mean())
                    intra_vol_spike = last_vol / avg_i_vol if avg_i_vol > 0 else 1.0
            except Exception:
                pass

            # ── Trade opportunity score ─────────────────────────────────────
            # Higher = more likely to make a sharp move
            abs_move   = abs(day_chg_pct)
            vol_score  = min(vol_ratio, 10) * 10   # 0-100
            atr_score  = min(atr_pct * 10, 100)    # 0-100
            mom_score  = min(abs(intra_momentum) * 20, 100)
            ivol_score = min(intra_vol_spike * 20, 100)

            opportunity_score = (
                abs_move  * 2.5  * 0.30 +   # day move
                vol_score        * 0.25 +   # volume vs avg
                atr_score        * 0.20 +   # volatility (ATR)
                mom_score        * 0.15 +   # recent 5-min momentum
                ivol_score       * 0.10     # intraday volume spike
            )

            results.append({
                "Symbol":       sym,
                "Name":         NSE_UNIVERSE.get(sym, sym),
                "Price":        round(close, 2),
                "Change%":      round(day_chg_pct, 2),
                "Change":       round(close - prev_c, 2),
                "Gap%":         round(gap_pct, 2),
                "Day High":     round(high, 2),
                "Day Low":      round(low, 2),
                "Day Range":    round(day_range, 2),
                "Volume":       int(vol),
                "Vol Ratio":    round(vol_ratio, 2),
                "ATR":          round(atr, 2),
                "ATR%":         round(atr_pct, 2),
                "Mom5m%":       round(intra_momentum, 3),
                "iVol Spike":   round(intra_vol_spike, 2),
                "Opp Score":    round(opportunity_score, 1),
            })

        except Exception as exc:
            logger.debug(f"Scanner error for {sym}: {exc}")

    if not results:
        return {"error": "No data could be fetched. Market may be closed."}

    df_all = pd.DataFrame(results).sort_values("Opp Score", ascending=False)

    # ── Classify each stock ────────────────────────────────────────────────────
    df_all["Signal"] = df_all.apply(_classify, axis=1)

    return {
        "all":             df_all,
        "gainers":         df_all.nlargest(10, "Change%"),
        "losers":          df_all.nsmallest(10, "Change%"),
        "volume_leaders":  df_all.nlargest(10, "Vol Ratio"),
        "opportunities":   df_all.nlargest(15, "Opp Score"),
        "sharp_moves":     df_all[df_all["Vol Ratio"] >= 2.0].nlargest(10, "ATR%"),
        "meta": {
            "scanned":    len(results),
            "scan_time":  datetime.now().strftime("%H:%M:%S"),
            "universe":   universe,
            "advancing":  int((df_all["Change%"] > 0).sum()),
            "declining":  int((df_all["Change%"] < 0).sum()),
            "unchanged":  int((df_all["Change%"] == 0).sum()),
        },
    }


def _classify(row) -> str:
    chg   = row["Change%"]
    vol   = row["Vol Ratio"]
    mom   = row["Mom5m%"]
    score = row["Opp Score"]

    if chg >= 3 and vol >= 2:
        return "🚀 Strong Breakout"
    if chg <= -3 and vol >= 2:
        return "📉 Sharp Fall"
    if abs(chg) >= 1.5 and vol >= 3:
        return "⚡ Volume Surge"
    if vol >= 2.5 and abs(mom) >= 0.3:
        return "🔥 Momentum"
    if chg >= 1:
        return "📈 Bullish"
    if chg <= -1:
        return "📉 Bearish"
    if score >= 20:
        return "👀 Watch"
    return "😴 Sideways"


def get_nse_summary(scan_result: Dict) -> str:
    """Return a natural-language summary of the scan for AI context."""
    if "error" in scan_result:
        return f"Scan error: {scan_result['error']}"
    meta = scan_result["meta"]
    top_g = scan_result["gainers"].head(3)
    top_l = scan_result["losers"].head(3)
    top_o = scan_result["opportunities"].head(3)
    gainers_str = ", ".join(f"{r['Symbol']}({r['Change%']:+.1f}%)" for _, r in top_g.iterrows())
    losers_str  = ", ".join(f"{r['Symbol']}({r['Change%']:+.1f}%)" for _, r in top_l.iterrows())
    opps_str    = ", ".join(f"{r['Symbol']}(score {r['Opp Score']:.0f})" for _, r in top_o.iterrows())
    return (
        f"NSE Scan @ {meta['scan_time']}: {meta['scanned']} stocks | "
        f"Advancing: {meta['advancing']} Declining: {meta['declining']}\n"
        f"Top Gainers: {gainers_str}\n"
        f"Top Losers: {losers_str}\n"
        f"Best Opportunities: {opps_str}"
    )
