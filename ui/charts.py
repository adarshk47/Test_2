import webbrowser
import tempfile
import os
from typing import Dict, Optional
from pathlib import Path

import pandas as pd


class ChartEngine:
    def __init__(self):
        self.output_dir = Path("charts")
        self.output_dir.mkdir(exist_ok=True)

    def candlestick_with_indicators(self, df: pd.DataFrame, symbol: str, ta_data: Dict = None) -> str:
        try:
            import plotly.graph_objects as go
            from plotly.subplots import make_subplots
        except ImportError:
            return ""

        fig = make_subplots(
            rows=3, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.03,
            row_heights=[0.6, 0.2, 0.2],
            subplot_titles=[f"{symbol} - 5min", "RSI (14)", "MACD"],
        )

        # Candlestick
        fig.add_trace(
            go.Candlestick(
                x=df.index,
                open=df["open"],
                high=df["high"],
                low=df["low"],
                close=df["close"],
                name=symbol,
                increasing_line_color="#00e676",
                decreasing_line_color="#ff1744",
            ),
            row=1, col=1,
        )

        # Bollinger Bands
        from analysis.technical import TechnicalAnalysis
        ta = TechnicalAnalysis()
        bb_upper, bb_mid, bb_lower = ta.bollinger_bands(df["close"])

        fig.add_trace(go.Scatter(x=df.index, y=bb_upper, line=dict(color="rgba(173,216,230,0.5)", width=1), name="BB Upper"), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=bb_lower, line=dict(color="rgba(173,216,230,0.5)", width=1), name="BB Lower", fill="tonexty", fillcolor="rgba(173,216,230,0.07)"), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=bb_mid, line=dict(color="rgba(173,216,230,0.3)", width=1, dash="dot"), name="BB Mid"), row=1, col=1)

        # EMA lines
        ema9 = ta.ema(df["close"], 9)
        ema21 = ta.ema(df["close"], 21)
        fig.add_trace(go.Scatter(x=df.index, y=ema9, line=dict(color="#ffeb3b", width=1), name="EMA 9"), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=ema21, line=dict(color="#ff9800", width=1), name="EMA 21"), row=1, col=1)

        # VWAP
        vwap = ta.vwap(df)
        fig.add_trace(go.Scatter(x=df.index, y=vwap, line=dict(color="#e040fb", width=1.5, dash="dot"), name="VWAP"), row=1, col=1)

        # Volume bars
        colors = ["#00e676" if c >= o else "#ff1744" for c, o in zip(df["close"], df["open"])]
        fig.add_trace(go.Bar(x=df.index, y=df["volume"], marker_color=colors, name="Volume", opacity=0.4), row=1, col=1)

        # RSI
        rsi_series = ta.rsi(df["close"])
        fig.add_trace(go.Scatter(x=df.index, y=rsi_series, line=dict(color="#64b5f6", width=1.5), name="RSI"), row=2, col=1)
        fig.add_hline(y=70, line_dash="dot", line_color="#ff1744", opacity=0.5, row=2, col=1)
        fig.add_hline(y=30, line_dash="dot", line_color="#00e676", opacity=0.5, row=2, col=1)
        fig.add_hline(y=50, line_dash="dot", line_color="gray", opacity=0.3, row=2, col=1)

        # MACD
        macd_line, signal_line, histogram = ta.macd(df["close"])
        hist_colors = ["#00e676" if v >= 0 else "#ff1744" for v in histogram]
        fig.add_trace(go.Bar(x=df.index, y=histogram, marker_color=hist_colors, name="Histogram", opacity=0.7), row=3, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=macd_line, line=dict(color="#64b5f6", width=1.5), name="MACD"), row=3, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=signal_line, line=dict(color="#ff9800", width=1.5), name="Signal"), row=3, col=1)

        # Layout
        fig.update_layout(
            template="plotly_dark",
            title=dict(text=f"{symbol} Intraday Analysis", font=dict(size=16, color="white")),
            xaxis_rangeslider_visible=False,
            showlegend=True,
            height=750,
            margin=dict(l=40, r=40, t=60, b=40),
            paper_bgcolor="#0d1117",
            plot_bgcolor="#161b22",
        )
        fig.update_xaxes(showgrid=True, gridcolor="#21262d", showspikes=True)
        fig.update_yaxes(showgrid=True, gridcolor="#21262d")

        out_path = self.output_dir / f"{symbol}_chart.html"
        fig.write_html(str(out_path))
        return str(out_path)

    def volume_profile_chart(self, df: pd.DataFrame, symbol: str) -> str:
        try:
            import plotly.graph_objects as go
            from analysis.volume import VolumeAnalysis
        except ImportError:
            return ""

        vp = VolumeAnalysis().volume_profile(df)
        if not isinstance(vp, dict):
            return ""
        profile = vp.get("profile", [])
        if not profile:
            return ""

        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=[p["volume"] for p in profile],
            y=[p["price"] for p in profile],
            orientation="h",
            marker_color=[
                "#ff9800" if p["price"] == vp.get("poc") else
                "#00e676" if p["vol_pct"] > 10 else "#64b5f6"
                for p in profile
            ],
            name="Volume Profile",
        ))
        poc = vp.get("poc")
        if poc:
            fig.add_hline(y=poc, line_dash="dash", line_color="#ff9800", annotation_text=f"POC {poc}")

        fig.update_layout(
            template="plotly_dark",
            title=f"{symbol} Volume Profile",
            height=500,
            paper_bgcolor="#0d1117",
            plot_bgcolor="#161b22",
        )
        out_path = self.output_dir / f"{symbol}_vp.html"
        fig.write_html(str(out_path))
        return str(out_path)

    def open_chart(self, path: str):
        if path and os.path.exists(path):
            webbrowser.open(f"file://{os.path.abspath(path)}")
