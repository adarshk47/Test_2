"""
Scalper Bot — Professional Trading Terminal
Run: streamlit run streamlit_app.py
"""
import os, time
from datetime import datetime
from typing import Dict, Optional, List, Tuple
import pandas as pd
import numpy as np
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(page_title="Scalper Bot", page_icon="📈", layout="wide",
                   initial_sidebar_state="collapsed")

# ── Full trading terminal CSS ─────────────────────────────────────────────────
st.markdown("""<style>
/* Base */
html,body,[data-testid="stAppViewContainer"]{background:#0a0e1a!important;color:#e8f0fe}
[data-testid="stSidebar"]{background:#0f1629!important;border-right:1px solid #1e3a5f}
[data-testid="stHeader"]{background:transparent!important}
.block-container{padding:0.5rem 1rem 1rem!important;max-width:100%!important}
/* Hide streamlit branding */
#MainMenu,footer,header{visibility:hidden}
/* Cards */
.card{background:#0f1629;border:1px solid #1e3a5f;border-radius:10px;padding:14px 18px;margin:4px 0}
.card-green{background:#0f1629;border:1px solid #00ff88;border-radius:10px;padding:14px 18px;box-shadow:0 0 12px rgba(0,255,136,0.15)}
.card-red{background:#0f1629;border:1px solid #ff3366;border-radius:10px;padding:14px 18px;box-shadow:0 0 12px rgba(255,51,102,0.15)}
.card-blue{background:#0f1629;border:1px solid #2196f3;border-radius:10px;padding:14px 18px;box-shadow:0 0 12px rgba(33,150,243,0.15)}
/* Signal badges */
.sig-BUY{color:#00ff88;font-size:2.2em;font-weight:900;letter-spacing:2px;text-shadow:0 0 20px rgba(0,255,136,0.5)}
.sig-SELL{color:#ff3366;font-size:2.2em;font-weight:900;letter-spacing:2px;text-shadow:0 0 20px rgba(255,51,102,0.5)}
.sig-WAIT{color:#ffd700;font-size:2.2em;font-weight:900;letter-spacing:2px;text-shadow:0 0 20px rgba(255,215,0,0.4)}
/* Probability meter */
.prob-hi{color:#00ff88;font-size:2.8em;font-weight:900;text-shadow:0 0 25px rgba(0,255,136,0.6)}
.prob-md{color:#ffd700;font-size:2.8em;font-weight:900;text-shadow:0 0 25px rgba(255,215,0,0.5)}
.prob-lo{color:#ff3366;font-size:2.8em;font-weight:900;text-shadow:0 0 25px rgba(255,51,102,0.5)}
/* KPI numbers */
.kpi-num{font-size:1.5em;font-weight:700;font-family:monospace}
.kpi-label{font-size:0.72em;color:#8899aa;text-transform:uppercase;letter-spacing:1px}
.up{color:#00ff88}.dn{color:#ff3366}.neu{color:#8899aa}
/* Global ticker strip */
.ticker-item{display:inline-block;padding:6px 16px;margin:0 4px;background:#0f1629;
  border:1px solid #1e3a5f;border-radius:20px;font-size:0.82em;font-family:monospace}
/* Tabs */
[data-testid="stTabs"] [role="tablist"]{background:#0f1629;border-radius:8px;padding:4px;border:1px solid #1e3a5f}
[data-testid="stTabs"] [role="tab"]{color:#8899aa;border-radius:6px;padding:6px 16px}
[data-testid="stTabs"] [aria-selected="true"]{background:#1e3a5f!important;color:#e8f0fe!important}
/* Metrics */
div[data-testid="stMetricValue"]>div{color:#e8f0fe!important;font-family:monospace!important}
div[data-testid="stMetricLabel"]{color:#8899aa!important;font-size:0.72em!important;text-transform:uppercase}
/* Buttons */
.stButton>button{background:#1e3a5f!important;color:#e8f0fe!important;
  border:1px solid #2196f3!important;border-radius:6px!important;font-weight:600}
.stButton>button:hover{background:#2196f3!important;box-shadow:0 0 12px rgba(33,150,243,0.4)!important}
/* Input fields */
.stSelectbox>div>div,.stTextInput>div>div>input{background:#0f1629!important;
  color:#e8f0fe!important;border:1px solid #1e3a5f!important}
/* Divider */
hr{border-color:#1e3a5f}
/* Chat */
.chat-u{background:#0f1629;border:1px solid #1e3a5f;border-radius:8px;padding:10px 14px;margin:6px 0}
.chat-b{background:#091429;border-left:3px solid #2196f3;border-radius:8px;padding:10px 14px;margin:6px 0}
/* Table */
[data-testid="stDataFrame"]{border:1px solid #1e3a5f;border-radius:8px}
</style>""", unsafe_allow_html=True)


# ── Helpers / cache ───────────────────────────────────────────────────────────
def _anthr_key():
    k = os.getenv("ANTHROPIC_API_KEY","")
    if k: return k
    try: return st.secrets.get("ANTHROPIC_API_KEY","")
    except: return ""

@st.cache_resource(show_spinner="Initialising trading terminal…")
def _init():
    from analysis.technical    import TechnicalAnalysis
    from analysis.volatility   import VolatilityAnalysis
    from analysis.volume       import VolumeAnalysis
    from analysis.expiry       import ExpiryAnalysis
    from trading.probability   import ProbabilityCalculator
    from trading.scalping      import ScalpingEngine
    from trading.paper_trading import PaperTradingDashboard
    from database.db_manager   import DatabaseManager
    from config import INSTRUMENTS
    from api.data_fetcher import _login
    _login()                                      # one-time AngelOne session
    db = DatabaseManager()
    return dict(
        ta=TechnicalAnalysis(), va=VolatilityAnalysis(),
        vola=VolumeAnalysis(), ea=ExpiryAnalysis(),
        prob=ProbabilityCalculator(), eng=ScalpingEngine(),
        paper=PaperTradingDashboard(db), db=db,
        syms=list(INSTRUMENTS.keys()),
    )

@st.cache_data(ttl=60, show_spinner=False)
def _candles(sym):
    from api.data_fetcher import get_candle_data
    return get_candle_data(sym,"FIVE_MINUTE",5)

@st.cache_data(ttl=30, show_spinner=False)
def _ltp(sym):
    from api.data_fetcher import get_ltp
    return get_ltp(sym)

@st.cache_data(ttl=60, show_spinner=False)
def _global_quote(ticker:str) -> Tuple[float,float,float]:
    """(price, change, change_pct)  for any yfinance ticker"""
    try:
        import yfinance as yf
        t = yf.Ticker(ticker)
        hist = t.history(period="2d", interval="1h")
        if hist is None or hist.empty: return (0,0,0)
        last  = float(hist["Close"].iloc[-1])
        prev  = float(hist["Close"].iloc[-25]) if len(hist)>25 else float(hist["Close"].iloc[0])
        chg   = last - prev
        pct   = chg/prev*100 if prev else 0
        return (round(last,2), round(chg,2), round(pct,2))
    except: return (0,0,0)


# ── Chart builder ─────────────────────────────────────────────────────────────
def _chart(df, symbol, ta):
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    fig = make_subplots(rows=3,cols=1,shared_xaxes=True,
                        vertical_spacing=0.015,row_heights=[0.60,0.20,0.20])
    # Candles
    fig.add_trace(go.Candlestick(x=df.index,open=df.open,high=df.high,
        low=df.low,close=df.close,name=symbol,
        increasing=dict(line_color="#00ff88",fillcolor="#00ff88"),
        decreasing=dict(line_color="#ff3366",fillcolor="#ff3366")),row=1,col=1)
    # BB
    bbu,bbm,bbl = ta.bollinger_bands(df.close)
    fig.add_trace(go.Scatter(x=df.index,y=bbu,line=dict(color="rgba(33,150,243,.4)",width=1),showlegend=False,name="BB"),row=1,col=1)
    fig.add_trace(go.Scatter(x=df.index,y=bbl,line=dict(color="rgba(33,150,243,.4)",width=1),fill="tonexty",fillcolor="rgba(33,150,243,.05)",showlegend=False),row=1,col=1)
    # EMAs
    fig.add_trace(go.Scatter(x=df.index,y=ta.ema(df.close,9), line=dict(color="#ffd700",width=1.2),name="EMA9"),row=1,col=1)
    fig.add_trace(go.Scatter(x=df.index,y=ta.ema(df.close,21),line=dict(color="#ff9800",width=1.2),name="EMA21"),row=1,col=1)
    fig.add_trace(go.Scatter(x=df.index,y=ta.vwap(df),line=dict(color="#e040fb",width=1.5,dash="dot"),name="VWAP"),row=1,col=1)
    # Volume
    vc=["#00ff88" if c>=o else "#ff3366" for c,o in zip(df.close,df.open)]
    fig.add_trace(go.Bar(x=df.index,y=df.volume,marker_color=vc,opacity=0.3,name="Vol",showlegend=False),row=1,col=1)
    # RSI
    rsi=ta.rsi(df.close)
    fig.add_trace(go.Scatter(x=df.index,y=rsi,line=dict(color="#2196f3",width=1.5),name="RSI",fill="tozeroy",fillcolor="rgba(33,150,243,.08)"),row=2,col=1)
    for y,c in [(70,"#ff3366"),(30,"#00ff88"),(50,"rgba(136,153,170,.4)")]:
        fig.add_hline(y=y,line_dash="dot",line_color=c,opacity=0.5,row=2,col=1)
    # MACD
    ml,sl_,hist=ta.macd(df.close)
    hc=["#00ff88" if v>=0 else "#ff3366" for v in hist]
    fig.add_trace(go.Bar(x=df.index,y=hist,marker_color=hc,opacity=0.8,name="Hist",showlegend=False),row=3,col=1)
    fig.add_trace(go.Scatter(x=df.index,y=ml, line=dict(color="#2196f3",width=1.5),name="MACD"),row=3,col=1)
    fig.add_trace(go.Scatter(x=df.index,y=sl_,line=dict(color="#ff9800",width=1.5),name="Sig"),row=3,col=1)
    fig.update_layout(
        template="plotly_dark",paper_bgcolor="#0a0e1a",plot_bgcolor="#0f1629",
        xaxis_rangeslider_visible=False,height=540,
        margin=dict(l=50,r=10,t=10,b=10),
        legend=dict(orientation="h",y=1.01,x=0,bgcolor="rgba(0,0,0,0)",font=dict(size=11)),
        font=dict(color="#8899aa"))
    fig.update_xaxes(showgrid=True,gridcolor="#1e3a5f",zeroline=False)
    fig.update_yaxes(showgrid=True,gridcolor="#1e3a5f",zeroline=False)
    return fig


def _prob_bar(p:float) -> str:
    filled = int(p/5)
    empty  = 20-filled
    color  = "#00ff88" if p>=65 else "#ffd700" if p>=50 else "#ff3366"
    bar = f'<span style="color:{color}">{"█"*filled}</span><span style="color:#1e3a5f">{"░"*empty}</span>'
    cls = "prob-hi" if p>=65 else "prob-md" if p>=50 else "prob-lo"
    return f'<div class="{cls}">{p:.0f}%</div><div style="font-size:1.1em;letter-spacing:2px">{bar}</div>'


def _delta_html(val:float, label:str="") -> str:
    if val>0: return f'<span class="up">▲ {val:+.2f}{label}</span>'
    if val<0: return f'<span class="dn">▼ {val:.2f}{label}</span>'
    return f'<span class="neu">— 0{label}</span>'


def _claude(q:str,ctx:str)->str:
    key=_anthr_key()
    if not key: return "⚠️ Add ANTHROPIC_API_KEY to .env or Streamlit Secrets."
    try:
        import anthropic
        r=anthropic.Anthropic(api_key=key).messages.create(
            model="claude-sonnet-4-6",max_tokens=700,
            system="Expert NSE/BSE intraday scalper. Give: probability%, entry, T1/T2/T3 targets, stop loss, R/R, key risk. Indian market context. Be direct.",
            messages=[{"role":"user","content":f"Live market data:\n{ctx}\n\nQuery: {q}"}])
        return r.content[0].text
    except Exception as e: return f"Claude error: {e}"


# ── Global indices config ─────────────────────────────────────────────────────
GLOBAL_INDICES = [
    ("GIFT Nifty*","^NSEI","pts"),
    ("DOW","^DJI","pts"),
    ("S&P 500","^GSPC","pts"),
    ("NASDAQ","^IXIC","pts"),
    ("Nikkei","^N225","pts"),
    ("Hang Seng","^HSI","pts"),
    ("Gold","GC=F","$/oz"),
    ("Crude","CL=F","$/bbl"),
    ("VIX","^VIX",""),
    ("USD/INR","USDINR=X","₹"),
]


# ══════════════════════════════════════════════════════════════════════════════
def main():
    bot = _init()
    from api.data_fetcher import get_data_source
    src = get_data_source()

    # ── Sidebar ───────────────────────────────────────────────────────────────
    with st.sidebar:
        st.markdown("### ⚡ Scalper Bot")
        badge = "🟢 **AngelOne Live**" if src=="AngelOne" else "🟡 **yfinance NSE**"
        st.markdown(badge)
        st.caption(datetime.now().strftime("%d %b %Y  %H:%M:%S IST"))
        try:
            from utils.helpers import is_market_hours, time_to_close
            if is_market_hours():
                st.success(f"Market OPEN  •  {time_to_close()} min")
            else:
                st.error("Market CLOSED")
        except: pass
        st.divider()
        symbol = st.selectbox("Instrument", bot["syms"], index=0,
                              label_visibility="collapsed")
        c1,c2 = st.columns(2)
        if c1.button("🔄 Refresh", use_container_width=True):
            st.cache_data.clear(); st.rerun()
        if c2.button("🔁 Reconnect", use_container_width=True):
            st.cache_resource.clear(); st.rerun()
        st.divider()
        st.caption("⚠️ Educational only — not financial advice\n\n*GIFT Nifty: using Nifty spot as proxy")

    # ── Header ────────────────────────────────────────────────────────────────
    hc1,hc2,hc3 = st.columns([3,2,2])
    with hc1:
        st.markdown('<span style="font-size:1.6em;font-weight:900;color:#2196f3">📈 SCALPER BOT</span>'
                    '<span style="color:#8899aa;font-size:0.9em"> &nbsp;|&nbsp; NSE/BSE Intraday</span>',
                    unsafe_allow_html=True)
    with hc2:
        try:
            from utils.helpers import is_market_hours, time_to_close
            if is_market_hours():
                st.markdown(f'<div style="text-align:center"><span style="color:#00ff88;font-size:1.1em;font-weight:700">● MARKET OPEN</span><br>'
                            f'<span style="color:#8899aa;font-size:0.85em">{time_to_close()} min remaining</span></div>',unsafe_allow_html=True)
            else:
                st.markdown('<div style="text-align:center"><span style="color:#ff3366;font-size:1.1em;font-weight:700">● MARKET CLOSED</span><br>'
                            '<span style="color:#8899aa;font-size:0.85em">Opens 9:15 AM IST</span></div>',unsafe_allow_html=True)
        except: pass
    with hc3:
        st.markdown(f'<div style="text-align:right;color:#8899aa;font-size:0.9em">'
                    f'<b style="color:#2196f3">{src}</b><br>{datetime.now().strftime("%H:%M:%S IST")}</div>',
                    unsafe_allow_html=True)

    # ── Global ticker strip ───────────────────────────────────────────────────
    st.markdown("---")
    ticker_parts = []
    for name, ticker, unit in GLOBAL_INDICES:
        price,chg,pct = _global_quote(ticker)
        if price:
            color = "#00ff88" if chg>=0 else "#ff3366"
            arrow = "▲" if chg>=0 else "▼"
            ticker_parts.append(
                f'<span class="ticker-item"><b style="color:#8899aa">{name}</b>&nbsp;'
                f'<b style="color:{color};font-family:monospace">{price:,.1f}</b>&nbsp;'
                f'<span style="color:{color};font-size:0.85em">{arrow}{abs(pct):.1f}%</span></span>')
    if ticker_parts:
        st.markdown('<div style="overflow-x:auto;white-space:nowrap;padding:6px 0">'+"".join(ticker_parts)+"</div>",
                    unsafe_allow_html=True)
    st.markdown("---")

    # ── Main Tabs ─────────────────────────────────────────────────────────────
    tabs = st.tabs(["📊 Dashboard","🔍 Market Scan","🌍 Global Markets","🔬 Analysis","🤖 AI Chat","📝 Paper Trade","📈 Backtest"])

    # ════════════════════════════════════════════════════════════════════════
    # TAB 1 — DASHBOARD
    # ════════════════════════════════════════════════════════════════════════
    with tabs[0]:
        df = _candles(symbol)
        if df is None or df.empty:
            st.markdown('<div class="card"><h3 style="color:#ff3366">⚠ No Data Available</h3>'
                        '<p style="color:#8899aa">Market may be closed. Data refreshes during market hours (9:15–15:30 IST).</p></div>',
                        unsafe_allow_html=True)
            st.stop()

        ta   = bot["ta"].full_analysis(df)
        sig  = bot["eng"].generate_signal(df, symbol)
        prob = bot["prob"].quick_probability(df, symbol)
        exp  = bot["ea"].expiry_volatility_pattern(symbol.replace("50",""))

        price   = ta.get("price",0)
        rsi_v   = ta.get("rsi",50)
        atr_v   = ta.get("atr",0)
        trend_v = ta.get("trend","—")
        sig_type= sig.get("signal","WAIT")
        p       = prob.get("probability",50)

        # ── KPI Strip ──────────────────────────────────────────────────────
        k = st.columns(7)
        def _kpi(col,label,val,sub="",color="#e8f0fe"):
            col.markdown(f'<div class="card" style="text-align:center;padding:10px">'
                         f'<div class="kpi-label">{label}</div>'
                         f'<div class="kpi-num" style="color:{color}">{val}</div>'
                         f'<div style="color:#8899aa;font-size:0.78em">{sub}</div></div>',
                         unsafe_allow_html=True)
        rsi_col = "#00ff88" if rsi_v<30 else "#ff3366" if rsi_v>70 else "#e8f0fe"
        trend_col= "#00ff88" if "UP" in trend_v else "#ff3366" if "DOWN" in trend_v else "#ffd700"
        sig_col = "#00ff88" if sig_type=="BUY" else "#ff3366" if sig_type=="SELL" else "#ffd700"
        _kpi(k[0],"PRICE",f"{price:,.2f}",f"ATR {atr_v:.1f}")
        _kpi(k[1],"RSI (14)",f"{rsi_v:.1f}","Oversold" if rsi_v<30 else "Overbought" if rsi_v>70 else "Neutral",rsi_col)
        _kpi(k[2],"VWAP",f"{ta.get('vwap',0):,.2f}","Above" if ta.get("above_vwap") else "Below")
        _kpi(k[3],"TREND",trend_v.replace("_"," "),ta.get("structure",""),trend_col)
        _kpi(k[4],"BB POS",f"{ta.get('bb_position_pct',0):.0f}%","Lower→Bullish")
        _kpi(k[5],"PROBABILITY",f"{p:.0f}%","Entry chances",("#00ff88" if p>=65 else "#ffd700" if p>=50 else "#ff3366"))
        _kpi(k[6],"SIGNAL",sig_type,sig.get("quality",""),sig_col)

        st.markdown("")
        # ── Chart + Signal ──────────────────────────────────────────────────
        ch,sp = st.columns([3,1])
        with ch:
            try:
                st.plotly_chart(_chart(df.tail(100),symbol,bot["ta"]),
                                use_container_width=True,key="main_chart")
            except Exception as e:
                st.error(f"Chart error: {e}")

        with sp:
            # Signal card
            border = {"BUY":"card-green","SELL":"card-red","WAIT":"card-blue"}.get(sig_type,"card-blue")
            st.markdown(f'<div class="{border}" style="text-align:center">',unsafe_allow_html=True)
            st.markdown(f'<div class="sig-{sig_type}">{sig_type}</div>',unsafe_allow_html=True)
            st.markdown(f'<div style="color:#8899aa;font-size:0.8em">{sig.get("quality","")} SIGNAL</div>',unsafe_allow_html=True)
            st.markdown('</div>',unsafe_allow_html=True)

            st.markdown("")
            # Probability meter
            st.markdown(f'<div class="card" style="text-align:center">'
                        f'<div class="kpi-label">ENTRY PROBABILITY</div>'
                        f'{_prob_bar(p)}'
                        f'<div style="color:#8899aa;font-size:0.78em;margin-top:4px">'
                        f'Buy {prob.get("buy_probability",0):.0f}% &nbsp;|&nbsp; Sell {prob.get("sell_probability",0):.0f}%</div>'
                        f'<div style="color:#2196f3;font-weight:700;font-size:0.9em;margin-top:4px">'
                        f'{prob.get("recommendation","WAIT")}</div></div>',unsafe_allow_html=True)

            st.markdown("")
            # Levels card
            entry  = sig.get("entry",0)
            sl     = sig.get("stop_loss",0)
            targets= sig.get("targets",[])
            rr     = sig.get("risk_reward",0)
            if entry:
                rr_color = "#00ff88" if rr>=1.5 else "#ffd700" if rr>=1 else "#ff3366"
                lvl_html = f'<div class="card"><div class="kpi-label">TRADE LEVELS</div>'
                lvl_html += f'<div style="margin:6px 0"><span style="color:#8899aa">Entry</span>&nbsp;&nbsp;<b style="font-family:monospace;color:#e8f0fe">{entry:,.2f}</b></div>'
                if sl:
                    lvl_html += f'<div style="margin:4px 0"><span style="color:#8899aa">Stop Loss</span>&nbsp;<b style="font-family:monospace;color:#ff3366">{sl:,.2f}</b> <span style="color:#ff3366;font-size:0.8em">({abs(entry-sl):.1f} pts)</span></div>'
                for i,t in enumerate(targets,1):
                    c="#00ff88" if i==1 else "#ffd700" if i==2 else "#ff9800"
                    lvl_html += f'<div style="margin:4px 0"><span style="color:#8899aa">Target {i}</span>&nbsp;<b style="font-family:monospace;color:{c}">{t:,.2f}</b> <span style="color:{c};font-size:0.8em">(+{abs(t-entry):.1f} pts)</span></div>'
                lvl_html += f'<div style="margin-top:8px;border-top:1px solid #1e3a5f;padding-top:6px"><span style="color:#8899aa">R:R</span>&nbsp;<b style="color:{rr_color}">{rr}</b></div></div>'
                st.markdown(lvl_html,unsafe_allow_html=True)

            # Expiry info
            if exp.get("is_expiry"):
                st.markdown('<div class="card-red" style="text-align:center;padding:8px">'
                            '<b style="color:#ff3366">🔥 EXPIRY DAY</b><br>'
                            f'<span style="color:#8899aa;font-size:0.8em">{exp.get("recommended_targets","")}</span></div>',
                            unsafe_allow_html=True)
            else:
                dte=exp.get("dte",0)
                st.markdown(f'<div class="card" style="text-align:center;padding:8px">'
                            f'<span style="color:#8899aa;font-size:0.8em">Expiry: {exp.get("expiry_date","")} | DTE: {dte}</span><br>'
                            f'<span style="color:#ffd700;font-size:0.8em">{exp.get("recommended_targets","")}</span></div>',
                            unsafe_allow_html=True)

        # Warnings
        for w in sig.get("time_warnings",[]):
            st.warning(w)

        # S&R + Conditions
        st.markdown("")
        sc1,sc2,sc3 = st.columns(3)
        with sc1:
            sr_html='<div class="card"><div class="kpi-label">RESISTANCE LEVELS</div>'
            for r in ta.get("resistance",[])[:3]:
                sr_html+=f'<div style="color:#ff3366;font-family:monospace;padding:3px 0">🔴 {r:,.2f}</div>'
            sr_html+='</div>'
            st.markdown(sr_html,unsafe_allow_html=True)
        with sc2:
            sr_html='<div class="card"><div class="kpi-label">SUPPORT LEVELS</div>'
            for s in ta.get("support",[])[:3]:
                sr_html+=f'<div style="color:#00ff88;font-family:monospace;padding:3px 0">🟢 {s:,.2f}</div>'
            sr_html+='</div>'
            st.markdown(sr_html,unsafe_allow_html=True)
        with sc3:
            cond=sig.get("conditions_met",[])
            c_html='<div class="card"><div class="kpi-label">CONDITIONS MET</div>'
            for c in cond: c_html+=f'<div style="color:#00ff88;font-size:0.85em;padding:2px 0">✓ {c.replace("_"," ").title()}</div>'
            if not cond: c_html+='<div style="color:#8899aa;font-size:0.85em">No clear signal conditions</div>'
            c_html+='</div>'
            st.markdown(c_html,unsafe_allow_html=True)

        # Market scan
        with st.expander("🔍 Market Scan — All Instruments"):
            rows=[]
            for sym in bot["syms"]:
                df2=_candles(sym)
                if df2 is not None and len(df2)>=30:
                    s=bot["eng"].generate_signal(df2,sym)
                    ta2=s.get("ta",{})
                    rows.append({"Symbol":sym,"Signal":s.get("signal","WAIT"),
                                 "Quality":s.get("quality",""),"Entry":s.get("entry",""),
                                 "T1":s.get("targets",[""])[0] if s.get("targets") else "",
                                 "SL":s.get("stop_loss",""),"R/R":s.get("risk_reward",""),
                                 "RSI":round(ta2.get("rsi",0),1),"Trend":ta2.get("trend","")})
            if rows:
                st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True)

    # ════════════════════════════════════════════════════════════════════════
    # TAB 2 — MARKET SCANNER
    # ════════════════════════════════════════════════════════════════════════
    with tabs[1]:
        st.markdown("## 🔍 NSE Market Scanner")
        st.markdown('<div style="color:#8899aa;font-size:0.85rem;margin-bottom:1rem">'
                    'Scans 100+ NSE stocks in one click — finds top gainers, losers, volume spikes, and best trade opportunities.</div>',
                    unsafe_allow_html=True)

        sc1, sc2, sc3 = st.columns([2, 2, 3])
        with sc1:
            scan_universe = st.selectbox("Universe", [
                ("Nifty 50 (~48 stocks, fast)", "nifty50"),
                ("Nifty 100 (100 stocks)", "nifty100"),
                ("Full NSE (~110 stocks)", "all"),
            ], format_func=lambda x: x[0], index=1)[1]
        with sc2:
            scan_sort = st.selectbox("Show by", [
                "Best Opportunities", "Top Gainers", "Top Losers",
                "Volume Spikes", "Sharp Moves",
            ])
        with sc3:
            run_scan = st.button("🔍  SCAN NSE MARKET NOW", type="primary", use_container_width=True)

        if "scan_result" not in st.session_state:
            st.session_state.scan_result = None
        if "scan_time" not in st.session_state:
            st.session_state.scan_time = None

        if run_scan:
            progress_placeholder = st.empty()
            with st.spinner("Scanning NSE market… (15-30 seconds)"):
                from analysis.market_scanner import scan_market
                def _prog(msg):
                    progress_placeholder.info(f"⏳ {msg}")
                result = scan_market(universe=scan_universe, progress_cb=_prog)
            progress_placeholder.empty()
            st.session_state.scan_result = result
            st.session_state.scan_time   = datetime.now().strftime("%H:%M:%S")

        scan = st.session_state.scan_result
        if scan and "error" not in scan:
            meta = scan["meta"]

            # ── Market Breadth ────────────────────────────────────────────────
            mb = st.columns(5)
            mb[0].metric("Stocks Scanned",  meta["scanned"])
            mb[1].metric("Advancing ▲",     meta["advancing"],
                         delta=f'+{meta["advancing"]}', delta_color="normal")
            mb[2].metric("Declining ▼",     meta["declining"],
                         delta=f'-{meta["declining"]}', delta_color="inverse")
            mb[3].metric("A/D Ratio",
                         f"{meta['advancing']/max(meta['declining'],1):.2f}",
                         "Bullish" if meta["advancing"] > meta["declining"] else "Bearish")
            mb[4].metric("Scan Time",       meta["scan_time"])

            # Market mood
            a = meta["advancing"]; d = meta["declining"]
            mood_pct = a / (a + d) * 100 if (a + d) > 0 else 50
            if mood_pct >= 65:
                st.success(f"📈 Market Breadth: **BULLISH** — {a} stocks rising vs {d} falling ({mood_pct:.0f}% advancing)")
            elif mood_pct <= 35:
                st.error(f"📉 Market Breadth: **BEARISH** — {d} stocks falling vs {a} rising ({100-mood_pct:.0f}% declining)")
            else:
                st.warning(f"↔ Market Breadth: **MIXED** — {a} rising, {d} falling")

            st.divider()

            # ── Main Table based on selected sort ─────────────────────────────
            sort_map = {
                "Best Opportunities": "opportunities",
                "Top Gainers":        "gainers",
                "Top Losers":         "losers",
                "Volume Spikes":      "volume_leaders",
                "Sharp Moves":        "sharp_moves",
            }
            key = sort_map.get(scan_sort, "opportunities")
            df_show = scan.get(key, scan["all"])

            # Display columns
            display_cols = ["Symbol", "Name", "Price", "Change%", "Change",
                            "Vol Ratio", "ATR%", "Mom5m%", "Signal", "Opp Score"]
            df_disp = df_show[[c for c in display_cols if c in df_show.columns]]

            def _style_row(row):
                styles = [""] * len(row)
                chg_idx = list(row.index).index("Change%") if "Change%" in row.index else -1
                if chg_idx >= 0:
                    if row["Change%"] >= 2:
                        styles[chg_idx] = "color:#00ff88;font-weight:700"
                    elif row["Change%"] <= -2:
                        styles[chg_idx] = "color:#ff3366;font-weight:700"
                return styles

            st.dataframe(
                df_disp.style.apply(_style_row, axis=1),
                use_container_width=True, hide_index=True,
                column_config={
                    "Change%":  st.column_config.NumberColumn("Chg%",  format="%.2f%%"),
                    "Change":   st.column_config.NumberColumn("Chg ₹", format="%.2f"),
                    "Price":    st.column_config.NumberColumn("Price ₹",format="%.2f"),
                    "Vol Ratio":st.column_config.NumberColumn("Vol Ratio", format="%.2fx"),
                    "ATR%":     st.column_config.NumberColumn("ATR%",   format="%.2f%%"),
                    "Mom5m%":   st.column_config.NumberColumn("5m Mom%",format="%.3f%%"),
                    "Opp Score":st.column_config.ProgressColumn("Opportunity", min_value=0, max_value=100),
                },
            )

            # ── Four-panel summary ────────────────────────────────────────────
            st.divider()
            p1, p2, p3, p4 = st.columns(4)

            def _mini_table(col, title, df_panel, color):
                rows_html = ""
                for _, r in df_panel.head(5).iterrows():
                    chg = r.get("Change%", 0)
                    arrow = "▲" if chg >= 0 else "▼"
                    c = "#00ff88" if chg >= 0 else "#ff3366"
                    rows_html += (f'<div style="display:flex;justify-content:space-between;'
                                  f'padding:3px 0;border-bottom:1px solid #1e3a5f">'
                                  f'<span style="font-weight:700">{r["Symbol"]}</span>'
                                  f'<span style="color:{c}">{arrow}{abs(chg):.2f}%</span>'
                                  f'</div>')
                col.markdown(f'<div class="card" style="border-color:{color}">'
                             f'<div style="color:{color};font-weight:700;font-size:0.8rem;margin-bottom:0.5rem">{title}</div>'
                             f'{rows_html}</div>', unsafe_allow_html=True)

            _mini_table(p1, "📈 TOP GAINERS",     scan["gainers"],         "#00ff88")
            _mini_table(p2, "📉 TOP LOSERS",       scan["losers"],          "#ff3366")
            _mini_table(p3, "🔥 VOLUME SPIKES",    scan["volume_leaders"],  "#2196f3")
            _mini_table(p4, "⚡ BEST TRADES",      scan["opportunities"],   "#ffd700")

            # ── Click to analyze ──────────────────────────────────────────────
            st.divider()
            all_syms = scan["all"]["Symbol"].tolist()
            tracked  = [s for s in all_syms if s in bot["syms"]]
            untracked = [s for s in all_syms if s not in bot["syms"]]

            st.markdown("#### 🎯 Quick Analysis of Top Opportunity")
            top_pick = scan["opportunities"].iloc[0] if not scan["opportunities"].empty else None
            if top_pick is not None:
                tp_sym = top_pick["Symbol"]
                st.markdown(
                    f'<div class="card-blue"><b style="font-size:1.1rem">{tp_sym}</b> '
                    f'<span style="color:{("#00ff88" if top_pick["Change%"]>=0 else "#ff3366")}">'
                    f'{top_pick["Change%"]:+.2f}%</span> | '
                    f'Vol Ratio: {top_pick["Vol Ratio"]:.2f}x | '
                    f'Signal: {top_pick.get("Signal","")}</div>',
                    unsafe_allow_html=True,
                )
                if tp_sym in bot["syms"]:
                    df_tp = _candles(tp_sym)
                    if df_tp is not None and not df_tp.empty:
                        ta_tp  = bot["ta"].full_analysis(df_tp)
                        sig_tp = bot["eng"].generate_signal(df_tp, tp_sym)
                        prob_tp = bot["prob"].quick_probability(df_tp, tp_sym)
                        cc = st.columns(4)
                        cc[0].metric("Signal",    sig_tp.get("signal","WAIT"))
                        cc[1].metric("Prob",      f"{prob_tp.get('probability',50):.0f}%")
                        cc[2].metric("Entry",     f"₹{sig_tp.get('entry',0):,.2f}" if sig_tp.get('entry') else "–")
                        cc[3].metric("Stop Loss", f"₹{sig_tp.get('stop_loss',0):,.2f}" if sig_tp.get('stop_loss') else "–")
                else:
                    st.info(f"{tp_sym} is not in your tracked instruments. "
                            f"Add it to `config.py` INSTRUMENTS for deep analysis.")

        elif scan and "error" in scan:
            st.error(f"Scan failed: {scan['error']}")
            st.info("Market may be closed. Try scanning during 9:15 AM – 3:30 PM IST.")
        else:
            st.markdown("""
<div style="text-align:center;padding:3rem;color:#8899aa">
  <div style="font-size:3rem">🔍</div>
  <div style="font-size:1.1rem;margin-top:0.5rem">Click <b style="color:#2196f3">SCAN NSE MARKET NOW</b> to analyse the entire market</div>
  <div style="font-size:0.85rem;margin-top:0.5rem">Finds stocks with highest movement, volume, and trade potential in one click</div>
</div>""", unsafe_allow_html=True)

    # ════════════════════════════════════════════════════════════════════════
    # TAB 3 — GLOBAL MARKETS
    # ════════════════════════════════════════════════════════════════════════
    with tabs[2]:
        st.markdown('<div style="color:#8899aa;font-size:0.85em;margin-bottom:12px">*GIFT Nifty: NSE IFSC data not available on yfinance — showing Nifty 50 spot as proxy. For live GIFT Nifty, use NSE/GIFT City portal.</div>',unsafe_allow_html=True)

        # India markets
        st.markdown("#### 🇮🇳 India Markets")
        india = [("Nifty 50","^NSEI"),("Bank Nifty","^NSEBANK"),("Sensex","^BSESN"),("India VIX","^VIX")]
        ic = st.columns(4)
        for (name,ticker),col in zip(india,ic):
            price,chg,pct=_global_quote(ticker)
            color="#00ff88" if chg>=0 else "#ff3366"
            arrow="▲" if chg>=0 else "▼"
            col.markdown(f'<div class="card" style="text-align:center">'
                        f'<div class="kpi-label">{name}</div>'
                        f'<div class="kpi-num">{price:,.1f}</div>'
                        f'<div style="color:{color}">{arrow} {abs(pct):.2f}%</div></div>',
                        unsafe_allow_html=True)

        st.markdown("#### 🌏 Asia Pacific")
        asia=[("Nikkei 225","^N225"),("Hang Seng","^HSI"),("Shanghai","000001.SS"),("KOSPI","^KS11")]
        ac=st.columns(4)
        for (name,ticker),col in zip(asia,ac):
            price,chg,pct=_global_quote(ticker)
            color="#00ff88" if chg>=0 else "#ff3366"
            col.markdown(f'<div class="card" style="text-align:center">'
                        f'<div class="kpi-label">{name}</div>'
                        f'<div class="kpi-num">{price:,.1f}</div>'
                        f'<div style="color:{color}">{"▲" if chg>=0 else "▼"} {abs(pct):.2f}%</div></div>',unsafe_allow_html=True)

        st.markdown("#### 🇺🇸 US Markets")
        us=[("S&P 500","^GSPC"),("Dow Jones","^DJI"),("NASDAQ","^IXIC"),("US VIX","^VIX")]
        uc=st.columns(4)
        for (name,ticker),col in zip(us,uc):
            price,chg,pct=_global_quote(ticker)
            color="#00ff88" if chg>=0 else "#ff3366"
            col.markdown(f'<div class="card" style="text-align:center">'
                        f'<div class="kpi-label">{name}</div>'
                        f'<div class="kpi-num">{price:,.1f}</div>'
                        f'<div style="color:{color}">{"▲" if chg>=0 else "▼"} {abs(pct):.2f}%</div></div>',unsafe_allow_html=True)

        st.markdown("#### 🛢️ Commodities & Forex")
        commod=[("Gold","GC=F","$/oz"),("Silver","SI=F","$/oz"),("Crude Oil","CL=F","$/bbl"),
                ("Nat Gas","NG=F","$/MMBtu"),("USD/INR","USDINR=X","₹"),("EUR/USD","EURUSD=X",""),
                ("Copper","HG=F","$/lb"),("Bitcoin","BTC-USD","$")]
        cc=st.columns(4)
        for i,(name,ticker,unit) in enumerate(commod):
            col=cc[i%4]
            price,chg,pct=_global_quote(ticker)
            color="#00ff88" if chg>=0 else "#ff3366"
            col.markdown(f'<div class="card" style="text-align:center">'
                        f'<div class="kpi-label">{name}</div>'
                        f'<div class="kpi-num">{price:,.2f}<span style="color:#8899aa;font-size:0.5em"> {unit}</span></div>'
                        f'<div style="color:{color}">{"▲" if chg>=0 else "▼"} {abs(pct):.2f}%</div></div>',unsafe_allow_html=True)

        # Market breadth for trade decisions
        st.markdown("#### 📊 Market Breadth Interpretation")
        sp_p,sp_c,_=_global_quote("^GSPC")
        vix_p,_,__=_global_quote("^VIX")
        usdinr_p,usdinr_c,_=_global_quote("USDINR=X")
        gold_p,gold_c,_=_global_quote("GC=F")
        crude_p,crude_c,_=_global_quote("CL=F")

        signals_global=[]
        if sp_c>0: signals_global.append("🟢 US markets positive → Nifty likely bullish open")
        else: signals_global.append("🔴 US markets negative → Nifty likely bearish open")
        if vix_p<15: signals_global.append("🟢 VIX low (<15) → Low fear, good for options buying")
        elif vix_p>20: signals_global.append("🔴 VIX high (>20) → High fear, avoid naked options")
        if usdinr_c>0: signals_global.append("🔴 USD/INR rising → FII outflow risk, bearish for Nifty")
        else: signals_global.append("🟢 USD/INR falling → FII inflow likely, bullish for Nifty")
        if gold_c>0: signals_global.append("🟡 Gold rising → Risk-off sentiment, caution")
        if crude_c>0: signals_global.append("🔴 Crude rising → Inflation concern, watch for downside")

        for sig_g in signals_global:
            st.markdown(f'<div class="card" style="padding:8px 14px">{sig_g}</div>',unsafe_allow_html=True)

    # ════════════════════════════════════════════════════════════════════════
    # TAB 4 — DEEP ANALYSIS
    # ════════════════════════════════════════════════════════════════════════
    with tabs[3]:
        df=_candles(symbol)
        if df is None: st.error("No data"); st.stop()
        ta   = bot["ta"].full_analysis(df)
        vold = bot["va"].full_analysis(df)
        volm = bot["vola"].full_analysis(df)
        st.markdown(f'<h3 style="color:#2196f3">🔬 {symbol} — Deep Analysis</h3>',unsafe_allow_html=True)
        a1,a2=st.columns(2)
        with a1:
            st.markdown('<div class="kpi-label" style="margin-bottom:8px">TECHNICAL INDICATORS</div>',unsafe_allow_html=True)
            indicators=[
                ("RSI (14)",ta.get("rsi",""),ta.get("rsi_signal","")),
                ("MACD",ta.get("macd",""),ta.get("macd_signal_str","")),
                ("BB Upper",ta.get("bb_upper",""),""),
                ("BB Lower",ta.get("bb_lower",""),""),
                ("BB Width",f"{ta.get('bb_squeeze_pct',0):.2f}%","Squeeze" if ta.get('bb_squeeze_pct',100)<2 else ""),
                ("VWAP",ta.get("vwap",""),"Above" if ta.get("above_vwap") else "Below"),
                ("ATR",ta.get("atr",""),""),
                ("EMA 9",ta.get("ema9",""),""),
                ("EMA 21",ta.get("ema21",""),""),
                ("EMA 50",ta.get("ema50",""),""),
            ]
            for ind,val,sig2 in indicators:
                sig_color="#00ff88" if any(x in str(sig2) for x in ["BULL","UP","Above","Oversold"]) else "#ff3366" if any(x in str(sig2) for x in ["BEAR","DOWN","Below","Over"]) else "#8899aa"
                st.markdown(f'<div style="display:flex;justify-content:space-between;padding:5px 0;border-bottom:1px solid #1e3a5f">'
                           f'<span style="color:#8899aa">{ind}</span>'
                           f'<span style="font-family:monospace;color:#e8f0fe">{val}</span>'
                           f'<span style="color:{sig_color};font-size:0.85em">{sig2}</span></div>',unsafe_allow_html=True)

        with a2:
            st.markdown('<div class="kpi-label" style="margin-bottom:8px">VOLATILITY & VOLUME</div>',unsafe_allow_html=True)
            vol_rows=[
                ("HV 5-day",f"{vold.get('hv_5day',0)}%"),
                ("HV 20-day",f"{vold.get('hv_20day',0)}%"),
                ("Vol Regime",vold.get("vol_regime","")),
                ("ATR Target ↑1",str(vold.get("t1_up",""))),
                ("ATR Target ↑2",str(vold.get("t2_up",""))),
                ("ATR Target ↓1",str(vold.get("t1_dn",""))),
                ("VWAP",str(volm.get("vwap",""))),
                ("Relative Vol",str(volm.get("relative_volume",""))),
                ("Vol Signal",volm.get("volume_signal","")),
                ("Momentum",f"{volm.get('roc_pct',0):.3f}%"),
                ("Divergence",volm.get("divergence","")),
            ]
            for label,val in vol_rows:
                st.markdown(f'<div style="display:flex;justify-content:space-between;padding:5px 0;border-bottom:1px solid #1e3a5f">'
                           f'<span style="color:#8899aa">{label}</span>'
                           f'<span style="font-family:monospace;color:#e8f0fe">{val}</span></div>',unsafe_allow_html=True)

        # Probability factor chart
        st.markdown("")
        prob=bot["prob"].quick_probability(df,symbol)
        factors=prob.get("factor_breakdown",{})
        if factors:
            import plotly.graph_objects as go
            names=[k.replace("_score","").replace("_"," ").title() for k in factors]
            vals=list(factors.values())
            colors=["#00ff88" if v>=60 else "#ffd700" if v>=45 else "#ff3366" for v in vals]
            fig2=go.Figure(go.Bar(x=vals,y=names,orientation="h",
                marker_color=colors,text=[f"{v:.0f}%" for v in vals],textposition="outside"))
            fig2.add_vline(x=50,line_dash="dot",line_color="#8899aa",opacity=0.5)
            fig2.update_layout(template="plotly_dark",paper_bgcolor="#0a0e1a",
                plot_bgcolor="#0f1629",height=240,margin=dict(l=120,r=60,t=20,b=10),
                xaxis=dict(range=[0,110],showgrid=True,gridcolor="#1e3a5f"),
                yaxis=dict(showgrid=False),font=dict(color="#8899aa"),
                title=dict(text="Probability Factor Breakdown",font=dict(color="#e8f0fe",size=14)))
            st.plotly_chart(fig2,use_container_width=True,key="factors")

    # ════════════════════════════════════════════════════════════════════════
    # TAB 5 — CLAUDE AI CHAT
    # ════════════════════════════════════════════════════════════════════════
    with tabs[4]:
        st.markdown('<h3 style="color:#2196f3">🤖 Claude AI — Trading Intelligence</h3>',unsafe_allow_html=True)
        if "hist" not in st.session_state: st.session_state.hist=[]
        df=_candles(symbol)
        ctx="No data"
        if df is not None and not df.empty:
            ta=bot["ta"].full_analysis(df)
            sig=bot["eng"].generate_signal(df,symbol)
            pr=bot["prob"].quick_probability(df,symbol)
            ex=bot["ea"].expiry_volatility_pattern(symbol.replace("50",""))
            ctx=(f"Symbol:{symbol} | Price:{ta.get('price')} | RSI:{ta.get('rsi')} ({ta.get('rsi_signal')}) | "
                 f"MACD:{ta.get('macd_signal_str')} | Trend:{ta.get('trend')}/{ta.get('structure')} | "
                 f"VWAP:{ta.get('vwap')} ({'above' if ta.get('above_vwap') else 'below'}) | ATR:{ta.get('atr')} | "
                 f"BB:{ta.get('bb_lower')}–{ta.get('bb_upper')} | Support:{ta.get('support')} | Resistance:{ta.get('resistance')} | "
                 f"Signal:{sig.get('signal')} | Entry:{sig.get('entry')} | SL:{sig.get('stop_loss')} | Targets:{sig.get('targets')} | "
                 f"Prob:{pr.get('probability')}% | Rec:{pr.get('recommendation')} | "
                 f"Expiry:{ex.get('expiry_date')} DTE:{ex.get('dte')} {'EXPIRY DAY' if ex.get('is_expiry') else ''}")
            # Append NSE scan summary if available
            if st.session_state.get("scan_result") and "error" not in st.session_state.scan_result:
                try:
                    from analysis.market_scanner import get_nse_summary
                    ctx += "\n" + get_nse_summary(st.session_state.scan_result)
                except Exception:
                    pass

        # Quick query buttons
        qs=[f"Should I take {symbol} {'call' if 'NIFTY' in symbol else 'buy'} now?",
            f"NIFTY call at 24100 — good entry?",
            f"What is probability of {symbol} moving 50 points?",
            f"Best scalping strategy for current {symbol} setup?"]
        qc=st.columns(4)
        for col,q in zip(qc,qs):
            if col.button(q[:24]+"…",use_container_width=True,key="q"+q[:6]):
                with st.spinner("Claude analysing…"):
                    ans=_claude(q,ctx)
                st.session_state.hist+=[{"r":"u","t":q},{"r":"b","t":ans}]
                st.rerun()
        st.markdown("---")
        for m in st.session_state.hist:
            tag="chat-u" if m["r"]=="u" else "chat-b"
            who="👤 You" if m["r"]=="u" else "🤖 Claude"
            st.markdown(f'<div class="{tag}"><b style="color:#2196f3">{who}:</b><br>{m["t"]}</div>',unsafe_allow_html=True)
        with st.form("cf",clear_on_submit=True):
            qi=st.text_input("",placeholder="Ask: Should I take NIFTY call at 24100?  |  SBIN mein entry leni chahiye?")
            cs,cc=st.columns([4,1])
            if cs.form_submit_button("Ask Claude 🤖",type="primary",use_container_width=True) and qi:
                with st.spinner("Analysing…"):
                    ans=_claude(qi,ctx)
                st.session_state.hist+=[{"r":"u","t":qi},{"r":"b","t":ans}]
                st.rerun()
            if cc.form_submit_button("Clear",use_container_width=True):
                st.session_state.hist=[];st.rerun()
        with st.expander("📋 Market context sent to Claude"):
            st.code(ctx)

    # ════════════════════════════════════════════════════════════════════════
    # TAB 6 — PAPER TRADING
    # ════════════════════════════════════════════════════════════════════════
    with tabs[5]:
        st.markdown('<h3 style="color:#2196f3">📝 Paper Trading</h3>',unsafe_allow_html=True)
        port=bot["paper"].get_portfolio()
        mx=port.get("metrics",{})
        pnl=port.get("realized_pnl",0)
        pnl_color="#00ff88" if pnl>=0 else "#ff3366"
        mc=st.columns(6)
        def _mcard(col,lbl,val,color="#e8f0fe"):
            col.markdown(f'<div class="card" style="text-align:center">'
                        f'<div class="kpi-label">{lbl}</div>'
                        f'<div class="kpi-num" style="color:{color}">{val}</div></div>',unsafe_allow_html=True)
        _mcard(mc[0],"CAPITAL",f"₹{port.get('capital',0):,.0f}")
        _mcard(mc[1],"P&L",f"₹{pnl:+,.2f}",pnl_color)
        _mcard(mc[2],"OPEN",str(port.get("open_positions",0)))
        _mcard(mc[3],"TRADES",str(mx.get("total_trades",0)))
        _mcard(mc[4],"WIN RATE",f"{mx.get('win_rate',0):.1f}%","#00ff88" if mx.get('win_rate',0)>50 else "#ff3366")
        _mcard(mc[5],"MAX DD",f"₹{mx.get('max_drawdown',0):,.0f}","#ff3366")
        st.markdown("---")
        pf1,pf2=st.columns([1,2])
        with pf1:
            st.markdown('<div class="kpi-label">NEW TRADE</div>',unsafe_allow_html=True)
            with st.form("nt"):
                pt_sym=st.selectbox("Symbol",bot["syms"])
                pt_type=st.radio("Type",["BUY","SELL"],horizontal=True)
                lv=_ltp(pt_sym)
                pt_px=st.number_input("Entry Price",value=float(lv or 0),min_value=0.0,step=0.05)
                pt_qty=st.number_input("Quantity",min_value=1,value=1,step=1)
                c1,c2=st.columns(2)
                pt_opt=c1.selectbox("Option",["None","CE","PE"])
                pt_str=c2.number_input("Strike",min_value=0.0,step=50.0)
                if st.form_submit_button("Enter Trade ✅",type="primary",use_container_width=True):
                    if pt_px>0:
                        tr=bot["paper"].enter_trade(pt_sym,pt_type,pt_px,pt_qty,
                                None if pt_opt=="None" else pt_opt,pt_str if pt_str>0 else None)
                        st.success(f"Trade #{tr['id']} entered!")
                        st.rerun()
        with pf2:
            open_t=port.get("open_trades",[])
            if open_t:
                st.markdown('<div class="kpi-label">OPEN POSITIONS</div>',unsafe_allow_html=True)
                for tr in open_t:
                    t_color="#00ff88" if tr.get("trade_type")=="BUY" else "#ff3366"
                    st.markdown(f'<div class="card"><b style="color:{t_color}">{tr.get("trade_type")}</b> '
                               f'{tr.get("symbol")} @ <b style="font-family:monospace">{tr.get("entry_price")}</b> × {tr.get("quantity")}</div>',
                               unsafe_allow_html=True)
                    with st.form(f"ex{tr['id']}"):
                        lv2=_ltp(tr.get("symbol",""))
                        ep=st.number_input("Exit Price",value=float(lv2 or 0),min_value=0.0,step=0.05,key=f"e{tr['id']}")
                        if st.form_submit_button("Exit 🔴",use_container_width=True):
                            if ep>0:
                                res=bot["paper"].exit_trade(tr["id"],ep)
                                pv=res.get("pnl",0) or 0
                                (st.success if pv>=0 else st.error)(f"P&L: ₹{pv:+.2f}")
                                st.rerun()
            else:
                st.markdown('<div class="card" style="text-align:center;color:#8899aa">No open positions</div>',unsafe_allow_html=True)
        cl=port.get("closed_trades",[])
        if cl:
            st.markdown('<div class="kpi-label" style="margin-top:12px">TRADE HISTORY</div>',unsafe_allow_html=True)
            hdf=pd.DataFrame(cl)[["symbol","trade_type","entry_time","entry_price","exit_price","quantity","pnl"]]
            hdf.columns=["Symbol","Type","Time","Entry","Exit","Qty","P&L"]
            st.dataframe(hdf,use_container_width=True,hide_index=True)

    # ════════════════════════════════════════════════════════════════════════
    # TAB 7 — BACKTEST
    # ════════════════════════════════════════════════════════════════════════
    with tabs[6]:
        st.markdown('<h3 style="color:#2196f3">📈 Strategy Backtest</h3>',unsafe_allow_html=True)
        bc1,bc2=st.columns([1,3])
        with bc1:
            bt_sym=st.selectbox("Symbol",bot["syms"],key="btsym")
            st.caption("Last 5 days × 5-min candles")
            run_bt=st.button("▶ Run Backtest",type="primary",use_container_width=True)
        if run_bt:
            df_bt=_candles(bt_sym)
            if df_bt is not None:
                with st.spinner("Running…"):
                    res=bot["paper"].backtest_strategy({bt_sym:df_bt},bot["eng"].generate_signal)
                with bc2:
                    bm=st.columns(5)
                    bm[0].metric("Trades",res.get("total_trades",0))
                    bm[1].metric("Win Rate",f"{res.get('win_rate',0):.1f}%")
                    bm[2].metric("P&L",f"{res.get('total_pnl',0):+.2f}")
                    bm[3].metric("Max DD",f"{res.get('max_drawdown',0):.2f}")
                    bm[4].metric("Avg/Trade",f"{res.get('avg_pnl_per_trade',0):.2f}")
                eq=res.get("equity_curve",[0])
                if len(eq)>1:
                    import plotly.graph_objects as go
                    pos=eq[-1]>=0
                    ef=go.Figure(go.Scatter(y=eq,mode="lines",
                        line=dict(color="#00ff88" if pos else "#ff3366",width=2),
                        fill="tozeroy",fillcolor="rgba(0,255,136,.08)" if pos else "rgba(255,51,102,.08)"))
                    ef.update_layout(template="plotly_dark",paper_bgcolor="#0a0e1a",
                        plot_bgcolor="#0f1629",height=280,title=dict(text="Equity Curve",font=dict(color="#e8f0fe")),
                        margin=dict(l=40,r=20,t=40,b=20),
                        xaxis=dict(showgrid=True,gridcolor="#1e3a5f"),
                        yaxis=dict(showgrid=True,gridcolor="#1e3a5f"))
                    st.plotly_chart(ef,use_container_width=True,key="eq")
                if res.get("trades"):
                    st.dataframe(pd.DataFrame(res["trades"]),use_container_width=True,hide_index=True)
            else:
                st.error("No data for backtest")


if __name__=="__main__":
    main()
