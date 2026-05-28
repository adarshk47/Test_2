"""
Scalper Bot — Streamlit Dashboard
Run: streamlit run streamlit_app.py
"""
import os
import sys
import time
import threading
from datetime import datetime
from typing import Dict, Optional

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

# ── Page config (must be first Streamlit call) ────────────────────────────────
st.set_page_config(
    page_title="Scalper Bot",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .main { background-color: #0d1117; }
    .stApp { background-color: #0d1117; color: #e6edf3; }
    .metric-card {
        background: #161b22;
        border: 1px solid #30363d;
        border-radius: 8px;
        padding: 12px 16px;
        text-align: center;
    }
    .signal-buy { color: #00e676; font-weight: bold; font-size: 1.4em; }
    .signal-sell { color: #ff1744; font-weight: bold; font-size: 1.4em; }
    .signal-wait { color: #ffeb3b; font-weight: bold; font-size: 1.4em; }
    .prob-high { color: #00e676; font-size: 1.8em; font-weight: bold; }
    .prob-mid  { color: #ffeb3b; font-size: 1.8em; font-weight: bold; }
    .prob-low  { color: #ff1744; font-size: 1.8em; font-weight: bold; }
    div[data-testid="stMetricValue"] { color: #e6edf3; }
    .stButton > button {
        background: #21262d;
        color: #e6edf3;
        border: 1px solid #30363d;
        border-radius: 6px;
    }
    .stButton > button:hover { background: #30363d; border-color: #58a6ff; }
    .chat-user { background: #1f2937; border-radius: 8px; padding: 10px; margin: 4px 0; }
    .chat-bot  { background: #0d2137; border-left: 3px solid #58a6ff; border-radius: 8px; padding: 10px; margin: 4px 0; }
    .stTabs [data-baseweb="tab"] { background: #161b22; color: #8b949e; }
    .stTabs [aria-selected="true"] { color: #58a6ff; border-bottom: 2px solid #58a6ff; }
</style>
""", unsafe_allow_html=True)


# ── Lazy imports with error handling ─────────────────────────────────────────
@st.cache_resource
def load_bot_components():
    try:
        from api.angelone import AngelOneAPI
        from analysis.technical import TechnicalAnalysis
        from analysis.volatility import VolatilityAnalysis
        from analysis.volume import VolumeAnalysis
        from analysis.expiry import ExpiryAnalysis
        from trading.probability import ProbabilityCalculator
        from trading.scalping import ScalpingEngine
        from trading.paper_trading import PaperTradingDashboard
        from database.db_manager import DatabaseManager
        from config import INSTRUMENTS

        api = AngelOneAPI()
        connected = api.connect()
        db = DatabaseManager()
        return {
            "api": api,
            "connected": connected,
            "ta": TechnicalAnalysis(),
            "va": VolatilityAnalysis(),
            "vola": VolumeAnalysis(),
            "ea": ExpiryAnalysis(),
            "prob": ProbabilityCalculator(),
            "engine": ScalpingEngine(),
            "paper": PaperTradingDashboard(db),
            "db": db,
            "instruments": list(INSTRUMENTS.keys()),
        }
    except Exception as e:
        st.error(f"Bot init error: {e}")
        return None


@st.cache_data(ttl=10)
def fetch_data(symbol: str, _api) -> Optional[pd.DataFrame]:
    """Fetch candle data — cached 10 seconds."""
    try:
        if _api and _api.connected:
            df = _api.get_candle_data(symbol, days_back=5)
            if df is not None and not df.empty:
                return df
    except Exception:
        pass
    try:
        from database.db_manager import DatabaseManager
        db = DatabaseManager()
        cached = db.get_cached_candles(symbol, "FIVE_MINUTE", 200)
        if cached:
            df = pd.DataFrame(cached)
            df["timestamp"] = pd.to_datetime(df["timestamp"])
            df = df.set_index("timestamp").sort_index()
            return df[["open", "high", "low", "close", "volume"]].astype(float)
    except Exception:
        pass
    return None


def make_candlestick(df: pd.DataFrame, symbol: str, ta) -> "go.Figure":
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    fig = make_subplots(
        rows=3, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.02,
        row_heights=[0.60, 0.20, 0.20],
    )

    fig.add_trace(go.Candlestick(
        x=df.index, open=df["open"], high=df["high"],
        low=df["low"], close=df["close"], name=symbol,
        increasing_line_color="#00e676", decreasing_line_color="#ff1744",
    ), row=1, col=1)

    bb_upper, bb_mid, bb_lower = ta.bollinger_bands(df["close"])
    fig.add_trace(go.Scatter(x=df.index, y=bb_upper, line=dict(color="rgba(100,181,246,0.4)", width=1), name="BB U", showlegend=False), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=bb_lower, line=dict(color="rgba(100,181,246,0.4)", width=1), name="BB L", fill="tonexty", fillcolor="rgba(100,181,246,0.05)", showlegend=False), row=1, col=1)

    ema9 = ta.ema(df["close"], 9)
    ema21 = ta.ema(df["close"], 21)
    fig.add_trace(go.Scatter(x=df.index, y=ema9, line=dict(color="#ffeb3b", width=1), name="EMA9"), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=ema21, line=dict(color="#ff9800", width=1), name="EMA21"), row=1, col=1)

    vwap = ta.vwap(df)
    fig.add_trace(go.Scatter(x=df.index, y=vwap, line=dict(color="#e040fb", width=1.5, dash="dot"), name="VWAP"), row=1, col=1)

    colors = ["#00e676" if c >= o else "#ff1744" for c, o in zip(df["close"], df["open"])]
    fig.add_trace(go.Bar(x=df.index, y=df["volume"], marker_color=colors, opacity=0.4, name="Vol"), row=1, col=1)

    rsi = ta.rsi(df["close"])
    fig.add_trace(go.Scatter(x=df.index, y=rsi, line=dict(color="#64b5f6", width=1.5), name="RSI"), row=2, col=1)
    for y, c in [(70, "#ff1744"), (30, "#00e676"), (50, "gray")]:
        fig.add_hline(y=y, line_dash="dot", line_color=c, opacity=0.4, row=2, col=1)

    macd_l, sig_l, hist = ta.macd(df["close"])
    hist_colors = ["#00e676" if v >= 0 else "#ff1744" for v in hist]
    fig.add_trace(go.Bar(x=df.index, y=hist, marker_color=hist_colors, opacity=0.7, name="Hist"), row=3, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=macd_l, line=dict(color="#64b5f6", width=1.5), name="MACD"), row=3, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=sig_l, line=dict(color="#ff9800", width=1.5), name="Signal"), row=3, col=1)

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#0d1117",
        plot_bgcolor="#161b22",
        xaxis_rangeslider_visible=False,
        height=550,
        margin=dict(l=40, r=20, t=30, b=20),
        legend=dict(orientation="h", y=1.02, x=0, bgcolor="rgba(0,0,0,0)"),
    )
    fig.update_xaxes(showgrid=True, gridcolor="#21262d")
    fig.update_yaxes(showgrid=True, gridcolor="#21262d")
    return fig


def prob_color_class(p: float) -> str:
    if p >= 65:
        return "prob-high"
    if p >= 50:
        return "prob-mid"
    return "prob-low"


def signal_class(sig: str) -> str:
    return {"BUY": "signal-buy", "SELL": "signal-sell"}.get(sig, "signal-wait")


# ── Claude AI helper ─────────────────────────────────────────────────────────
def ask_claude(query: str, context: str) -> str:
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        return "Anthropic API key not set in .env"
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        system = """You are an expert intraday scalping trader specializing in NSE/BSE Indian markets.
You analyze NIFTY50, BANKNIFTY, SENSEX, and individual stocks for 5-minute scalping opportunities.
You answer in a concise, trader-friendly style. Give specific entry/exit levels when asked.
Always mention: probability of success, entry level, target, stop loss, and key risks.
Be direct and actionable. Use Indian market context (NSE, BSE, F&O, expiry days)."""

        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=800,
            system=system,
            messages=[{"role": "user", "content": f"Market Context:\n{context}\n\nTrader Query: {query}"}],
        )
        return message.content[0].text
    except ImportError:
        return "anthropic package not installed. Run: pip install anthropic"
    except Exception as e:
        return f"Claude API error: {e}"


# ── Main App ─────────────────────────────────────────────────────────────────
def main():
    bot = load_bot_components()

    # Sidebar
    with st.sidebar:
        st.markdown("## 📈 Scalper Bot")
        st.markdown(f"**{datetime.now().strftime('%d %b %Y  %H:%M:%S')}**")

        from utils.helpers import is_market_hours, time_to_close
        if is_market_hours():
            st.success("Market: OPEN")
            st.caption(f"Time to close: {time_to_close()} min")
        else:
            st.error("Market: CLOSED")

        if bot:
            st.success("AngelOne: Connected" if bot["connected"] else "AngelOne: Offline")
        st.divider()

        symbol = st.selectbox("Instrument", bot["instruments"] if bot else ["NIFTY50", "SBIN", "BANKNIFTY", "SENSEX"], index=0)
        auto_refresh = st.toggle("Auto Refresh (5s)", value=False)
        if st.button("🔄 Refresh Now"):
            st.cache_data.clear()
            st.rerun()

        st.divider()
        st.caption("⚠️ For educational use only. Not financial advice.")

    if not bot:
        st.error("Bot components failed to load. Check requirements.")
        return

    # Auto-refresh
    if auto_refresh:
        time.sleep(5)
        st.cache_data.clear()
        st.rerun()

    # Tabs
    tab_live, tab_analysis, tab_ai, tab_paper, tab_backtest = st.tabs([
        "📊 Live Dashboard", "🔬 Deep Analysis", "🤖 Claude AI", "📝 Paper Trading", "📈 Backtest"
    ])

    # ── TAB 1: LIVE DASHBOARD ────────────────────────────────────────────────
    with tab_live:
        df = fetch_data(symbol, bot["api"])
        if df is None or df.empty:
            st.warning(f"No data for {symbol}. Check API credentials or internet connection.")
            st.stop()

        ta_data = bot["ta"].full_analysis(df)
        sig = bot["engine"].generate_signal(df, symbol)
        prob = bot["prob"].quick_probability(df, symbol)
        expiry = bot["ea"].expiry_volatility_pattern(symbol.replace("50", ""))

        # Top metrics row
        col1, col2, col3, col4, col5, col6 = st.columns(6)
        price = ta_data.get("price", 0)
        atr = ta_data.get("atr", 0)
        rsi = ta_data.get("rsi", 0)
        vwap = ta_data.get("vwap", 0)
        p = prob.get("probability", 50)
        sig_type = sig.get("signal", "WAIT")

        col1.metric("Price", f"{price:,.2f}", delta=f"ATR {atr:.1f}")
        col2.metric("RSI (14)", f"{rsi:.1f}", delta="Oversold" if rsi < 30 else ("Overbought" if rsi > 70 else "Neutral"))
        col3.metric("VWAP", f"{vwap:,.2f}", delta="Above" if ta_data.get("above_vwap") else "Below")
        col4.metric("Trend", ta_data.get("trend", ""), delta=ta_data.get("structure", ""))
        col5.metric("Entry Prob", f"{p:.0f}%")
        col6.metric("Signal", sig_type)

        st.divider()

        # Chart + Signal side by side
        chart_col, sig_col = st.columns([3, 1])
        with chart_col:
            try:
                fig = make_candlestick(df.tail(100), symbol, bot["ta"])
                st.plotly_chart(fig, use_container_width=True, key="main_chart")
            except Exception as e:
                st.error(f"Chart error: {e}")

        with sig_col:
            st.markdown(f"### Signal")
            st.markdown(f'<div class="{signal_class(sig_type)}">{sig_type}</div>', unsafe_allow_html=True)
            st.caption(f"Quality: **{sig.get('quality', '')}**")

            if sig.get("entry"):
                st.metric("Entry", f"{sig['entry']:,.2f}")
            if sig.get("stop_loss"):
                st.metric("Stop Loss", f"{sig['stop_loss']:,.2f}", delta=f"-{abs(sig['entry'] - sig['stop_loss']):.1f}", delta_color="inverse")
            targets = sig.get("targets", [])
            if targets:
                st.markdown("**Targets**")
                for i, t in enumerate(targets, 1):
                    st.metric(f"T{i}", f"{t:,.2f}", delta=f"+{abs(t - sig['entry']):.1f}")

            if sig.get("risk_reward"):
                color = "green" if sig["risk_reward"] >= 2 else "orange"
                st.markdown(f"R/R: **:{color}[{sig['risk_reward']}]**")

            st.divider()
            st.markdown(f"**Probability**")
            st.markdown(f'<div class="{prob_color_class(p)}">{p:.0f}%</div>', unsafe_allow_html=True)
            st.caption(f"Buy: {prob.get('buy_probability', 0):.0f}%  |  Sell: {prob.get('sell_probability', 0):.0f}%")
            st.caption(f"Recommendation: **{prob.get('recommendation', '')}**")

            if expiry.get("is_expiry"):
                st.warning("🔥 EXPIRY DAY")
                st.caption(expiry.get("phase_pattern", ""))

        # Warnings
        for w in sig.get("time_warnings", []):
            st.warning(w)

        # Expiry bar
        with st.expander(f"📅 Expiry Info — DTE: {expiry.get('dte', 0)} | {expiry.get('expiry_date', '')}"):
            ec1, ec2, ec3, ec4 = st.columns(4)
            ec1.metric("Days to Expiry", expiry.get("dte", ""))
            ec2.metric("Target Multiplier", f"{expiry.get('target_multiplier', 1)}x")
            ec3.metric("IV Crush Risk", expiry.get("iv_crush_risk", ""))
            ec4.metric("Targets", expiry.get("recommended_targets", ""))
            st.caption(expiry.get("phase_pattern", ""))

        # Market scan
        with st.expander("🔍 Market Scan — All Instruments"):
            scan_data = []
            for sym_scan in bot["instruments"]:
                df_s = fetch_data(sym_scan, bot["api"])
                if df_s is not None and len(df_s) >= 30:
                    s = bot["engine"].generate_signal(df_s, sym_scan)
                    ta_s = s.get("ta", {})
                    scan_data.append({
                        "Symbol": sym_scan,
                        "Signal": s.get("signal", "WAIT"),
                        "Quality": s.get("quality", ""),
                        "Entry": s.get("entry", ""),
                        "T1": s.get("targets", [""])[0] if s.get("targets") else "",
                        "SL": s.get("stop_loss", ""),
                        "R/R": s.get("risk_reward", ""),
                        "RSI": ta_s.get("rsi", ""),
                        "Trend": ta_s.get("trend", ""),
                    })
            if scan_data:
                scan_df = pd.DataFrame(scan_data)

                def color_signal(val):
                    if val == "BUY":
                        return "color: #00e676; font-weight: bold"
                    if val == "SELL":
                        return "color: #ff1744; font-weight: bold"
                    return "color: #ffeb3b"

                st.dataframe(
                    scan_df.style.applymap(color_signal, subset=["Signal"]),
                    use_container_width=True,
                    hide_index=True,
                )

    # ── TAB 2: DEEP ANALYSIS ─────────────────────────────────────────────────
    with tab_analysis:
        df = fetch_data(symbol, bot["api"])
        if df is None:
            st.warning("No data available")
            st.stop()

        st.subheader(f"Deep Analysis — {symbol}")

        a_col1, a_col2 = st.columns(2)
        ta_data = bot["ta"].full_analysis(df)
        vol_data = bot["va"].full_analysis(df)
        vol_ana = bot["vola"].full_analysis(df)

        with a_col1:
            st.markdown("#### Technical Indicators")
            ta_df = pd.DataFrame([
                {"Indicator": "RSI (14)", "Value": ta_data.get("rsi", ""), "Signal": ta_data.get("rsi_signal", "")},
                {"Indicator": "MACD", "Value": ta_data.get("macd", ""), "Signal": ta_data.get("macd_signal_str", "")},
                {"Indicator": "BB Position", "Value": f"{ta_data.get('bb_position_pct', 0):.1f}%", "Signal": ""},
                {"Indicator": "BB Upper", "Value": ta_data.get("bb_upper", ""), "Signal": ""},
                {"Indicator": "BB Lower", "Value": ta_data.get("bb_lower", ""), "Signal": ""},
                {"Indicator": "VWAP", "Value": ta_data.get("vwap", ""), "Signal": "Above" if ta_data.get("above_vwap") else "Below"},
                {"Indicator": "ATR", "Value": ta_data.get("atr", ""), "Signal": ""},
                {"Indicator": "Trend", "Value": ta_data.get("trend", ""), "Signal": ta_data.get("structure", "")},
                {"Indicator": "EMA 9", "Value": ta_data.get("ema9", ""), "Signal": ""},
                {"Indicator": "EMA 21", "Value": ta_data.get("ema21", ""), "Signal": ""},
            ])
            st.dataframe(ta_df, use_container_width=True, hide_index=True)

            st.markdown("#### Support & Resistance")
            s_r_col1, s_r_col2 = st.columns(2)
            with s_r_col1:
                st.markdown("**Resistance**")
                for r in ta_data.get("resistance", []):
                    st.markdown(f"🔴 `{r}`")
            with s_r_col2:
                st.markdown("**Support**")
                for s in ta_data.get("support", []):
                    st.markdown(f"🟢 `{s}`")

        with a_col2:
            st.markdown("#### Volatility Analysis")
            vol_df = pd.DataFrame([
                {"Metric": "HV 5-day", "Value": f"{vol_data.get('hv_5day', 0)}%"},
                {"Metric": "HV 20-day", "Value": f"{vol_data.get('hv_20day', 0)}%"},
                {"Metric": "HV 50-day", "Value": f"{vol_data.get('hv_50day', 0)}%"},
                {"Metric": "Vol Regime", "Value": vol_data.get("vol_regime", "")},
                {"Metric": "ATR T1 ↑", "Value": vol_data.get("t1_up", "")},
                {"Metric": "ATR T2 ↑", "Value": vol_data.get("t2_up", "")},
                {"Metric": "ATR T1 ↓", "Value": vol_data.get("t1_dn", "")},
            ])
            st.dataframe(vol_df, use_container_width=True, hide_index=True)

            st.markdown("#### Volume & Momentum")
            vol_m_df = pd.DataFrame([
                {"Metric": "VWAP", "Value": vol_ana.get("vwap", "")},
                {"Metric": "Relative Volume", "Value": vol_ana.get("relative_volume", "")},
                {"Metric": "Volume Signal", "Value": vol_ana.get("volume_signal", "")},
                {"Metric": "Momentum %", "Value": f"{vol_ana.get('roc_pct', 0):.4f}%"},
                {"Metric": "Momentum Signal", "Value": vol_ana.get("momentum_signal", "")},
                {"Metric": "Divergence", "Value": vol_ana.get("divergence", "")},
            ])
            st.dataframe(vol_m_df, use_container_width=True, hide_index=True)

            vp = vol_ana.get("volume_profile", {})
            if isinstance(vp, dict):
                poc = vp.get("poc")
                hvn = vp.get("high_volume_nodes", [])
                lvn = vp.get("low_volume_nodes", [])
                if poc:
                    st.metric("Point of Control (POC)", poc)
                if hvn:
                    st.caption(f"High Volume Nodes: {hvn}")
                if lvn:
                    st.caption(f"Low Volume Nodes (weak areas): {lvn}")

        # Probability factor breakdown
        st.markdown("#### Probability Factor Breakdown")
        prob = bot["prob"].quick_probability(df, symbol)
        factors = prob.get("factor_breakdown", {})
        if factors:
            import plotly.graph_objects as go
            fig_prob = go.Figure(go.Bar(
                x=list(factors.values()),
                y=[k.replace("_score", "").replace("_", " ").title() for k in factors],
                orientation="h",
                marker_color=["#00e676" if v >= 60 else "#ffeb3b" if v >= 45 else "#ff1744" for v in factors.values()],
            ))
            fig_prob.update_layout(
                template="plotly_dark",
                paper_bgcolor="#0d1117",
                plot_bgcolor="#161b22",
                height=250,
                margin=dict(l=120, r=20, t=20, b=20),
                xaxis=dict(range=[0, 100]),
            )
            fig_prob.add_vline(x=50, line_dash="dot", line_color="gray", opacity=0.5)
            st.plotly_chart(fig_prob, use_container_width=True, key="prob_chart")

    # ── TAB 3: CLAUDE AI ─────────────────────────────────────────────────────
    with tab_ai:
        st.subheader("🤖 Claude AI Trading Assistant")
        st.caption("Powered by Anthropic Claude — Ask anything about the market")

        if "chat_history" not in st.session_state:
            st.session_state.chat_history = []

        # Build market context for Claude
        df_ctx = fetch_data(symbol, bot["api"])
        context_str = "No market data available"
        if df_ctx is not None and not df_ctx.empty:
            ta_ctx = bot["ta"].full_analysis(df_ctx)
            prob_ctx = bot["prob"].quick_probability(df_ctx, symbol)
            sig_ctx = bot["engine"].generate_signal(df_ctx, symbol)
            expiry_ctx = bot["ea"].expiry_volatility_pattern(symbol.replace("50", ""))
            context_str = f"""
Symbol: {symbol}
Current Price: {ta_ctx.get('price', 'N/A')}
RSI(14): {ta_ctx.get('rsi', 'N/A')} — {ta_ctx.get('rsi_signal', '')}
MACD: {ta_ctx.get('macd_signal_str', 'N/A')}
Trend: {ta_ctx.get('trend', 'N/A')} | Structure: {ta_ctx.get('structure', '')}
VWAP: {ta_ctx.get('vwap', 'N/A')} | Price {'above' if ta_ctx.get('above_vwap') else 'below'} VWAP
ATR: {ta_ctx.get('atr', 'N/A')}
BB Upper: {ta_ctx.get('bb_upper', 'N/A')} | BB Lower: {ta_ctx.get('bb_lower', 'N/A')}
Support: {ta_ctx.get('support', [])} | Resistance: {ta_ctx.get('resistance', [])}
Signal: {sig_ctx.get('signal', 'WAIT')} | Quality: {sig_ctx.get('quality', '')}
Entry: {sig_ctx.get('entry', '')} | SL: {sig_ctx.get('stop_loss', '')} | Targets: {sig_ctx.get('targets', [])}
Entry Probability: {prob_ctx.get('probability', 50)}%
Expiry: {expiry_ctx.get('expiry_date', '')} | DTE: {expiry_ctx.get('dte', '')} | {'EXPIRY DAY' if expiry_ctx.get('is_expiry') else 'Normal day'}
Target Multiplier: {expiry_ctx.get('target_multiplier', 1)}x
"""

        # Quick query buttons
        st.markdown("**Quick Queries:**")
        q_col1, q_col2, q_col3, q_col4 = st.columns(4)
        quick_queries = {
            q_col1: f"Should I take {symbol} call right now?",
            q_col2: f"What's the probability of {symbol} moving 50 points up?",
            q_col3: f"Is this a good scalping setup?",
            q_col4: f"Show {symbol} analysis for next 30 minutes",
        }
        for col, query in quick_queries.items():
            if col.button(query[:30] + "...", use_container_width=True):
                with st.spinner("Claude is analyzing..."):
                    response = ask_claude(query, context_str)
                st.session_state.chat_history.append({"role": "user", "content": query})
                st.session_state.chat_history.append({"role": "assistant", "content": response})

        st.divider()

        # Chat history display
        for msg in st.session_state.chat_history:
            if msg["role"] == "user":
                st.markdown(f'<div class="chat-user">👤 <strong>You:</strong> {msg["content"]}</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="chat-bot">🤖 <strong>Claude:</strong><br>{msg["content"]}</div>', unsafe_allow_html=True)

        # Query input
        with st.form("chat_form", clear_on_submit=True):
            user_query = st.text_input("Ask Claude about the market...",
                placeholder="e.g. Should I take NIFTY call at 24100? What are the key levels?")
            col_send, col_clear = st.columns([4, 1])
            submitted = col_send.form_submit_button("Send", use_container_width=True)
            cleared = col_clear.form_submit_button("Clear", use_container_width=True)

        if submitted and user_query:
            with st.spinner("Claude is analyzing market data..."):
                response = ask_claude(user_query, context_str)
            st.session_state.chat_history.append({"role": "user", "content": user_query})
            st.session_state.chat_history.append({"role": "assistant", "content": response})
            st.rerun()

        if cleared:
            st.session_state.chat_history = []
            st.rerun()

        # Market context preview
        with st.expander("📋 Current Market Context (sent to Claude)"):
            st.code(context_str)

    # ── TAB 4: PAPER TRADING ─────────────────────────────────────────────────
    with tab_paper:
        st.subheader("📝 Paper Trading Dashboard")

        portfolio = bot["paper"].get_portfolio()
        metrics = portfolio.get("metrics", {})

        # Metrics row
        m1, m2, m3, m4, m5, m6 = st.columns(6)
        pnl = portfolio.get("realized_pnl", 0)
        m1.metric("Capital", f"₹{portfolio.get('capital', 0):,.0f}")
        m2.metric("Realized P&L", f"₹{pnl:+,.2f}", delta_color="normal")
        m3.metric("Open Positions", portfolio.get("open_positions", 0))
        m4.metric("Total Trades", metrics.get("total_trades", 0))
        m5.metric("Win Rate", f"{metrics.get('win_rate', 0):.1f}%")
        m6.metric("Max Drawdown", f"₹{metrics.get('max_drawdown', 0):,.0f}")

        st.divider()

        pt_col1, pt_col2 = st.columns([1, 2])

        with pt_col1:
            st.markdown("#### New Paper Trade")
            with st.form("paper_trade_form"):
                pt_sym = st.selectbox("Symbol", bot["instruments"])
                pt_type = st.radio("Type", ["BUY", "SELL"], horizontal=True)
                pt_price = st.number_input("Entry Price", min_value=0.0, step=0.5)

                # Auto-fill current price
                if st.form_submit_button("Get Current Price", type="secondary"):
                    df_pt = fetch_data(pt_sym, bot["api"])
                    if df_pt is not None:
                        st.session_state["pt_price"] = float(df_pt["close"].iloc[-1])

                pt_qty = st.number_input("Quantity (lots)", min_value=1, value=1, step=1)
                pt_opt = st.selectbox("Option Type (optional)", ["None", "CE", "PE"])
                pt_strike = st.number_input("Strike (options only)", min_value=0.0, step=50.0)
                pt_submit = st.form_submit_button("Enter Trade", use_container_width=True, type="primary")

                if pt_submit and pt_price > 0:
                    opt_type = None if pt_opt == "None" else pt_opt
                    strike_val = pt_strike if pt_strike > 0 else None
                    trade = bot["paper"].enter_trade(pt_sym, pt_type, pt_price, pt_qty, opt_type, strike_val)
                    st.success(f"Trade #{trade['id']} entered: {pt_type} {pt_sym} @ {pt_price}")
                    st.rerun()

        with pt_col2:
            # Open positions
            open_trades = portfolio.get("open_trades", [])
            if open_trades:
                st.markdown("#### Open Positions")
                for trade in open_trades:
                    with st.container():
                        tc1, tc2, tc3, tc4 = st.columns([2, 2, 2, 1])
                        tc1.markdown(f"**{trade.get('symbol')}** {trade.get('trade_type')}")
                        tc2.markdown(f"Entry: `{trade.get('entry_price')}`")
                        tc3.markdown(f"Qty: `{trade.get('quantity')}`")
                        with st.form(f"exit_form_{trade['id']}"):
                            exit_p = st.number_input("Exit Price", min_value=0.0, step=0.5, key=f"ep_{trade['id']}")
                            if st.form_submit_button("Exit", use_container_width=True):
                                if exit_p > 0:
                                    result = bot["paper"].exit_trade(trade["id"], exit_p)
                                    pnl_val = result.get("pnl", 0) or 0
                                    if pnl_val >= 0:
                                        st.success(f"Closed +₹{pnl_val:.2f}")
                                    else:
                                        st.error(f"Closed ₹{pnl_val:.2f}")
                                    st.rerun()
            else:
                st.info("No open positions")

        # Trade history table
        closed_trades = portfolio.get("closed_trades", [])
        if closed_trades:
            st.markdown("#### Trade History")
            hist_df = pd.DataFrame(closed_trades)[
                ["symbol", "trade_type", "entry_time", "entry_price", "exit_price", "quantity", "pnl"]
            ].rename(columns={
                "symbol": "Symbol", "trade_type": "Type",
                "entry_time": "Entry Time", "entry_price": "Entry",
                "exit_price": "Exit", "quantity": "Qty", "pnl": "P&L"
            })
            st.dataframe(
                hist_df.style.applymap(
                    lambda v: "color: #00e676" if isinstance(v, (int, float)) and v > 0
                    else "color: #ff1744" if isinstance(v, (int, float)) and v < 0 else "",
                    subset=["P&L"]
                ),
                use_container_width=True,
                hide_index=True,
            )

    # ── TAB 5: BACKTEST ──────────────────────────────────────────────────────
    with tab_backtest:
        st.subheader("📈 Strategy Backtest")
        bt_col1, bt_col2 = st.columns([1, 3])

        with bt_col1:
            bt_sym = st.selectbox("Symbol to Backtest", bot["instruments"], key="bt_sym")
            st.caption("Uses last 10 days of 5-min data")
            run_bt = st.button("Run Backtest", type="primary", use_container_width=True)

        if run_bt:
            with st.spinner(f"Running backtest on {bt_sym}..."):
                df_bt = fetch_data(bt_sym, bot["api"])
                if df_bt is not None:
                    result = bot["paper"].backtest_strategy(
                        {bt_sym: df_bt}, bot["engine"].generate_signal
                    )
                    with bt_col2:
                        m1, m2, m3, m4, m5 = st.columns(5)
                        m1.metric("Total Trades", result.get("total_trades", 0))
                        m2.metric("Win Rate", f"{result.get('win_rate', 0):.1f}%")
                        m3.metric("Total P&L", f"{result.get('total_pnl', 0):+.2f}")
                        m4.metric("Max Drawdown", f"{result.get('max_drawdown', 0):.2f}")
                        m5.metric("Avg P&L/Trade", f"{result.get('avg_pnl_per_trade', 0):.2f}")

                    # Equity curve
                    equity = result.get("equity_curve", [0])
                    if len(equity) > 1:
                        import plotly.graph_objects as go
                        fig_eq = go.Figure()
                        fig_eq.add_trace(go.Scatter(
                            y=equity,
                            mode="lines",
                            line=dict(color="#00e676" if equity[-1] >= 0 else "#ff1744", width=2),
                            fill="tozeroy",
                            fillcolor="rgba(0,230,118,0.1)" if equity[-1] >= 0 else "rgba(255,23,68,0.1)",
                            name="Equity Curve",
                        ))
                        fig_eq.update_layout(
                            template="plotly_dark",
                            paper_bgcolor="#0d1117",
                            plot_bgcolor="#161b22",
                            height=300,
                            title="Equity Curve",
                            margin=dict(l=40, r=20, t=40, b=20),
                        )
                        st.plotly_chart(fig_eq, use_container_width=True, key="eq_curve")

                    # Trade table
                    trades = result.get("trades", [])
                    if trades:
                        st.markdown("**Recent Backtest Trades**")
                        bt_df = pd.DataFrame(trades)
                        st.dataframe(bt_df, use_container_width=True, hide_index=True)
                else:
                    st.warning("No data for backtest")


if __name__ == "__main__":
    main()
