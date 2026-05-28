"""
Scalper Bot — Professional Trading Terminal
Run: streamlit run streamlit_app.py
"""
import os
from datetime import datetime
from typing import Dict, Optional

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(
    page_title="Scalper Bot | Trading Terminal",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Trading Terminal CSS ───────────────────────────────────────────────────────
st.markdown("""<style>
/* === BASE === */
html,body,[data-testid="stAppViewContainer"]{
  background:#0a0e1a!important;color:#e8f0fe;font-family:'Segoe UI',monospace}
[data-testid="stSidebar"]{background:#0f1629!important;border-right:1px solid #1e3a5f}
[data-testid="stHeader"]{background:transparent!important;display:none}
.block-container{padding:0.5rem 1rem 1rem!important;max-width:100%!important}
footer{display:none!important}
/* === TABS === */
[data-testid="stTabs"] button{
  background:#0f1629;color:#8899aa;border:1px solid #1e3a5f;border-radius:6px 6px 0 0;
  font-weight:600;font-size:0.82rem;padding:0.4rem 0.9rem}
[data-testid="stTabs"] button[aria-selected="true"]{
  background:#1e3a5f;color:#e8f0fe;border-bottom:2px solid #2196f3}
[data-testid="stTabPanel"]{background:#0a0e1a;padding:0.5rem 0}
/* === METRICS === */
[data-testid="stMetric"]{
  background:#0f1629;border:1px solid #1e3a5f;border-radius:8px;padding:0.6rem 0.8rem}
[data-testid="stMetricLabel"]{color:#8899aa!important;font-size:0.72rem!important}
[data-testid="stMetricValue"]{color:#e8f0fe!important;font-size:1.1rem!important;font-weight:700}
[data-testid="stMetricDelta"]{font-size:0.75rem!important}
/* === CARDS === */
.card{background:#0f1629;border:1px solid #1e3a5f;border-radius:10px;padding:1rem;margin:0.3rem 0}
.card-buy{border:2px solid #00ff88;box-shadow:0 0 18px rgba(0,255,136,0.3)}
.card-sell{border:2px solid #ff3366;box-shadow:0 0 18px rgba(255,51,102,0.3)}
.card-wait{border:2px solid #ffd700;box-shadow:0 0 18px rgba(255,215,0,0.2)}
/* === SIGNAL === */
.sig-BUY{color:#00ff88;font-size:2.4em;font-weight:900;letter-spacing:2px}
.sig-SELL{color:#ff3366;font-size:2.4em;font-weight:900;letter-spacing:2px}
.sig-WAIT{color:#ffd700;font-size:2.4em;font-weight:900;letter-spacing:2px}
/* === PROB METER === */
.prob-bar{font-family:monospace;font-size:1.1em;letter-spacing:1px}
.prob-hi{color:#00ff88}.prob-md{color:#ffd700}.prob-lo{color:#ff3366}
/* === TICKER === */
.ticker-wrap{background:#0f1629;border-bottom:1px solid #1e3a5f;
  padding:0.4rem 1rem;overflow-x:auto;white-space:nowrap;margin:-0.5rem -1rem 0.8rem}
.ticker-item{display:inline-block;margin-right:2rem;font-size:0.78rem}
.ticker-lbl{color:#8899aa;margin-right:0.3rem}
.ticker-val{color:#e8f0fe;font-weight:700;margin-right:0.2rem}
.ticker-up{color:#00ff88}.ticker-dn{color:#ff3366}.ticker-neu{color:#8899aa}
/* === CHAT === */
.chat-u{background:#0f1629;border:1px solid #1e3a5f;border-radius:8px;padding:10px;margin:4px 0}
.chat-b{background:#0a1929;border-left:3px solid #2196f3;border-radius:8px;padding:10px;margin:4px 0}
/* === LEVEL ROW === */
.lvl-row{display:flex;justify-content:space-between;align-items:center;
  padding:0.35rem 0;border-bottom:1px solid #1e3a5f}
.lvl-lbl{color:#8899aa;font-size:0.78rem;min-width:50px}
.lvl-val{color:#e8f0fe;font-weight:700;font-size:0.95rem}
.lvl-pts-up{color:#00ff88;font-size:0.72rem}
.lvl-pts-dn{color:#ff3366;font-size:0.72rem}
/* === SECTION HEADER === */
.sec-hdr{color:#2196f3;font-size:0.7rem;font-weight:700;letter-spacing:2px;
  text-transform:uppercase;margin:0.8rem 0 0.4rem;border-bottom:1px solid #1e3a5f;padding-bottom:0.3rem}
/* === STATUS === */
.status-live{background:#003322;border:1px solid #00ff88;color:#00ff88;
  border-radius:4px;padding:2px 8px;font-size:0.72rem;font-weight:700}
.status-yf{background:#1a1500;border:1px solid #ffd700;color:#ffd700;
  border-radius:4px;padding:2px 8px;font-size:0.72rem;font-weight:700}
.status-closed{background:#1a0010;border:1px solid #ff3366;color:#ff3366;
  border-radius:4px;padding:2px 8px;font-size:0.72rem;font-weight:700}
/* === GLOBAL INDEX CARD === */
.gi-card{background:#0f1629;border:1px solid #1e3a5f;border-radius:8px;
  padding:0.7rem;text-align:center;min-width:100px}
.gi-name{color:#8899aa;font-size:0.65rem;font-weight:700;letter-spacing:1px}
.gi-val{color:#e8f0fe;font-size:1.05rem;font-weight:700;margin:0.2rem 0}
.gi-chg-up{color:#00ff88;font-size:0.75rem}
.gi-chg-dn{color:#ff3366;font-size:0.75rem}
/* === CONDITION BADGES === */
.cond-met{color:#00ff88;font-size:0.8rem}
.cond-not{color:#8899aa;font-size:0.8rem;text-decoration:line-through}
/* === SELECT BOX === */
[data-testid="stSelectbox"] > div{background:#0f1629;border:1px solid #1e3a5f;border-radius:6px}
[data-testid="stButton"] button{
  background:#1e3a5f;color:#e8f0fe;border:1px solid #2196f3;border-radius:6px;
  font-weight:600;transition:all 0.2s}
[data-testid="stButton"] button:hover{background:#2196f3;color:#fff}
</style>""", unsafe_allow_html=True)

# ── Constants ──────────────────────────────────────────────────────────────────
GLOBAL_TICKERS = {
    "GIFT NIFTY*": "^NSEI",
    "DOW":         "^DJI",
    "S&P 500":     "^GSPC",
    "NASDAQ":      "^IXIC",
    "NIKKEI":      "^N225",
    "HANG SENG":   "^HSI",
    "GOLD":        "GC=F",
    "CRUDE OIL":   "CL=F",
    "VIX":         "^VIX",
    "USD/INR":     "USDINR=X",
}

# ── Helpers ────────────────────────────────────────────────────────────────────
def _anthr_key() -> str:
    k = os.getenv("ANTHROPIC_API_KEY", "")
    if k:
        return k
    try:
        return st.secrets.get("ANTHROPIC_API_KEY", "")
    except Exception:
        return ""


@st.cache_resource(show_spinner="Initialising trading engine…")
def _init():
    from analysis.technical    import TechnicalAnalysis
    from analysis.volatility   import VolatilityAnalysis
    from analysis.volume       import VolumeAnalysis
    from analysis.expiry       import ExpiryAnalysis
    from trading.probability   import ProbabilityCalculator
    from trading.scalping      import ScalpingEngine
    from trading.paper_trading import PaperTradingDashboard
    from database.db_manager   import DatabaseManager
    from config                import INSTRUMENTS
    from api.data_fetcher      import _login
    _login()
    db = DatabaseManager()
    return dict(
        ta=TechnicalAnalysis(), va=VolatilityAnalysis(),
        vola=VolumeAnalysis(),  ea=ExpiryAnalysis(),
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
        return None


@st.cache_data(ttl=30, show_spinner=False)
def _ltp(symbol: str) -> Optional[float]:
    try:
        from api.data_fetcher import get_ltp
        return get_ltp(symbol)
    except Exception:
        return None


@st.cache_data(ttl=120, show_spinner=False)
def _global_indices() -> Dict[str, dict]:
    """Fetch all global index data at once to minimise yfinance calls."""
    try:
        import yfinance as yf
        tickers = list(GLOBAL_TICKERS.values())
        raw = yf.download(tickers, period="2d", interval="1d",
                          group_by="ticker", auto_adjust=True, progress=False)
        result = {}
        for name, sym in GLOBAL_TICKERS.items():
            try:
                if len(tickers) > 1:
                    df = raw[sym] if sym in raw.columns.get_level_values(0) else pd.DataFrame()
                else:
                    df = raw
                if df is None or df.empty or len(df) < 1:
                    result[name] = {}
                    continue
                last  = float(df["Close"].iloc[-1])
                prev  = float(df["Close"].iloc[-2]) if len(df) >= 2 else last
                chg   = last - prev
                pct   = (chg / prev * 100) if prev else 0
                result[name] = {"price": last, "change": chg, "pct": pct, "sym": sym}
            except Exception:
                result[name] = {}
        return result
    except Exception:
        return {}


def _fmt_price(v: float, sym: str) -> str:
    if "USDINR" in sym:
        return f"{v:.2f}"
    if v > 10000:
        return f"{v:,.0f}"
    if v > 100:
        return f"{v:,.2f}"
    return f"{v:.2f}"


def _prob_bar(p: float) -> str:
    filled = int(p / 5)
    empty  = 20 - filled
    cls    = "prob-hi" if p >= 65 else "prob-md" if p >= 50 else "prob-lo"
    bar    = "█" * filled + "░" * empty
    return f'<span class="{cls} prob-bar">[{bar}] {p:.0f}%</span>'


def _is_market_open() -> bool:
    try:
        from utils.helpers import is_market_hours
        return is_market_hours()
    except Exception:
        now = datetime.now()
        return now.weekday() < 5 and (
            (9, 15) <= (now.hour, now.minute) <= (15, 30)
        )


def _chart(df: pd.DataFrame, symbol: str, ta) -> "go.Figure":
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True,
                        vertical_spacing=0.02, row_heights=[0.60, 0.20, 0.20])
    # Candles
    fig.add_trace(go.Candlestick(
        x=df.index, open=df.open, high=df.high, low=df.low, close=df.close,
        name=symbol, increasing_line_color="#00ff88", decreasing_line_color="#ff3366",
        increasing_fillcolor="#00ff88", decreasing_fillcolor="#ff3366"), row=1, col=1)
    # Bollinger Bands
    bb_u, bb_m, bb_l = ta.bollinger_bands(df.close)
    fig.add_trace(go.Scatter(x=df.index, y=bb_u, line=dict(color="rgba(33,150,243,0.35)", width=1),
        showlegend=False, name="BB Upper"), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=bb_l, line=dict(color="rgba(33,150,243,0.35)", width=1),
        fill="tonexty", fillcolor="rgba(33,150,243,0.05)", showlegend=False, name="BB Lower"), row=1, col=1)
    # EMAs
    fig.add_trace(go.Scatter(x=df.index, y=ta.ema(df.close, 9),
        line=dict(color="#ffd700", width=1.2), name="EMA9"), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=ta.ema(df.close, 21),
        line=dict(color="#ff9800", width=1.2), name="EMA21"), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=ta.vwap(df),
        line=dict(color="#e040fb", width=1.5, dash="dot"), name="VWAP"), row=1, col=1)
    # Volume
    vc = ["#00ff88" if c >= o else "#ff3366" for c, o in zip(df.close, df.open)]
    fig.add_trace(go.Bar(x=df.index, y=df.volume, marker_color=vc,
        opacity=0.25, name="Vol", showlegend=False), row=1, col=1)
    # RSI
    rsi = ta.rsi(df.close)
    fig.add_trace(go.Scatter(x=df.index, y=rsi,
        line=dict(color="#2196f3", width=1.5), name="RSI"), row=2, col=1)
    for y, c in [(70, "#ff3366"), (30, "#00ff88"), (50, "rgba(255,255,255,0.2)")]:
        fig.add_hline(y=y, line_dash="dot", line_color=c, opacity=0.5, row=2, col=1)
    # MACD
    ml, sl, hist = ta.macd(df.close)
    hc = ["#00ff88" if v >= 0 else "#ff3366" for v in hist]
    fig.add_trace(go.Bar(x=df.index, y=hist, marker_color=hc, opacity=0.6,
        name="Hist", showlegend=False), row=3, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=ml, line=dict(color="#2196f3", width=1.5), name="MACD"),   row=3, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=sl, line=dict(color="#ff9800", width=1.5), name="Signal"), row=3, col=1)
    fig.add_hline(y=0, line_dash="dot", line_color="rgba(255,255,255,0.15)", row=3, col=1)

    fig.update_layout(
        template="plotly_dark", paper_bgcolor="#0a0e1a", plot_bgcolor="#0f1629",
        xaxis_rangeslider_visible=False, height=560,
        margin=dict(l=40, r=10, t=10, b=20),
        legend=dict(orientation="h", y=1.02, x=0, bgcolor="rgba(0,0,0,0)",
                    font=dict(size=10, color="#8899aa")),
        font=dict(color="#8899aa"),
    )
    fig.update_xaxes(showgrid=True, gridcolor="#1e3a5f", zeroline=False)
    fig.update_yaxes(showgrid=True, gridcolor="#1e3a5f", zeroline=False)
    return fig


def _claude(query: str, ctx: str) -> str:
    key = _anthr_key()
    if not key:
        return "⚠️ ANTHROPIC_API_KEY not set. Add it to `.env` or Streamlit Secrets."
    try:
        import anthropic
        r = anthropic.Anthropic(api_key=key).messages.create(
            model="claude-sonnet-4-6", max_tokens=800,
            system=(
                "You are an expert NSE/BSE intraday scalper and technical analyst. "
                "Answer concisely with: probability%, entry zone, target(s), stop-loss, R/R ratio, "
                "risk warnings. Indian market context. Use ₹ for prices. Max 300 words."
            ),
            messages=[{"role": "user", "content": f"Live market data:\n{ctx}\n\nQuery: {query}"}],
        )
        return r.content[0].text
    except Exception as e:
        return f"Claude error: {e}"


# ══════════════════════════════════════════════════════════════════════════════
def main():
    bot = _init()

    # ── TOP HEADER BAR ─────────────────────────────────────────────────────────
    h1, h2, h3, h4 = st.columns([3, 2, 2, 1])
    with h1:
        st.markdown("## 📈 Scalper Bot")
    with h2:
        now = datetime.now()
        st.markdown(f"<div style='color:#8899aa;font-size:0.8rem;padding-top:0.6rem'>"
                    f"🕐 {now.strftime('%d %b %Y  %H:%M:%S')} IST</div>", unsafe_allow_html=True)
    with h3:
        from api.data_fetcher import get_data_source
        src = get_data_source()
        if src == "AngelOne":
            st.markdown('<span class="status-live">🟢 ANGELONE LIVE</span>', unsafe_allow_html=True)
        else:
            st.markdown('<span class="status-yf">🟡 YFINANCE NSE</span>', unsafe_allow_html=True)
        if _is_market_open():
            st.markdown('<span class="status-live" style="margin-left:6px">MARKET OPEN</span>', unsafe_allow_html=True)
        else:
            st.markdown('<span class="status-closed" style="margin-left:6px">MARKET CLOSED</span>', unsafe_allow_html=True)
    with h4:
        symbol = st.selectbox("", bot["syms"], index=0, label_visibility="collapsed")

    # ── GLOBAL INDICES TICKER STRIP ────────────────────────────────────────────
    gi = _global_indices()
    ticker_html = '<div class="ticker-wrap">'
    for name, d in gi.items():
        if not d:
            continue
        price = _fmt_price(d["price"], d.get("sym", ""))
        pct   = d.get("pct", 0)
        chg   = d.get("change", 0)
        arrow = "▲" if pct >= 0 else "▼"
        cls   = "ticker-up" if pct >= 0 else "ticker-dn"
        ticker_html += (
            f'<span class="ticker-item">'
            f'<span class="ticker-lbl">{name}</span>'
            f'<span class="ticker-val">{price}</span>'
            f'<span class="{cls}">{arrow}{abs(pct):.2f}%</span>'
            f'</span>'
        )
    ticker_html += "</div>"
    st.markdown(ticker_html, unsafe_allow_html=True)

    # ── SIDEBAR ────────────────────────────────────────────────────────────────
    with st.sidebar:
        st.markdown("## ⚙️ Controls")
        if st.button("🔄 Refresh All", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
        st.caption("⚠️ Educational use only. Not financial advice.")

    # ── TABS ───────────────────────────────────────────────────────────────────
    tabs = st.tabs(["📊 Dashboard", "🌍 Global Markets", "🔬 Deep Analysis", "🤖 AI Chat", "📝 Paper Trade", "📈 Backtest"])

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 1 — DASHBOARD
    # ══════════════════════════════════════════════════════════════════════════
    with tabs[0]:
        df = _data(symbol)
        if df is None or df.empty:
            st.error(f"No data for **{symbol}**. Market may be closed or data unavailable.")
            st.info("Market hours: Mon–Fri  9:15 AM – 3:30 PM IST")
            st.stop()

        ta   = bot["ta"].full_analysis(df)
        sig  = bot["eng"].generate_signal(df, symbol)
        prob = bot["prob"].quick_probability(df, symbol)
        exp  = bot["ea"].expiry_volatility_pattern(symbol.replace("50", ""))

        p_val   = prob.get("probability", 50)
        signal  = sig.get("signal", "WAIT")
        entry   = sig.get("entry") or 0
        sl      = sig.get("stop_loss") or 0
        targets = sig.get("targets") or []

        # ── KPI STRIP ─────────────────────────────────────────────────────────
        k = st.columns(7)
        ltp_val = ta.get("price", 0)
        k[0].metric("💰 LTP",       f"₹{ltp_val:,.2f}",  f"ATR {ta.get('atr', 0):.1f}")
        rsi_v = ta.get("rsi", 50)
        k[1].metric("📊 RSI",       f"{rsi_v:.1f}",
                    "Oversold" if rsi_v < 30 else "Overbought" if rsi_v > 70 else "Neutral")
        vwap_v = ta.get("vwap", 0)
        k[2].metric("〰 VWAP",      f"₹{vwap_v:,.2f}",
                    "▲ Above" if ta.get("above_vwap") else "▼ Below")
        k[3].metric("📈 Trend",     ta.get("trend", "—"),   ta.get("structure", ""))
        k[4].metric("🎯 Prob",      f"{p_val:.0f}%",
                    "BUY bias" if prob.get("buy_probability", 0) > prob.get("sell_probability", 0) else "SELL bias")
        k[5].metric("⚡ Signal",    signal,                  sig.get("quality", ""))
        bb_pct = ta.get("bb_position_pct", 50)
        k[6].metric("📉 BB Pos",   f"{bb_pct:.0f}%",
                    "Near Top" if bb_pct > 80 else "Near Bot" if bb_pct < 20 else "Mid")
        st.divider()

        # ── MAIN GRID: CHART + SIGNAL PANEL ───────────────────────────────────
        col_chart, col_sig = st.columns([3, 1])

        with col_chart:
            st.plotly_chart(_chart(df.tail(120), symbol, bot["ta"]),
                            use_container_width=True, key="chart_main")
            # Conditions met
            conditions = sig.get("conditions", [])
            if conditions:
                st.markdown('<div class="sec-hdr">Conditions</div>', unsafe_allow_html=True)
                cc = st.columns(min(len(conditions), 3))
                for i, c in enumerate(conditions):
                    with cc[i % 3]:
                        st.markdown(f'<span class="cond-met">✓ {c}</span>', unsafe_allow_html=True)

        with col_sig:
            card_cls = f"card card-{signal.lower()}"
            # Signal card with glow
            st.markdown(f"""
<div class="{card_cls}">
  <div style="color:#8899aa;font-size:0.65rem;font-weight:700;letter-spacing:2px">SIGNAL</div>
  <div class="sig-{signal}">{signal}</div>
  <div style="color:#8899aa;font-size:0.8rem;margin-top:0.3rem">{sig.get('quality','')}</div>
</div>""", unsafe_allow_html=True)

            # Probability meter
            st.markdown(f"""
<div class="card" style="margin-top:0.5rem">
  <div style="color:#8899aa;font-size:0.65rem;font-weight:700;letter-spacing:2px;margin-bottom:0.4rem">PROBABILITY</div>
  {_prob_bar(p_val)}
  <div style="margin-top:0.4rem;font-size:0.75rem">
    <span class="prob-hi">▲ {prob.get('buy_probability', 0):.0f}%</span>
    <span style="color:#8899aa;margin:0 0.5rem">|</span>
    <span class="prob-lo">▼ {prob.get('sell_probability', 0):.0f}%</span>
  </div>
  <div style="color:#8899aa;font-size:0.72rem;margin-top:0.3rem">{prob.get('recommendation','')}</div>
</div>""", unsafe_allow_html=True)

            # Trade levels
            if entry:
                sl_pts  = abs(entry - sl)
                tgt_html = ""
                for i, t in enumerate(targets, 1):
                    pts   = abs(t - entry)
                    arrow = "▲" if t > entry else "▼"
                    cls   = "lvl-pts-up" if t > entry else "lvl-pts-dn"
                    tgt_html += (
                        f'<div class="lvl-row">'
                        f'<span class="lvl-lbl">T{i}</span>'
                        f'<span class="lvl-val">₹{t:,.2f}</span>'
                        f'<span class="{cls}">{arrow}{pts:.1f}pts</span>'
                        f'</div>'
                    )
                rr = sig.get("risk_reward", 0)
                rr_color = "#00ff88" if rr >= 2 else "#ffd700" if rr >= 1.5 else "#ff3366"
                st.markdown(f"""
<div class="card" style="margin-top:0.5rem">
  <div style="color:#8899aa;font-size:0.65rem;font-weight:700;letter-spacing:2px;margin-bottom:0.4rem">TRADE LEVELS</div>
  <div class="lvl-row">
    <span class="lvl-lbl">Entry</span>
    <span class="lvl-val">₹{entry:,.2f}</span>
    <span class="lvl-pts-up"></span>
  </div>
  <div class="lvl-row">
    <span class="lvl-lbl">SL</span>
    <span class="lvl-val" style="color:#ff3366">₹{sl:,.2f}</span>
    <span class="lvl-pts-dn">▼{sl_pts:.1f}pts</span>
  </div>
  {tgt_html}
  <div style="margin-top:0.5rem;font-size:0.78rem">
    R/R: <span style="color:{rr_color};font-weight:700">{rr}:1</span>
  </div>
</div>""", unsafe_allow_html=True)
            else:
                st.markdown('<div class="card" style="color:#8899aa;text-align:center;padding:1.5rem">'
                            'No active signal<br><small>Wait for setup</small></div>', unsafe_allow_html=True)

            # Support / Resistance
            supports    = ta.get("support", [])
            resistances = ta.get("resistance", [])
            sr_html = '<div class="card" style="margin-top:0.5rem"><div class="sec-hdr">S/R LEVELS</div>'
            for r in resistances[:3]:
                sr_html += f'<div class="lvl-row"><span class="lvl-lbl">R</span><span style="color:#ff3366;font-weight:700">₹{r:,.2f}</span></div>'
            for s in supports[:3]:
                sr_html += f'<div class="lvl-row"><span class="lvl-lbl">S</span><span style="color:#00ff88;font-weight:700">₹{s:,.2f}</span></div>'
            sr_html += "</div>"
            st.markdown(sr_html, unsafe_allow_html=True)

            # Expiry info
            if exp.get("is_expiry"):
                st.markdown(
                    '<div class="card card-sell" style="text-align:center;margin-top:0.5rem">'
                    '<span style="color:#ff3366;font-size:0.85rem;font-weight:700">🔥 EXPIRY DAY</span><br>'
                    f'<span style="color:#8899aa;font-size:0.72rem">Targets {exp.get("target_multiplier",1)}x</span>'
                    '</div>', unsafe_allow_html=True)
            else:
                dte = exp.get("dte", "?")
                st.markdown(
                    f'<div class="card" style="text-align:center;margin-top:0.5rem">'
                    f'<span style="color:#8899aa;font-size:0.72rem">DTE: <span style="color:#ffd700">{dte}</span> days</span><br>'
                    f'<span style="color:#8899aa;font-size:0.68rem">{exp.get("recommended_targets","")}</span>'
                    '</div>', unsafe_allow_html=True)

        # ── Time warnings ──────────────────────────────────────────────────────
        for w in sig.get("time_warnings", []):
            st.warning(w)

        # ── Market Scan ────────────────────────────────────────────────────────
        with st.expander("🔍 Market Scan — All Instruments"):
            rows = []
            for sym in bot["syms"]:
                df2 = _data(sym)
                if df2 is not None and len(df2) >= 30:
                    s    = bot["eng"].generate_signal(df2, sym)
                    ta2  = s.get("ta", {})
                    rows.append({
                        "Symbol":  sym,
                        "Signal":  s.get("signal", "WAIT"),
                        "Quality": s.get("quality", ""),
                        "Entry":   f"₹{s.get('entry', 0):,.2f}" if s.get("entry") else "–",
                        "T1":      f"₹{s['targets'][0]:,.2f}" if s.get("targets") else "–",
                        "SL":      f"₹{s.get('stop_loss', 0):,.2f}" if s.get("stop_loss") else "–",
                        "R/R":     s.get("risk_reward", ""),
                        "RSI":     round(ta2.get("rsi", 0), 1),
                        "Trend":   ta2.get("trend", ""),
                    })
            if rows:
                st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 2 — GLOBAL MARKETS
    # ══════════════════════════════════════════════════════════════════════════
    with tabs[1]:
        st.markdown("## 🌍 Global Markets")
        gi = _global_indices()

        sections = {
            "🇮🇳 India / Asia": ["GIFT NIFTY*", "NIKKEI", "HANG SENG"],
            "🇺🇸 US Markets":    ["DOW", "S&P 500", "NASDAQ"],
            "🛢️ Commodities":    ["GOLD", "CRUDE OIL", "VIX", "USD/INR"],
        }

        for sec_name, keys in sections.items():
            st.markdown(f'<div class="sec-hdr">{sec_name}</div>', unsafe_allow_html=True)
            cols = st.columns(len(keys))
            for col, k in zip(cols, keys):
                d = gi.get(k, {})
                with col:
                    if d:
                        pct   = d.get("pct", 0)
                        chg   = d.get("change", 0)
                        price = _fmt_price(d["price"], d.get("sym", ""))
                        arrow = "▲" if pct >= 0 else "▼"
                        chg_cls = "gi-chg-up" if pct >= 0 else "gi-chg-dn"
                        st.markdown(f"""
<div class="gi-card">
  <div class="gi-name">{k}</div>
  <div class="gi-val">{price}</div>
  <div class="{chg_cls}">{arrow} {abs(chg):.2f} ({abs(pct):.2f}%)</div>
</div>""", unsafe_allow_html=True)
                    else:
                        st.markdown(f'<div class="gi-card"><div class="gi-name">{k}</div>'
                                    '<div style="color:#8899aa">N/A</div></div>', unsafe_allow_html=True)

        # Market breadth interpretation
        st.divider()
        st.markdown("### 📊 Market Breadth Interpretation")
        up_count = sum(1 for d in gi.values() if d and d.get("pct", 0) > 0)
        dn_count = sum(1 for d in gi.values() if d and d.get("pct", 0) < 0)
        vix_d    = gi.get("VIX", {})
        vix_val  = vix_d.get("price", 0) if vix_d else 0
        dow_d    = gi.get("DOW", {})
        dow_pct  = dow_d.get("pct", 0) if dow_d else 0
        gold_d   = gi.get("GOLD", {})
        gold_pct = gold_d.get("pct", 0) if gold_d else 0

        b1, b2, b3 = st.columns(3)
        b1.metric("Markets Rising", f"{up_count}/{len(gi)} indices", f"{up_count-dn_count:+d} net")
        b2.metric("VIX (Fear Index)", f"{vix_val:.2f}" if vix_val else "N/A",
                  "High Fear" if vix_val > 25 else "Normal" if vix_val > 15 else "Low Fear")
        b3.metric("US Market Mood", f"DOW {dow_pct:+.2f}%",
                  "Risk-On" if dow_pct > 0.5 else "Risk-Off" if dow_pct < -0.5 else "Neutral")

        # Interpretation text
        interp = []
        if up_count >= len(gi) * 0.7:
            interp.append("🟢 Strong global risk-on: Most markets advancing → Bullish NSE open")
        elif dn_count >= len(gi) * 0.7:
            interp.append("🔴 Strong global risk-off: Most markets declining → Bearish NSE open")
        else:
            interp.append("🟡 Mixed global cues: No clear directional bias")

        if vix_val > 25:
            interp.append("⚠️ VIX elevated (>25): High volatility expected — widen SL, reduce size")
        elif vix_val < 15:
            interp.append("✅ VIX low (<15): Low volatility — tight scalping setups work well")

        if gold_pct > 0.5:
            interp.append("🪙 Gold rising: Flight to safety — avoid aggressive longs")
        if abs(dow_pct) > 1:
            interp.append(f"🇺🇸 Strong US move ({dow_pct:+.2f}%): Gap up/down likely at NSE open")

        note_html = '<div class="card" style="margin-top:1rem">'
        for line in interp:
            note_html += f'<div style="margin:0.3rem 0;font-size:0.85rem">{line}</div>'
        note_html += "<div style='color:#8899aa;font-size:0.68rem;margin-top:0.6rem'>*GIFT NIFTY uses NSE spot as proxy — actual GIFT Nifty futures not available via free API</div>"
        note_html += "</div>"
        st.markdown(note_html, unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 3 — DEEP ANALYSIS
    # ══════════════════════════════════════════════════════════════════════════
    with tabs[2]:
        df = _data(symbol)
        if df is None or df.empty:
            st.warning("No data available")
            st.stop()

        ta_d  = bot["ta"].full_analysis(df)
        vold  = bot["va"].full_analysis(df)
        volm  = bot["vola"].full_analysis(df)
        prob  = bot["prob"].quick_probability(df, symbol)

        st.markdown(f"## 🔬 Deep Analysis — {symbol}")

        a1, a2 = st.columns(2)
        with a1:
            st.markdown('<div class="sec-hdr">Technical Indicators</div>', unsafe_allow_html=True)
            st.dataframe(pd.DataFrame([
                {"Indicator": "RSI (14)",     "Value": f"{ta_d.get('rsi', 0):.2f}",      "Signal": ta_d.get("rsi_signal", "")},
                {"Indicator": "MACD",         "Value": f"{ta_d.get('macd', 0):.4f}",     "Signal": ta_d.get("macd_signal_str", "")},
                {"Indicator": "BB Upper",     "Value": f"₹{ta_d.get('bb_upper', 0):,.2f}","Signal": ""},
                {"Indicator": "BB Middle",    "Value": f"₹{ta_d.get('bb_middle', 0):,.2f}","Signal": ""},
                {"Indicator": "BB Lower",     "Value": f"₹{ta_d.get('bb_lower', 0):,.2f}","Signal": ""},
                {"Indicator": "BB Position",  "Value": f"{ta_d.get('bb_position_pct', 0):.1f}%","Signal": ""},
                {"Indicator": "VWAP",         "Value": f"₹{ta_d.get('vwap', 0):,.2f}",   "Signal": "Above" if ta_d.get("above_vwap") else "Below"},
                {"Indicator": "ATR (14)",     "Value": f"{ta_d.get('atr', 0):.2f}",      "Signal": ""},
                {"Indicator": "Trend",        "Value": ta_d.get("trend", ""),             "Signal": ta_d.get("structure", "")},
                {"Indicator": "EMA 9",        "Value": f"₹{ta_d.get('ema9', 0):,.2f}",   "Signal": ""},
                {"Indicator": "EMA 21",       "Value": f"₹{ta_d.get('ema21', 0):,.2f}",  "Signal": ""},
                {"Indicator": "EMA 50",       "Value": f"₹{ta_d.get('ema50', 0):,.2f}",  "Signal": ""},
            ]), use_container_width=True, hide_index=True)

        with a2:
            st.markdown('<div class="sec-hdr">Volatility</div>', unsafe_allow_html=True)
            st.dataframe(pd.DataFrame([
                {"Metric": "HV 5-day",       "Value": f"{vold.get('hv_5day', 0):.2f}%"},
                {"Metric": "HV 20-day",      "Value": f"{vold.get('hv_20day', 0):.2f}%"},
                {"Metric": "HV 50-day",      "Value": f"{vold.get('hv_50day', 0):.2f}%"},
                {"Metric": "Vol Regime",     "Value": vold.get("vol_regime", "")},
                {"Metric": "ATR T1 ↑",       "Value": f"₹{vold.get('t1_up', 0):,.2f}" if vold.get('t1_up') else "–"},
                {"Metric": "ATR T2 ↑",       "Value": f"₹{vold.get('t2_up', 0):,.2f}" if vold.get('t2_up') else "–"},
                {"Metric": "ATR T1 ↓",       "Value": f"₹{vold.get('t1_dn', 0):,.2f}" if vold.get('t1_dn') else "–"},
                {"Metric": "Intraday Bias",  "Value": vold.get("intraday_bias", "")},
            ]), use_container_width=True, hide_index=True)

            st.markdown('<div class="sec-hdr" style="margin-top:0.8rem">Volume & Momentum</div>', unsafe_allow_html=True)
            vp = volm.get("volume_profile", {})
            st.dataframe(pd.DataFrame([
                {"Metric": "VWAP",            "Value": f"₹{volm.get('vwap', 0):,.2f}" if volm.get('vwap') else "–"},
                {"Metric": "Rel. Volume",     "Value": f"{volm.get('relative_volume', 0):.2f}x" if volm.get('relative_volume') else "–"},
                {"Metric": "Volume Signal",   "Value": volm.get("volume_signal", "")},
                {"Metric": "Momentum %",      "Value": f"{volm.get('roc_pct', 0):.3f}%" if volm.get('roc_pct') is not None else "–"},
                {"Metric": "Mom Signal",      "Value": volm.get("momentum_signal", "")},
                {"Metric": "Divergence",      "Value": volm.get("divergence", "")},
                {"Metric": "POC",             "Value": f"₹{vp.get('poc', 0):,.2f}" if isinstance(vp, dict) and vp.get("poc") else "–"},
            ]), use_container_width=True, hide_index=True)

        # Factor breakdown chart
        factors = prob.get("factor_breakdown", {})
        if factors:
            import plotly.graph_objects as go
            fig2 = go.Figure(go.Bar(
                x=list(factors.values()),
                y=[k.replace("_score", "").replace("_", " ").title() for k in factors],
                orientation="h",
                marker_color=[
                    "#00ff88" if v >= 65 else "#ffd700" if v >= 45 else "#ff3366"
                    for v in factors.values()
                ],
                text=[f"{v:.0f}%" for v in factors.values()],
                textposition="outside",
            ))
            fig2.update_layout(
                template="plotly_dark", paper_bgcolor="#0a0e1a", plot_bgcolor="#0f1629",
                height=260, margin=dict(l=130, r=60, t=20, b=10),
                xaxis=dict(range=[0, 115], gridcolor="#1e3a5f"),
                yaxis=dict(gridcolor="#1e3a5f"),
                title=dict(text="Probability Factor Breakdown", font=dict(color="#8899aa", size=12)),
            )
            fig2.add_vline(x=50, line_dash="dot", line_color="rgba(255,255,255,0.2)")
            st.plotly_chart(fig2, use_container_width=True, key="factors")

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 4 — AI CHAT
    # ══════════════════════════════════════════════════════════════════════════
    with tabs[3]:
        st.markdown("## 🤖 Claude AI Trading Assistant")
        if "hist" not in st.session_state:
            st.session_state.hist = []

        df  = _data(symbol)
        ctx = "No market data"
        if df is not None and not df.empty:
            ta_d = bot["ta"].full_analysis(df)
            sig  = bot["eng"].generate_signal(df, symbol)
            pr   = bot["prob"].quick_probability(df, symbol)
            ex   = bot["ea"].expiry_volatility_pattern(symbol.replace("50", ""))
            gi   = _global_indices()
            nifty_d = gi.get("GIFT NIFTY*", {})
            dow_d   = gi.get("DOW", {})
            ctx = (
                f"=== {symbol} @ {datetime.now().strftime('%H:%M')} ===\n"
                f"Price:{ta_d.get('price')} RSI:{ta_d.get('rsi'):.1f} "
                f"MACD:{ta_d.get('macd_signal_str')} Trend:{ta_d.get('trend')}/{ta_d.get('structure')}\n"
                f"VWAP:{ta_d.get('vwap')} ATR:{ta_d.get('atr'):.1f} "
                f"BB_pos:{ta_d.get('bb_position_pct'):.0f}%\n"
                f"Support:{ta_d.get('support')} Resistance:{ta_d.get('resistance')}\n"
                f"Signal:{sig.get('signal')} Quality:{sig.get('quality')} "
                f"Entry:{sig.get('entry')} SL:{sig.get('stop_loss')} "
                f"Targets:{sig.get('targets')} R/R:{sig.get('risk_reward')}\n"
                f"Probability:{pr.get('probability')}% "
                f"Buy:{pr.get('buy_probability')}% Sell:{pr.get('sell_probability')}%\n"
                f"DTE:{ex.get('dte')} ExpDate:{ex.get('expiry_date')} "
                f"{'EXPIRY DAY ' if ex.get('is_expiry') else ''}"
                f"TargetMult:{ex.get('target_multiplier')}x\n"
                f"=== Global ===\n"
                f"Nifty_spot:{nifty_d.get('price', 'N/A')} ({nifty_d.get('pct', 0):+.2f}%) "
                f"DOW:{dow_d.get('pct', 0):+.2f}%"
            )

        # Quick question buttons
        quick = [
            f"Should I buy {symbol} now?",
            f"NIFTY call at 24100 — good entry?",
            f"What's the risk for {symbol} trade?",
            f"Best strategy for expiry day?",
        ]
        qc = st.columns(4)
        for col, q in zip(qc, quick):
            if col.button(q[:25] + ("…" if len(q) > 25 else ""), use_container_width=True, key="qb_" + q[:8]):
                with st.spinner("Claude thinking…"):
                    ans = _claude(q, ctx)
                st.session_state.hist += [{"r": "u", "t": q}, {"r": "b", "t": ans}]
                st.rerun()

        st.divider()
        for m in st.session_state.hist:
            tag = "chat-u" if m["r"] == "u" else "chat-b"
            who = "👤 You" if m["r"] == "u" else "🤖 Claude"
            st.markdown(f'<div class="{tag}"><b>{who}:</b><br>{m["t"]}</div>', unsafe_allow_html=True)

        with st.form("cf", clear_on_submit=True):
            qi = st.text_input("Ask about any trade…",
                               placeholder="e.g. 24100 CE looks good? SBIN se kab nikalna chahiye?")
            cs, cc = st.columns([4, 1])
            sub = cs.form_submit_button("Ask Claude 🤖", type="primary", use_container_width=True)
            clr = cc.form_submit_button("Clear", use_container_width=True)

        if sub and qi:
            with st.spinner("Analysing…"):
                ans = _claude(qi, ctx)
            st.session_state.hist += [{"r": "u", "t": qi}, {"r": "b", "t": ans}]
            st.rerun()
        if clr:
            st.session_state.hist = []
            st.rerun()

        with st.expander("📋 Live market context sent to Claude"):
            st.code(ctx)

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 5 — PAPER TRADING
    # ══════════════════════════════════════════════════════════════════════════
    with tabs[4]:
        st.markdown("## 📝 Paper Trading Dashboard")
        port = bot["paper"].get_portfolio()
        mx   = port.get("metrics", {})
        pnl  = port.get("realized_pnl", 0)

        mc = st.columns(6)
        mc[0].metric("Capital",       f"₹{port.get('capital', 0):,.0f}")
        mc[1].metric("Realized P&L",  f"₹{pnl:+,.2f}", delta_color="normal")
        mc[2].metric("Open Pos",      port.get("open_positions", 0))
        mc[3].metric("Total Trades",  mx.get("total_trades", 0))
        mc[4].metric("Win Rate",      f"{mx.get('win_rate', 0):.1f}%")
        mc[5].metric("Max Drawdown",  f"₹{mx.get('max_drawdown', 0):,.0f}", delta_color="inverse")
        st.divider()

        pf1, pf2 = st.columns([1, 2])
        with pf1:
            st.markdown("#### ➕ New Trade")
            with st.form("nt"):
                pt_sym  = st.selectbox("Symbol", bot["syms"])
                pt_type = st.radio("Type", ["BUY", "SELL"], horizontal=True)
                ltp_v   = _ltp(pt_sym)
                pt_px   = st.number_input("Entry Price", value=float(ltp_v or 0), min_value=0.0, step=0.05)
                pt_qty  = st.number_input("Qty", min_value=1, value=1, step=1)
                pt_opt  = st.selectbox("Option Type", ["None", "CE", "PE"])
                pt_str  = st.number_input("Strike", min_value=0.0, step=50.0)
                if st.form_submit_button("Enter Trade ✅", type="primary", use_container_width=True):
                    if pt_px > 0:
                        tr = bot["paper"].enter_trade(
                            pt_sym, pt_type, pt_px, pt_qty,
                            None if pt_opt == "None" else pt_opt,
                            pt_str if pt_str > 0 else None,
                        )
                        st.success(f"Trade #{tr['id']} entered!")
                        st.rerun()

        with pf2:
            open_t = port.get("open_trades", [])
            if open_t:
                st.markdown("#### 📂 Open Positions")
                for tr in open_t:
                    with st.container(border=True):
                        c1, c2 = st.columns([3, 2])
                        c1.markdown(
                            f"**{tr.get('symbol')}** {tr.get('trade_type')}  "
                            f"`₹{tr.get('entry_price', 0):,.2f}` × {tr.get('quantity')}"
                        )
                        with st.form(f"ex{tr['id']}"):
                            lv = _ltp(tr.get("symbol", ""))
                            ep = st.number_input("Exit", value=float(lv or 0),
                                                 min_value=0.0, step=0.05, key=f"e{tr['id']}")
                            if st.form_submit_button("Exit 🔴", use_container_width=True):
                                if ep > 0:
                                    res = bot["paper"].exit_trade(tr["id"], ep)
                                    pv  = res.get("pnl", 0) or 0
                                    (st.success if pv >= 0 else st.error)(f"P&L: ₹{pv:+.2f}")
                                    st.rerun()
            else:
                st.info("No open positions — enter a trade to start paper trading")

        cl = port.get("closed_trades", [])
        if cl:
            st.markdown("#### 📜 Trade History")
            hdf = pd.DataFrame(cl)[["symbol", "trade_type", "entry_time", "entry_price", "exit_price", "quantity", "pnl"]]
            hdf.columns = ["Symbol", "Type", "Entry Time", "Entry ₹", "Exit ₹", "Qty", "P&L ₹"]
            st.dataframe(hdf, use_container_width=True, hide_index=True)

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 6 — BACKTEST
    # ══════════════════════════════════════════════════════════════════════════
    with tabs[5]:
        st.markdown("## 📈 Strategy Backtest")
        bc1, bc2 = st.columns([1, 3])
        with bc1:
            bt_sym = st.selectbox("Symbol", bot["syms"], key="btsym")
            run_bt = st.button("▶ Run Backtest", type="primary", use_container_width=True)

        if run_bt:
            df_bt = _data(bt_sym)
            if df_bt is not None and not df_bt.empty:
                with st.spinner("Running backtest…"):
                    res = bot["paper"].backtest_strategy({bt_sym: df_bt}, bot["eng"].generate_signal)
                with bc2:
                    bm = st.columns(5)
                    bm[0].metric("Trades",    res.get("total_trades", 0))
                    bm[1].metric("Win Rate",  f"{res.get('win_rate', 0):.1f}%")
                    bm[2].metric("Total P&L", f"₹{res.get('total_pnl', 0):+.2f}")
                    bm[3].metric("Max DD",    f"₹{res.get('max_drawdown', 0):.2f}")
                    bm[4].metric("Avg/Trade", f"₹{res.get('avg_pnl_per_trade', 0):.2f}")

                eq = res.get("equity_curve", [0])
                if len(eq) > 1:
                    import plotly.graph_objects as go
                    pos = eq[-1] >= 0
                    ef  = go.Figure(go.Scatter(
                        y=eq, mode="lines",
                        line=dict(color="#00ff88" if pos else "#ff3366", width=2),
                        fill="tozeroy",
                        fillcolor="rgba(0,255,136,0.08)" if pos else "rgba(255,51,102,0.08)",
                    ))
                    ef.update_layout(
                        template="plotly_dark", paper_bgcolor="#0a0e1a", plot_bgcolor="#0f1629",
                        height=300, title="Equity Curve",
                        margin=dict(l=40, r=20, t=40, b=20),
                    )
                    st.plotly_chart(ef, use_container_width=True, key="eq")

                if res.get("trades"):
                    st.dataframe(pd.DataFrame(res["trades"]), use_container_width=True, hide_index=True)
            else:
                st.warning("No data available for backtest")


if __name__ == "__main__":
    main()
