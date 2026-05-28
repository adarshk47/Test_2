"""
Scalper Bot — Streamlit Dashboard
Run locally : streamlit run streamlit_app.py
Streamlit Cloud: push to GitHub, connect repo
"""
import os
import time
from datetime import datetime
from typing import Dict, Optional

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Scalper Bot 📈",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Dark theme CSS ────────────────────────────────────────────────────────────
st.markdown("""
<style>
[data-testid="stAppViewContainer"] { background: #0d1117; color: #e6edf3; }
[data-testid="stSidebar"]          { background: #161b22; }
[data-testid="stHeader"]           { background: transparent; }
.metric-box {
    background: #161b22; border: 1px solid #30363d;
    border-radius: 8px; padding: 12px; text-align: center; margin: 4px;
}
.signal-BUY  { color: #00e676; font-size: 1.6em; font-weight: 900; }
.signal-SELL { color: #ff1744; font-size: 1.6em; font-weight: 900; }
.signal-WAIT { color: #ffeb3b; font-size: 1.6em; font-weight: 900; }
.prob-hi { color: #00e676; font-size: 2em; font-weight: 900; }
.prob-md { color: #ffeb3b; font-size: 2em; font-weight: 900; }
.prob-lo { color: #ff1744; font-size: 2em; font-weight: 900; }
.chat-user { background:#1f2937; border-radius:8px; padding:10px; margin:4px 0; }
.chat-bot  { background:#0d2137; border-left:3px solid #58a6ff; border-radius:8px; padding:10px; margin:4px 0; }
div[data-testid="stMetricValue"] > div { color: #e6edf3 !important; }
hr { border-color: #30363d; }
</style>
""", unsafe_allow_html=True)


# ── Cached initialisation ─────────────────────────────────────────────────────
@st.cache_resource(show_spinner="Initialising bot components...")
def init_components():
    from analysis.technical import TechnicalAnalysis
    from analysis.volatility import VolatilityAnalysis
    from analysis.volume import VolumeAnalysis
    from analysis.expiry import ExpiryAnalysis
    from trading.probability import ProbabilityCalculator
    from trading.scalping import ScalpingEngine
    from trading.paper_trading import PaperTradingDashboard
    from database.db_manager import DatabaseManager
    from config import INSTRUMENTS

    db = DatabaseManager()
    return {
        "ta":    TechnicalAnalysis(),
        "va":    VolatilityAnalysis(),
        "vola":  VolumeAnalysis(),
        "ea":    ExpiryAnalysis(),
        "prob":  ProbabilityCalculator(),
        "eng":   ScalpingEngine(),
        "paper": PaperTradingDashboard(db),
        "db":    db,
        "syms":  list(INSTRUMENTS.keys()),
    }


@st.cache_data(ttl=30, show_spinner=False)
def load_data(symbol: str) -> Optional[pd.DataFrame]:
    """30-second cache; tries AngelOne then yfinance automatically."""
    from api.data_fetcher import get_candle_data
    return get_candle_data(symbol, "FIVE_MINUTE", days_back=5)


@st.cache_data(ttl=15, show_spinner=False)
def load_ltp(symbol: str) -> Optional[float]:
    from api.data_fetcher import get_ltp
    return get_ltp(symbol)


# ── Chart builder ─────────────────────────────────────────────────────────────
def build_chart(df: pd.DataFrame, symbol: str, ta) -> "go.Figure":
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    fig = make_subplots(
        rows=3, cols=1, shared_xaxes=True,
        vertical_spacing=0.02, row_heights=[0.60, 0.20, 0.20],
    )

    # Candles
    fig.add_trace(go.Candlestick(
        x=df.index, open=df["open"], high=df["high"],
        low=df["low"], close=df["close"], name=symbol,
        increasing_line_color="#00e676", decreasing_line_color="#ff1744",
    ), row=1, col=1)

    # Bollinger Bands
    bb_u, bb_m, bb_l = ta.bollinger_bands(df["close"])
    fig.add_trace(go.Scatter(x=df.index, y=bb_u, line=dict(color="rgba(100,181,246,.35)", width=1), showlegend=False), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=bb_l, line=dict(color="rgba(100,181,246,.35)", width=1), fill="tonexty", fillcolor="rgba(100,181,246,.05)", showlegend=False), row=1, col=1)

    # EMAs + VWAP
    fig.add_trace(go.Scatter(x=df.index, y=ta.ema(df["close"], 9),  line=dict(color="#ffeb3b", width=1), name="EMA9"),  row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=ta.ema(df["close"], 21), line=dict(color="#ff9800", width=1), name="EMA21"), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=ta.vwap(df), line=dict(color="#e040fb", width=1.5, dash="dot"), name="VWAP"), row=1, col=1)

    # Volume
    vol_colors = ["#00e676" if c >= o else "#ff1744" for c, o in zip(df["close"], df["open"])]
    fig.add_trace(go.Bar(x=df.index, y=df["volume"], marker_color=vol_colors, opacity=0.35, name="Vol"), row=1, col=1)

    # RSI
    rsi = ta.rsi(df["close"])
    fig.add_trace(go.Scatter(x=df.index, y=rsi, line=dict(color="#64b5f6", width=1.5), name="RSI"), row=2, col=1)
    for lvl, col in [(70, "#ff1744"), (30, "#00e676"), (50, "gray")]:
        fig.add_hline(y=lvl, line_dash="dot", line_color=col, opacity=0.4, row=2, col=1)

    # MACD
    ml, sl_line, hist = ta.macd(df["close"])
    hcol = ["#00e676" if v >= 0 else "#ff1744" for v in hist]
    fig.add_trace(go.Bar(x=df.index, y=hist, marker_color=hcol, opacity=0.7, name="Hist"), row=3, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=ml,      line=dict(color="#64b5f6", width=1.5), name="MACD"),   row=3, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=sl_line, line=dict(color="#ff9800", width=1.5), name="Signal"), row=3, col=1)

    fig.update_layout(
        template="plotly_dark", paper_bgcolor="#0d1117", plot_bgcolor="#161b22",
        xaxis_rangeslider_visible=False, height=560,
        margin=dict(l=40, r=10, t=30, b=20),
        legend=dict(orientation="h", y=1.02, bgcolor="rgba(0,0,0,0)"),
        font=dict(color="#e6edf3"),
    )
    fig.update_xaxes(showgrid=True, gridcolor="#21262d")
    fig.update_yaxes(showgrid=True, gridcolor="#21262d")
    return fig


# ── Claude AI ─────────────────────────────────────────────────────────────────
def ask_claude(query: str, context: str) -> str:
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        return "⚠️ Anthropic API key not set. Add ANTHROPIC_API_KEY to .env or Streamlit secrets."
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        msg = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=800,
            system="""You are an expert intraday scalping trader for NSE/BSE Indian markets.
Specialise in NIFTY50, BANKNIFTY, SENSEX and large-cap stocks on 5-minute candles.
Give concise, actionable answers with: probability %, entry level, target, stop loss, key risk.
Use Indian market context (F&O, expiry, NSE/BSE). Be direct — no disclaimers.""",
            messages=[{"role": "user", "content": f"Live Market Data:\n{context}\n\nQuery: {query}"}],
        )
        return msg.content[0].text
    except ImportError:
        return "anthropic package missing. Run: pip install anthropic"
    except Exception as e:
        return f"Claude error: {e}"


# ── Helpers ───────────────────────────────────────────────────────────────────
def pcolor(p: float) -> str:
    return "prob-hi" if p >= 65 else "prob-md" if p >= 50 else "prob-lo"


def market_status() -> tuple[bool, int]:
    from utils.helpers import is_market_hours, time_to_close
    return is_market_hours(), time_to_close()


# ══════════════════════════════════════════════════════════════════════════════
#  MAIN APP
# ══════════════════════════════════════════════════════════════════════════════
def main():
    bot = init_components()

    # ── Sidebar ───────────────────────────────────────────────────────────────
    with st.sidebar:
        st.markdown("## 📈 Scalper Bot")
        st.caption(datetime.now().strftime("%d %b %Y  %H:%M:%S"))

        mkt_open, ttc = market_status()
        if mkt_open:
            st.success(f"🟢 Market OPEN  |  {ttc} min left")
        else:
            st.error("🔴 Market CLOSED")

        st.info("Data: yfinance (NSE/BSE live)", icon="📡")

        symbol = st.selectbox("Instrument", bot["syms"], index=0)

        col_r, col_a = st.columns(2)
        with col_r:
            if st.button("🔄 Refresh", use_container_width=True):
                st.cache_data.clear()
                st.rerun()
        with col_a:
            auto = st.toggle("Auto 30s")

        st.divider()
        st.caption("⚠️ Educational use only — not financial advice.")

    if auto:
        time.sleep(30)
        st.cache_data.clear()
        st.rerun()

    # ── Tabs ──────────────────────────────────────────────────────────────────
    t1, t2, t3, t4, t5 = st.tabs([
        "📊 Live Dashboard", "🔬 Deep Analysis",
        "🤖 Claude AI", "📝 Paper Trading", "📈 Backtest",
    ])

    # ════════════════════════════════════════════════════════
    #  TAB 1 — LIVE DASHBOARD
    # ════════════════════════════════════════════════════════
    with t1:
        df = load_data(symbol)
        if df is None or df.empty:
            st.warning(f"No data for **{symbol}**. Market may be closed or yfinance unavailable.")
            st.stop()

        ta   = bot["ta"].full_analysis(df)
        sig  = bot["eng"].generate_signal(df, symbol)
        prob = bot["prob"].quick_probability(df, symbol)
        exp  = bot["ea"].expiry_volatility_pattern(symbol.replace("50", ""))

        # ── KPI row ──────────────────────────────────────────
        k1, k2, k3, k4, k5, k6 = st.columns(6)
        price = ta.get("price", 0)
        rsi   = ta.get("rsi", 0)
        atr   = ta.get("atr", 0)
        vwap  = ta.get("vwap", 0)
        p     = prob.get("probability", 50)

        k1.metric("💰 Price",    f"{price:,.2f}",  delta=f"ATR {atr:.1f}")
        k2.metric("📊 RSI",      f"{rsi:.1f}",     delta="Oversold" if rsi < 30 else "Overbought" if rsi > 70 else "Neutral")
        k3.metric("〰️ VWAP",    f"{vwap:,.2f}",   delta="Above" if ta.get("above_vwap") else "Below")
        k4.metric("📈 Trend",    ta.get("trend", "—"),  delta=ta.get("structure", ""))
        k5.metric("🎯 Prob",     f"{p:.0f}%")
        k6.metric("⚡ Signal",   sig.get("signal", "WAIT"))

        st.divider()

        # ── Chart + Signal panel ──────────────────────────────
        ch_col, sp_col = st.columns([3, 1])

        with ch_col:
            try:
                fig = build_chart(df.tail(120), symbol, bot["ta"])
                st.plotly_chart(fig, use_container_width=True, key="c1")
            except Exception as e:
                st.error(f"Chart error: {e}")

        with sp_col:
            sig_type = sig.get("signal", "WAIT")
            st.markdown(f'<div class="signal-{sig_type}">{sig_type}</div>', unsafe_allow_html=True)
            st.caption(f"Quality: **{sig.get('quality','')}**")
            st.markdown("---")

            if sig.get("entry"):
                st.metric("Entry", f"{sig['entry']:,.2f}")
            if sig.get("stop_loss"):
                sl_diff = abs(sig['entry'] - sig['stop_loss'])
                st.metric("Stop Loss", f"{sig['stop_loss']:,.2f}", delta=f"-{sl_diff:.1f}", delta_color="inverse")
            targets = sig.get("targets", [])
            if targets:
                for i, t in enumerate(targets, 1):
                    st.metric(f"Target {i}", f"{t:,.2f}", delta=f"+{abs(t - sig['entry']):.1f}")
            rr = sig.get("risk_reward", 0)
            if rr:
                color = "green" if rr >= 1.5 else "orange"
                st.markdown(f"R/R: **:{color}[{rr}]**")

            st.markdown("---")
            st.markdown(f'<div class="{pcolor(p)}">{p:.0f}%</div>', unsafe_allow_html=True)
            st.caption(f"Buy: {prob.get('buy_probability',0):.0f}%  |  Sell: {prob.get('sell_probability',0):.0f}%")
            st.caption(f"**{prob.get('recommendation','')}**")

            if exp.get("is_expiry"):
                st.warning("🔥 EXPIRY DAY")
                st.caption(f"Targets: {exp.get('recommended_targets','')}")

        # ── Warnings ──────────────────────────────────────────
        for w in sig.get("time_warnings", []):
            st.warning(w)

        # ── Expiry strip ──────────────────────────────────────
        with st.expander(f"📅 Expiry  |  DTE {exp.get('dte',0)}  |  {exp.get('expiry_date','')}"):
            e1, e2, e3, e4 = st.columns(4)
            e1.metric("DTE",          exp.get("dte", ""))
            e2.metric("Multiplier",   f"{exp.get('target_multiplier',1)}x")
            e3.metric("IV Crush",     exp.get("iv_crush_risk", ""))
            e4.metric("Targets",      exp.get("recommended_targets", ""))
            st.caption(exp.get("phase_pattern", ""))

        # ── Market scan ───────────────────────────────────────
        with st.expander("🔍 Market Scan — All Instruments"):
            rows = []
            for sym in bot["syms"]:
                df_s = load_data(sym)
                if df_s is not None and len(df_s) >= 30:
                    s = bot["eng"].generate_signal(df_s, sym)
                    ta_s = s.get("ta", {})
                    rows.append({
                        "Symbol": sym, "Signal": s.get("signal", "WAIT"),
                        "Quality": s.get("quality", ""),
                        "Entry": s.get("entry", ""),
                        "T1": s.get("targets", [""])[0] if s.get("targets") else "",
                        "SL": s.get("stop_loss", ""), "R/R": s.get("risk_reward", ""),
                        "RSI": round(ta_s.get("rsi", 0), 1), "Trend": ta_s.get("trend", ""),
                    })
            if rows:
                scan_df = pd.DataFrame(rows)
                st.dataframe(scan_df, use_container_width=True, hide_index=True)
            else:
                st.info("Fetching scan data...")

    # ════════════════════════════════════════════════════════
    #  TAB 2 — DEEP ANALYSIS
    # ════════════════════════════════════════════════════════
    with t2:
        df = load_data(symbol)
        if df is None:
            st.warning("No data")
            st.stop()

        st.subheader(f"🔬 Deep Analysis — {symbol}")
        ta   = bot["ta"].full_analysis(df)
        vold = bot["va"].full_analysis(df)
        volm = bot["vola"].full_analysis(df)

        dc1, dc2 = st.columns(2)

        with dc1:
            st.markdown("#### Technical Indicators")
            st.dataframe(pd.DataFrame([
                {"Indicator": "RSI (14)",       "Value": ta.get("rsi",""),      "Signal": ta.get("rsi_signal","")},
                {"Indicator": "MACD",           "Value": ta.get("macd",""),     "Signal": ta.get("macd_signal_str","")},
                {"Indicator": "BB Upper",       "Value": ta.get("bb_upper",""), "Signal": ""},
                {"Indicator": "BB Lower",       "Value": ta.get("bb_lower",""), "Signal": ""},
                {"Indicator": "BB Position",    "Value": f"{ta.get('bb_position_pct',0):.1f}%", "Signal": ""},
                {"Indicator": "VWAP",           "Value": ta.get("vwap",""),     "Signal": "Above" if ta.get("above_vwap") else "Below"},
                {"Indicator": "ATR",            "Value": ta.get("atr",""),      "Signal": ""},
                {"Indicator": "Trend",          "Value": ta.get("trend",""),    "Signal": ta.get("structure","")},
                {"Indicator": "EMA 9",          "Value": ta.get("ema9",""),     "Signal": ""},
                {"Indicator": "EMA 21",         "Value": ta.get("ema21",""),    "Signal": ""},
            ]), use_container_width=True, hide_index=True)

            st.markdown("#### Support & Resistance")
            sc1, sc2 = st.columns(2)
            with sc1:
                st.markdown("**🔴 Resistance**")
                for r in ta.get("resistance", []):
                    st.code(str(r))
            with sc2:
                st.markdown("**🟢 Support**")
                for s in ta.get("support", []):
                    st.code(str(s))

        with dc2:
            st.markdown("#### Volatility")
            st.dataframe(pd.DataFrame([
                {"Metric": "HV 5-day",    "Value": f"{vold.get('hv_5day',0)}%"},
                {"Metric": "HV 20-day",   "Value": f"{vold.get('hv_20day',0)}%"},
                {"Metric": "Vol Regime",  "Value": vold.get("vol_regime","")},
                {"Metric": "ATR T1 ↑",    "Value": vold.get("t1_up","")},
                {"Metric": "ATR T2 ↑",    "Value": vold.get("t2_up","")},
                {"Metric": "ATR T1 ↓",    "Value": vold.get("t1_dn","")},
                {"Metric": "ATR T2 ↓",    "Value": vold.get("t2_dn","")},
            ]), use_container_width=True, hide_index=True)

            st.markdown("#### Volume & Momentum")
            vp = volm.get("volume_profile", {})
            st.dataframe(pd.DataFrame([
                {"Metric": "VWAP",          "Value": volm.get("vwap","")},
                {"Metric": "Rel. Volume",   "Value": volm.get("relative_volume","")},
                {"Metric": "Vol Signal",    "Value": volm.get("volume_signal","")},
                {"Metric": "Momentum %",    "Value": f"{volm.get('roc_pct',0):.3f}%"},
                {"Metric": "Mom Signal",    "Value": volm.get("momentum_signal","")},
                {"Metric": "Divergence",    "Value": volm.get("divergence","")},
                {"Metric": "POC",           "Value": vp.get("poc","") if isinstance(vp,dict) else ""},
            ]), use_container_width=True, hide_index=True)

        # Probability breakdown bar chart
        st.markdown("#### Trade Probability Factor Breakdown")
        prob = bot["prob"].quick_probability(df, symbol)
        factors = prob.get("factor_breakdown", {})
        if factors:
            import plotly.graph_objects as go
            bar_fig = go.Figure(go.Bar(
                x=list(factors.values()),
                y=[k.replace("_score","").replace("_"," ").title() for k in factors],
                orientation="h",
                marker_color=["#00e676" if v>=60 else "#ffeb3b" if v>=45 else "#ff1744"
                              for v in factors.values()],
                text=[f"{v:.0f}%" for v in factors.values()],
                textposition="outside",
            ))
            bar_fig.update_layout(
                template="plotly_dark", paper_bgcolor="#0d1117",
                plot_bgcolor="#161b22", height=240,
                margin=dict(l=120, r=40, t=10, b=10),
                xaxis=dict(range=[0, 110]),
            )
            bar_fig.add_vline(x=50, line_dash="dot", line_color="gray", opacity=0.5)
            st.plotly_chart(bar_fig, use_container_width=True, key="factors")

    # ════════════════════════════════════════════════════════
    #  TAB 3 — CLAUDE AI CHAT
    # ════════════════════════════════════════════════════════
    with t3:
        st.subheader("🤖 Claude AI Trading Assistant")
        st.caption("Powered by Anthropic Claude — live market data auto-included in every query")

        if "history" not in st.session_state:
            st.session_state.history = []

        # Build live context string
        df_c = load_data(symbol)
        ctx = "No data available"
        if df_c is not None and not df_c.empty:
            ta_c   = bot["ta"].full_analysis(df_c)
            sig_c  = bot["eng"].generate_signal(df_c, symbol)
            prob_c = bot["prob"].quick_probability(df_c, symbol)
            exp_c  = bot["ea"].expiry_volatility_pattern(symbol.replace("50",""))
            ctx = f"""Symbol: {symbol}
Price: {ta_c.get('price','N/A')}  |  RSI: {ta_c.get('rsi','N/A')} ({ta_c.get('rsi_signal','')})
MACD: {ta_c.get('macd_signal_str','')}  |  Trend: {ta_c.get('trend','')} / {ta_c.get('structure','')}
VWAP: {ta_c.get('vwap','')} ({'above' if ta_c.get('above_vwap') else 'below'})  |  ATR: {ta_c.get('atr','')}
Support: {ta_c.get('support',[])}  |  Resistance: {ta_c.get('resistance',[])}
Signal: {sig_c.get('signal','WAIT')} ({sig_c.get('quality','')})
Entry: {sig_c.get('entry','')}  |  SL: {sig_c.get('stop_loss','')}  |  Targets: {sig_c.get('targets',[])}
Entry Probability: {prob_c.get('probability',50)}%  |  Rec: {prob_c.get('recommendation','')}
Expiry: {exp_c.get('expiry_date','')} DTE={exp_c.get('dte','')} {'⚠️ EXPIRY DAY' if exp_c.get('is_expiry') else ''}
Target Multiplier: {exp_c.get('target_multiplier',1)}x  |  IV Crush: {exp_c.get('iv_crush_risk','')}"""

        # Quick buttons
        st.markdown("**Quick Queries:**")
        qb1, qb2, qb3, qb4 = st.columns(4)
        quick = {
            qb1: f"Should I take {symbol} call right now?",
            qb2: f"What's the probability of {symbol} moving 50 pts up?",
            qb3: f"Is this a good scalping setup for {symbol}?",
            qb4: f"Give me key levels for {symbol} next 30 mins",
        }
        for col, q in quick.items():
            if col.button(q[:28]+"…", use_container_width=True, key=q[:15]):
                with st.spinner("Claude analysing..."):
                    ans = ask_claude(q, ctx)
                st.session_state.history += [{"role":"user","content":q}, {"role":"bot","content":ans}]
                st.rerun()

        st.divider()

        # Chat display
        for m in st.session_state.history:
            if m["role"] == "user":
                st.markdown(f'<div class="chat-user">👤 <b>You:</b> {m["content"]}</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="chat-bot">🤖 <b>Claude:</b><br>{m["content"]}</div>', unsafe_allow_html=True)

        # Input
        with st.form("chat", clear_on_submit=True):
            q_in = st.text_input("Ask anything about the market...",
                placeholder="e.g. Should I take NIFTY call at 24100?  |  What are SBIN key levels?")
            cs, cc = st.columns([4, 1])
            sub = cs.form_submit_button("Ask Claude 🤖", use_container_width=True, type="primary")
            clr = cc.form_submit_button("Clear", use_container_width=True)

        if sub and q_in:
            with st.spinner("Claude analysing market data..."):
                ans = ask_claude(q_in, ctx)
            st.session_state.history += [{"role":"user","content":q_in}, {"role":"bot","content":ans}]
            st.rerun()
        if clr:
            st.session_state.history = []
            st.rerun()

        with st.expander("📋 Market context sent to Claude"):
            st.code(ctx)

    # ════════════════════════════════════════════════════════
    #  TAB 4 — PAPER TRADING
    # ════════════════════════════════════════════════════════
    with t4:
        st.subheader("📝 Paper Trading Dashboard")
        port    = bot["paper"].get_portfolio()
        metrics = port.get("metrics", {})

        pm1, pm2, pm3, pm4, pm5, pm6 = st.columns(6)
        pnl_val = port.get("realized_pnl", 0)
        pm1.metric("Capital",      f"₹{port.get('capital',0):,.0f}")
        pm2.metric("Realized P&L", f"₹{pnl_val:+,.2f}")
        pm3.metric("Open",         port.get("open_positions", 0))
        pm4.metric("Total Trades", metrics.get("total_trades", 0))
        pm5.metric("Win Rate",     f"{metrics.get('win_rate',0):.1f}%")
        pm6.metric("Max DD",       f"₹{metrics.get('max_drawdown',0):,.0f}")

        st.divider()
        pf1, pf2 = st.columns([1, 2])

        with pf1:
            st.markdown("#### New Trade")
            with st.form("new_trade"):
                pt_sym  = st.selectbox("Symbol", bot["syms"], key="pt_s")
                pt_type = st.radio("Type", ["BUY","SELL"], horizontal=True)
                ltp_hint = load_ltp(pt_sym)
                pt_price = st.number_input("Entry Price", value=float(ltp_hint or 0), min_value=0.0, step=0.05)
                pt_qty   = st.number_input("Qty (lots)", min_value=1, value=1, step=1)
                pt_opt   = st.selectbox("Option", ["None","CE","PE"])
                pt_str   = st.number_input("Strike", min_value=0.0, step=50.0)
                if st.form_submit_button("Enter Trade ✅", type="primary", use_container_width=True):
                    if pt_price > 0:
                        tr = bot["paper"].enter_trade(
                            pt_sym, pt_type, pt_price, pt_qty,
                            None if pt_opt=="None" else pt_opt,
                            pt_str if pt_str > 0 else None,
                        )
                        st.success(f"Trade #{tr['id']} entered!")
                        st.rerun()

        with pf2:
            open_t = port.get("open_trades", [])
            if open_t:
                st.markdown("#### Open Positions")
                for tr in open_t:
                    with st.container(border=True):
                        c1, c2, c3 = st.columns([3, 2, 2])
                        c1.markdown(f"**{tr.get('symbol')}** — {tr.get('trade_type')}")
                        c2.markdown(f"Entry `{tr.get('entry_price')}`  Qty `{tr.get('quantity')}`")
                        with st.form(f"exit_{tr['id']}"):
                            ltp_exit = load_ltp(tr.get("symbol",""))
                            ep = st.number_input("Exit price", value=float(ltp_exit or 0), min_value=0.0, step=0.05, key=f"ep{tr['id']}")
                            if st.form_submit_button("Exit 🔴", use_container_width=True):
                                if ep > 0:
                                    res = bot["paper"].exit_trade(tr["id"], ep)
                                    pv  = res.get("pnl",0) or 0
                                    st.success(f"Closed  P&L: ₹{pv:+.2f}")
                                    st.rerun()
            else:
                st.info("No open positions")

        closed = port.get("closed_trades", [])
        if closed:
            st.markdown("#### Trade History")
            hist_df = pd.DataFrame(closed)[["symbol","trade_type","entry_time","entry_price","exit_price","quantity","pnl"]]
            hist_df.columns = ["Symbol","Type","Entry Time","Entry","Exit","Qty","P&L"]
            st.dataframe(hist_df, use_container_width=True, hide_index=True)

    # ════════════════════════════════════════════════════════
    #  TAB 5 — BACKTEST
    # ════════════════════════════════════════════════════════
    with t5:
        st.subheader("📈 Strategy Backtest")
        bc1, bc2 = st.columns([1, 3])
        with bc1:
            bt_sym = st.selectbox("Symbol", bot["syms"], key="bt")
            st.caption("Uses last 5 days of 5-min data")
            run_bt = st.button("Run Backtest ▶", type="primary", use_container_width=True)

        if run_bt:
            with st.spinner("Running..."):
                df_bt = load_data(bt_sym)
            if df_bt is not None:
                result = bot["paper"].backtest_strategy({bt_sym: df_bt}, bot["eng"].generate_signal)
                with bc2:
                    b1,b2,b3,b4,b5 = st.columns(5)
                    b1.metric("Trades",   result.get("total_trades",0))
                    b2.metric("Win Rate", f"{result.get('win_rate',0):.1f}%")
                    b3.metric("P&L",      f"{result.get('total_pnl',0):+.2f}")
                    b4.metric("Max DD",   f"{result.get('max_drawdown',0):.2f}")
                    b5.metric("Avg/Trade",f"{result.get('avg_pnl_per_trade',0):.2f}")

                eq = result.get("equity_curve", [0])
                if len(eq) > 1:
                    import plotly.graph_objects as go
                    pos = eq[-1] >= 0
                    eq_fig = go.Figure(go.Scatter(
                        y=eq, mode="lines",
                        line=dict(color="#00e676" if pos else "#ff1744", width=2),
                        fill="tozeroy",
                        fillcolor="rgba(0,230,118,.1)" if pos else "rgba(255,23,68,.1)",
                    ))
                    eq_fig.update_layout(
                        template="plotly_dark", paper_bgcolor="#0d1117",
                        plot_bgcolor="#161b22", height=280,
                        title="Equity Curve",
                        margin=dict(l=40, r=20, t=40, b=20),
                    )
                    st.plotly_chart(eq_fig, use_container_width=True, key="eq")

                trades = result.get("trades", [])
                if trades:
                    st.dataframe(pd.DataFrame(trades), use_container_width=True, hide_index=True)
            else:
                st.warning("No data for backtest")


if __name__ == "__main__":
    main()
