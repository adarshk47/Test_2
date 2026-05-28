"""
Scalper Bot — Streamlit Dashboard
Deploy: https://share.streamlit.io  |  Main file: streamlit_app.py
Local:  streamlit run streamlit_app.py
"""
import os, time
from datetime import datetime
from typing import Dict, Optional

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(
    page_title="Scalper Bot 📈",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
[data-testid="stAppViewContainer"]{background:#0d1117;color:#e6edf3}
[data-testid="stSidebar"]{background:#161b22}
[data-testid="stHeader"]{background:transparent}
.block-container{padding-top:1rem}
.sig-BUY {color:#00e676;font-size:1.8em;font-weight:900}
.sig-SELL{color:#ff1744;font-size:1.8em;font-weight:900}
.sig-WAIT{color:#ffeb3b;font-size:1.8em;font-weight:900}
.prob-hi {color:#00e676;font-size:2.2em;font-weight:900}
.prob-md {color:#ffeb3b;font-size:2.2em;font-weight:900}
.prob-lo {color:#ff1744;font-size:2.2em;font-weight:900}
.chat-u{background:#1f2937;border-radius:8px;padding:10px;margin:4px 0}
.chat-b{background:#0d2137;border-left:3px solid #58a6ff;border-radius:8px;padding:10px;margin:4px 0}
div[data-testid="stMetricValue"]>div{color:#e6edf3!important}
</style>
""", unsafe_allow_html=True)


# ── Helpers ───────────────────────────────────────────────────────────────────
def _anthr_key() -> str:
    k = os.getenv("ANTHROPIC_API_KEY", "")
    if k:
        return k
    try:
        return st.secrets.get("ANTHROPIC_API_KEY", "")
    except Exception:
        return ""


@st.cache_resource(show_spinner="Loading bot…")
def _init():
    from analysis.technical  import TechnicalAnalysis
    from analysis.volatility import VolatilityAnalysis
    from analysis.volume     import VolumeAnalysis
    from analysis.expiry     import ExpiryAnalysis
    from trading.probability import ProbabilityCalculator
    from trading.scalping    import ScalpingEngine
    from trading.paper_trading import PaperTradingDashboard
    from database.db_manager import DatabaseManager
    from config import INSTRUMENTS
    db = DatabaseManager()
    return dict(
        ta=TechnicalAnalysis(), va=VolatilityAnalysis(),
        vola=VolumeAnalysis(), ea=ExpiryAnalysis(),
        prob=ProbabilityCalculator(), eng=ScalpingEngine(),
        paper=PaperTradingDashboard(db), db=db,
        syms=list(INSTRUMENTS.keys()),
    )


@st.cache_data(ttl=60, show_spinner=False)
def _data(symbol: str) -> Optional[pd.DataFrame]:
    try:
        from api.data_fetcher import get_candle_data
        return get_candle_data(symbol, "FIVE_MINUTE", days_back=5)
    except Exception as e:
        st.warning(f"Data fetch error: {e}")
        return None


@st.cache_data(ttl=30, show_spinner=False)
def _ltp(symbol: str) -> Optional[float]:
    try:
        from api.data_fetcher import get_ltp
        return get_ltp(symbol)
    except Exception:
        return None


def _chart(df, symbol, ta):
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True,
                        vertical_spacing=0.02, row_heights=[0.60, 0.20, 0.20])
    fig.add_trace(go.Candlestick(x=df.index, open=df.open, high=df.high,
        low=df.low, close=df.close, name=symbol,
        increasing_line_color="#00e676", decreasing_line_color="#ff1744"), row=1, col=1)
    bb_u, bb_m, bb_l = ta.bollinger_bands(df.close)
    fig.add_trace(go.Scatter(x=df.index, y=bb_u, line=dict(color="rgba(100,181,246,.3)", width=1), showlegend=False), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=bb_l, line=dict(color="rgba(100,181,246,.3)", width=1), fill="tonexty", fillcolor="rgba(100,181,246,.04)", showlegend=False), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=ta.ema(df.close, 9),  line=dict(color="#ffeb3b", width=1), name="EMA9"),  row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=ta.ema(df.close, 21), line=dict(color="#ff9800", width=1), name="EMA21"), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=ta.vwap(df),          line=dict(color="#e040fb", width=1.5, dash="dot"), name="VWAP"), row=1, col=1)
    vc = ["#00e676" if c >= o else "#ff1744" for c, o in zip(df.close, df.open)]
    fig.add_trace(go.Bar(x=df.index, y=df.volume, marker_color=vc, opacity=0.3, name="Vol"), row=1, col=1)
    rsi = ta.rsi(df.close)
    fig.add_trace(go.Scatter(x=df.index, y=rsi, line=dict(color="#64b5f6", width=1.5), name="RSI"), row=2, col=1)
    for y, c in [(70,"#ff1744"),(30,"#00e676"),(50,"gray")]:
        fig.add_hline(y=y, line_dash="dot", line_color=c, opacity=0.4, row=2, col=1)
    ml, sl, hist = ta.macd(df.close)
    hc = ["#00e676" if v >= 0 else "#ff1744" for v in hist]
    fig.add_trace(go.Bar(x=df.index, y=hist, marker_color=hc, opacity=0.7, name="Hist"),   row=3, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=ml, line=dict(color="#64b5f6",width=1.5), name="MACD"),   row=3, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=sl, line=dict(color="#ff9800",width=1.5), name="Signal"), row=3, col=1)
    fig.update_layout(template="plotly_dark", paper_bgcolor="#0d1117",
        plot_bgcolor="#161b22", xaxis_rangeslider_visible=False,
        height=560, margin=dict(l=40,r=10,t=20,b=20),
        legend=dict(orientation="h", y=1.02, bgcolor="rgba(0,0,0,0)"))
    fig.update_xaxes(showgrid=True, gridcolor="#21262d")
    fig.update_yaxes(showgrid=True, gridcolor="#21262d")
    return fig


def _claude(query: str, ctx: str) -> str:
    key = _anthr_key()
    if not key:
        return "⚠️ ANTHROPIC_API_KEY not set. Add it to `.env` or Streamlit Cloud Secrets."
    try:
        import anthropic
        r = anthropic.Anthropic(api_key=key).messages.create(
            model="claude-sonnet-4-6", max_tokens=700,
            system="Expert NSE/BSE intraday scalper. Answer concisely: probability%, entry, target, SL, risk. Indian market context.",
            messages=[{"role":"user","content":f"Live data:\n{ctx}\n\nQuery: {query}"}])
        return r.content[0].text
    except Exception as e:
        return f"Claude error: {e}"


def _pc(p): return "prob-hi" if p>=65 else "prob-md" if p>=50 else "prob-lo"


# ══════════════════════════════════════════════════════════════════════════════
def main():
    bot = _init()

    # ── Sidebar ───────────────────────────────────────────────────────────────
    with st.sidebar:
        st.markdown("## 📈 Scalper Bot")
        st.caption(datetime.now().strftime("%d %b %Y  %H:%M:%S"))
        try:
            from utils.helpers import is_market_hours, time_to_close
            if is_market_hours():
                st.success(f"🟢 Market OPEN  •  {time_to_close()} min left")
            else:
                st.error("🔴 Market CLOSED")
        except Exception:
            pass
        st.info("📡 Data: yfinance (NSE/BSE live)")
        symbol = st.selectbox("Instrument", bot["syms"], index=0)
        if st.button("🔄 Refresh Data", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
        st.divider()
        st.caption("⚠️ Educational use only")

    tabs = st.tabs(["📊 Dashboard","🔬 Analysis","🤖 Claude AI","📝 Paper Trade","📈 Backtest"])

    # ════════════════════════════════════════════════════════
    # TAB 1 — DASHBOARD
    # ════════════════════════════════════════════════════════
    with tabs[0]:
        df = _data(symbol)
        if df is None or df.empty:
            st.error(f"No data for **{symbol}**. Market may be closed or network unavailable.")
            st.info("Market hours: Mon–Fri  9:15 AM – 3:30 PM IST")
            st.stop()

        ta   = bot["ta"].full_analysis(df)
        sig  = bot["eng"].generate_signal(df, symbol)
        prob = bot["prob"].quick_probability(df, symbol)
        exp  = bot["ea"].expiry_volatility_pattern(symbol.replace("50",""))

        # KPIs
        k = st.columns(6)
        k[0].metric("💰 Price",  f"{ta.get('price',0):,.2f}", f"ATR {ta.get('atr',0):.1f}")
        k[1].metric("📊 RSI",    f"{ta.get('rsi',0):.1f}",   "Oversold" if ta.get('rsi',50)<30 else "Overbought" if ta.get('rsi',50)>70 else "Neutral")
        k[2].metric("〰 VWAP",   f"{ta.get('vwap',0):,.2f}", "Above" if ta.get('above_vwap') else "Below")
        k[3].metric("📈 Trend",  ta.get("trend","—"),         ta.get("structure",""))
        k[4].metric("🎯 Prob",   f"{prob.get('probability',50):.0f}%")
        k[5].metric("⚡ Signal", sig.get("signal","WAIT"))
        st.divider()

        # Chart + Signal
        c1, c2 = st.columns([3,1])
        with c1:
            st.plotly_chart(_chart(df.tail(120), symbol, bot["ta"]),
                            use_container_width=True, key="chart_main")
        with c2:
            st.markdown(f'<div class="sig-{sig.get("signal","WAIT")}">{sig.get("signal","WAIT")}</div>', unsafe_allow_html=True)
            st.caption(f"Quality: **{sig.get('quality','')}**")
            st.divider()
            p = prob.get("probability", 50)
            if sig.get("entry"):   st.metric("Entry", f"{sig['entry']:,.2f}")
            if sig.get("stop_loss"): st.metric("Stop Loss", f"{sig['stop_loss']:,.2f}", f"-{abs(sig['entry']-sig['stop_loss']):.1f}", delta_color="inverse")
            for i,t in enumerate(sig.get("targets",[]),1):
                st.metric(f"T{i}", f"{t:,.2f}", f"+{abs(t-sig['entry']):.1f}")
            if sig.get("risk_reward"):
                st.markdown(f"R/R: **{'🟢' if sig['risk_reward']>=1.5 else '🟡'} {sig['risk_reward']}**")
            st.divider()
            st.markdown(f'<div class="{_pc(p)}">{p:.0f}%</div>', unsafe_allow_html=True)
            st.caption(f"Buy {prob.get('buy_probability',0):.0f}%  |  Sell {prob.get('sell_probability',0):.0f}%")
            st.caption(f"**{prob.get('recommendation','')}**")
            if exp.get("is_expiry"):
                st.warning("🔥 EXPIRY DAY")

        for w in sig.get("time_warnings",[]): st.warning(w)

        with st.expander(f"📅 Expiry: DTE {exp.get('dte',0)}  |  {exp.get('expiry_date','')}  |  {exp.get('recommended_targets','')}"):
            ec = st.columns(4)
            ec[0].metric("DTE",          exp.get("dte",""))
            ec[1].metric("Multiplier",   f"{exp.get('target_multiplier',1)}x")
            ec[2].metric("IV Crush Risk",exp.get("iv_crush_risk",""))
            ec[3].metric("Targets",      exp.get("recommended_targets",""))
            st.caption(exp.get("phase_pattern",""))

        with st.expander("🔍 Market Scan"):
            rows=[]
            for sym in bot["syms"]:
                df2 = _data(sym)
                if df2 is not None and len(df2)>=30:
                    s = bot["eng"].generate_signal(df2, sym)
                    ta2= s.get("ta",{})
                    rows.append({"Symbol":sym,"Signal":s.get("signal","WAIT"),
                        "Quality":s.get("quality",""),"Entry":s.get("entry",""),
                        "T1":(s.get("targets",[""])[0] if s.get("targets") else ""),
                        "SL":s.get("stop_loss",""),"R/R":s.get("risk_reward",""),
                        "RSI":round(ta2.get("rsi",0),1),"Trend":ta2.get("trend","")})
            if rows:
                st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    # ════════════════════════════════════════════════════════
    # TAB 2 — ANALYSIS
    # ════════════════════════════════════════════════════════
    with tabs[1]:
        df = _data(symbol)
        if df is None: st.warning("No data"); st.stop()
        ta   = bot["ta"].full_analysis(df)
        vold = bot["va"].full_analysis(df)
        volm = bot["vola"].full_analysis(df)
        st.subheader(f"🔬 Deep Analysis — {symbol}")
        a1, a2 = st.columns(2)
        with a1:
            st.markdown("**Technical Indicators**")
            st.dataframe(pd.DataFrame([
                {"Indicator":"RSI (14)","Value":ta.get("rsi",""),"Signal":ta.get("rsi_signal","")},
                {"Indicator":"MACD","Value":ta.get("macd",""),"Signal":ta.get("macd_signal_str","")},
                {"Indicator":"BB Upper","Value":ta.get("bb_upper",""),"Signal":""},
                {"Indicator":"BB Lower","Value":ta.get("bb_lower",""),"Signal":""},
                {"Indicator":"BB Position","Value":f"{ta.get('bb_position_pct',0):.1f}%","Signal":""},
                {"Indicator":"VWAP","Value":ta.get("vwap",""),"Signal":"Above" if ta.get("above_vwap") else "Below"},
                {"Indicator":"ATR","Value":ta.get("atr",""),"Signal":""},
                {"Indicator":"Trend","Value":ta.get("trend",""),"Signal":ta.get("structure","")},
                {"Indicator":"EMA 9","Value":ta.get("ema9",""),"Signal":""},
                {"Indicator":"EMA 21","Value":ta.get("ema21",""),"Signal":""},
            ]), use_container_width=True, hide_index=True)
            sc1,sc2=st.columns(2)
            with sc1:
                st.markdown("**🔴 Resistance**")
                for r in ta.get("resistance",[]): st.code(str(r))
            with sc2:
                st.markdown("**🟢 Support**")
                for s in ta.get("support",[]): st.code(str(s))
        with a2:
            st.markdown("**Volatility**")
            st.dataframe(pd.DataFrame([
                {"Metric":"HV 5-day","Value":f"{vold.get('hv_5day',0)}%"},
                {"Metric":"HV 20-day","Value":f"{vold.get('hv_20day',0)}%"},
                {"Metric":"Vol Regime","Value":vold.get("vol_regime","")},
                {"Metric":"ATR T1 ↑","Value":vold.get("t1_up","")},
                {"Metric":"ATR T2 ↑","Value":vold.get("t2_up","")},
                {"Metric":"ATR T1 ↓","Value":vold.get("t1_dn","")},
            ]), use_container_width=True, hide_index=True)
            st.markdown("**Volume & Momentum**")
            vp = volm.get("volume_profile",{})
            st.dataframe(pd.DataFrame([
                {"Metric":"VWAP","Value":volm.get("vwap","")},
                {"Metric":"Rel. Volume","Value":volm.get("relative_volume","")},
                {"Metric":"Vol Signal","Value":volm.get("volume_signal","")},
                {"Metric":"Momentum %","Value":f"{volm.get('roc_pct',0):.3f}%"},
                {"Metric":"Mom Signal","Value":volm.get("momentum_signal","")},
                {"Metric":"Divergence","Value":volm.get("divergence","")},
                {"Metric":"POC","Value":vp.get("poc","") if isinstance(vp,dict) else ""},
            ]), use_container_width=True, hide_index=True)
        # Factor chart
        prob = bot["prob"].quick_probability(df, symbol)
        factors = prob.get("factor_breakdown",{})
        if factors:
            import plotly.graph_objects as go
            fig2 = go.Figure(go.Bar(
                x=list(factors.values()),
                y=[k.replace("_score","").replace("_"," ").title() for k in factors],
                orientation="h",
                marker_color=["#00e676" if v>=60 else "#ffeb3b" if v>=45 else "#ff1744" for v in factors.values()],
                text=[f"{v:.0f}%" for v in factors.values()], textposition="outside"))
            fig2.update_layout(template="plotly_dark",paper_bgcolor="#0d1117",
                plot_bgcolor="#161b22",height=240,margin=dict(l=120,r=40,t=10,b=10),
                xaxis=dict(range=[0,110]))
            fig2.add_vline(x=50,line_dash="dot",line_color="gray",opacity=0.5)
            st.plotly_chart(fig2, use_container_width=True, key="factors")

    # ════════════════════════════════════════════════════════
    # TAB 3 — CLAUDE AI
    # ════════════════════════════════════════════════════════
    with tabs[2]:
        st.subheader("🤖 Claude AI Trading Assistant")
        if "hist" not in st.session_state:
            st.session_state.hist = []

        df = _data(symbol)
        ctx = "No data"
        if df is not None and not df.empty:
            ta  = bot["ta"].full_analysis(df)
            sig = bot["eng"].generate_signal(df, symbol)
            pr  = bot["prob"].quick_probability(df, symbol)
            ex  = bot["ea"].expiry_volatility_pattern(symbol.replace("50",""))
            ctx = (f"Symbol:{symbol} Price:{ta.get('price')} RSI:{ta.get('rsi')} "
                   f"MACD:{ta.get('macd_signal_str')} Trend:{ta.get('trend')}/{ta.get('structure')} "
                   f"VWAP:{ta.get('vwap')} ATR:{ta.get('atr')} "
                   f"Support:{ta.get('support')} Resistance:{ta.get('resistance')} "
                   f"Signal:{sig.get('signal')} Entry:{sig.get('entry')} "
                   f"SL:{sig.get('stop_loss')} Targets:{sig.get('targets')} "
                   f"Prob:{pr.get('probability')}% Rec:{pr.get('recommendation')} "
                   f"Expiry:{ex.get('expiry_date')} DTE:{ex.get('dte')} "
                   f"{'EXPIRY DAY' if ex.get('is_expiry') else ''} "
                   f"TargetMult:{ex.get('target_multiplier')}x")

        qs = [f"Should I take {symbol} call now?",
              f"NIFTY call at 24100 — good entry?",
              f"What is probability of {symbol} moving 50 pts?",
              f"Key support/resistance for {symbol}"]
        qc = st.columns(4)
        for col, q in zip(qc, qs):
            if col.button(q[:22]+"…", use_container_width=True, key="qb"+q[:8]):
                with st.spinner("Claude thinking…"):
                    ans = _claude(q, ctx)
                st.session_state.hist += [{"r":"u","t":q},{"r":"b","t":ans}]
                st.rerun()

        st.divider()
        for m in st.session_state.hist:
            tag = "chat-u" if m["r"]=="u" else "chat-b"
            who = "👤 You" if m["r"]=="u" else "🤖 Claude"
            st.markdown(f'<div class="{tag}"><b>{who}:</b> {m["t"]}</div>', unsafe_allow_html=True)

        with st.form("cf", clear_on_submit=True):
            qi = st.text_input("Ask the market…", placeholder="Should I take NIFTY call at 24100?")
            cs,cc = st.columns([4,1])
            sub = cs.form_submit_button("Ask Claude 🤖", type="primary", use_container_width=True)
            clr = cc.form_submit_button("Clear", use_container_width=True)
        if sub and qi:
            with st.spinner("Analysing…"):
                ans = _claude(qi, ctx)
            st.session_state.hist += [{"r":"u","t":qi},{"r":"b","t":ans}]
            st.rerun()
        if clr:
            st.session_state.hist = []
            st.rerun()
        with st.expander("📋 Market context"):
            st.code(ctx)

    # ════════════════════════════════════════════════════════
    # TAB 4 — PAPER TRADING
    # ════════════════════════════════════════════════════════
    with tabs[3]:
        st.subheader("📝 Paper Trading Dashboard")
        port = bot["paper"].get_portfolio()
        mx   = port.get("metrics",{})
        pnl  = port.get("realized_pnl",0)
        mc   = st.columns(6)
        mc[0].metric("Capital",      f"₹{port.get('capital',0):,.0f}")
        mc[1].metric("Realized P&L", f"₹{pnl:+,.2f}")
        mc[2].metric("Open",         port.get("open_positions",0))
        mc[3].metric("Total Trades", mx.get("total_trades",0))
        mc[4].metric("Win Rate",     f"{mx.get('win_rate',0):.1f}%")
        mc[5].metric("Max DD",       f"₹{mx.get('max_drawdown',0):,.0f}")
        st.divider()
        pf1,pf2 = st.columns([1,2])
        with pf1:
            st.markdown("#### New Trade")
            with st.form("nt"):
                pt_sym  = st.selectbox("Symbol", bot["syms"])
                pt_type = st.radio("Type",["BUY","SELL"],horizontal=True)
                ltp_v   = _ltp(pt_sym)
                pt_px   = st.number_input("Entry Price", value=float(ltp_v or 0), min_value=0.0, step=0.05)
                pt_qty  = st.number_input("Qty", min_value=1, value=1, step=1)
                pt_opt  = st.selectbox("Option",["None","CE","PE"])
                pt_str  = st.number_input("Strike", min_value=0.0, step=50.0)
                if st.form_submit_button("Enter ✅", type="primary", use_container_width=True):
                    if pt_px > 0:
                        tr = bot["paper"].enter_trade(pt_sym, pt_type, pt_px, pt_qty,
                                None if pt_opt=="None" else pt_opt,
                                pt_str if pt_str>0 else None)
                        st.success(f"Trade #{tr['id']} entered!")
                        st.rerun()
        with pf2:
            open_t = port.get("open_trades",[])
            if open_t:
                st.markdown("#### Open Positions")
                for tr in open_t:
                    with st.container(border=True):
                        c1,c2 = st.columns([3,2])
                        c1.markdown(f"**{tr.get('symbol')}** {tr.get('trade_type')}  `{tr.get('entry_price')}` × {tr.get('quantity')}")
                        with st.form(f"ex{tr['id']}"):
                            lv = _ltp(tr.get("symbol",""))
                            ep = st.number_input("Exit", value=float(lv or 0), min_value=0.0, step=0.05, key=f"e{tr['id']}")
                            if st.form_submit_button("Exit 🔴", use_container_width=True):
                                if ep>0:
                                    res = bot["paper"].exit_trade(tr["id"], ep)
                                    pv  = res.get("pnl",0) or 0
                                    (st.success if pv>=0 else st.error)(f"P&L: ₹{pv:+.2f}")
                                    st.rerun()
            else:
                st.info("No open positions")
        cl = port.get("closed_trades",[])
        if cl:
            st.markdown("#### History")
            hdf = pd.DataFrame(cl)[["symbol","trade_type","entry_time","entry_price","exit_price","quantity","pnl"]]
            hdf.columns=["Symbol","Type","Entry Time","Entry","Exit","Qty","P&L"]
            st.dataframe(hdf, use_container_width=True, hide_index=True)

    # ════════════════════════════════════════════════════════
    # TAB 5 — BACKTEST
    # ════════════════════════════════════════════════════════
    with tabs[4]:
        st.subheader("📈 Backtest")
        bc1,bc2 = st.columns([1,3])
        with bc1:
            bt_sym = st.selectbox("Symbol", bot["syms"], key="btsym")
            run_bt = st.button("Run ▶", type="primary", use_container_width=True)
        if run_bt:
            df_bt = _data(bt_sym)
            if df_bt is not None:
                with st.spinner("Running backtest…"):
                    res = bot["paper"].backtest_strategy({bt_sym:df_bt}, bot["eng"].generate_signal)
                with bc2:
                    bm = st.columns(5)
                    bm[0].metric("Trades",   res.get("total_trades",0))
                    bm[1].metric("Win Rate", f"{res.get('win_rate',0):.1f}%")
                    bm[2].metric("P&L",      f"{res.get('total_pnl',0):+.2f}")
                    bm[3].metric("Max DD",   f"{res.get('max_drawdown',0):.2f}")
                    bm[4].metric("Avg/Trade",f"{res.get('avg_pnl_per_trade',0):.2f}")
                eq = res.get("equity_curve",[0])
                if len(eq)>1:
                    import plotly.graph_objects as go
                    pos = eq[-1]>=0
                    ef = go.Figure(go.Scatter(y=eq, mode="lines",
                        line=dict(color="#00e676" if pos else "#ff1744",width=2),
                        fill="tozeroy", fillcolor="rgba(0,230,118,.1)" if pos else "rgba(255,23,68,.1)"))
                    ef.update_layout(template="plotly_dark",paper_bgcolor="#0d1117",
                        plot_bgcolor="#161b22",height=280,title="Equity Curve",
                        margin=dict(l=40,r=20,t=40,b=20))
                    st.plotly_chart(ef, use_container_width=True, key="eq")
                if res.get("trades"):
                    st.dataframe(pd.DataFrame(res["trades"]), use_container_width=True, hide_index=True)
            else:
                st.warning("No data for backtest")


if __name__ == "__main__":
    main()
