#!/usr/bin/env python3
"""
Scalper Bot — Intraday scalping assistant for NSE/BSE
Usage: python main.py
"""
import sys
import logging
import threading
import time
from datetime import datetime
from typing import Dict, Optional

import pandas as pd
from rich.console import Console
from rich.prompt import Prompt

from config import INSTRUMENTS, trading_config
from api.angelone import AngelOneAPI
from analysis.technical import TechnicalAnalysis
from analysis.volatility import VolatilityAnalysis
from analysis.volume import VolumeAnalysis
from analysis.expiry import ExpiryAnalysis
from trading.probability import ProbabilityCalculator
from trading.scalping import ScalpingEngine
from trading.paper_trading import PaperTradingDashboard
from database.db_manager import DatabaseManager
from ui.cli_display import (
    console, print_banner, print_analysis, print_signal,
    print_portfolio, print_market_scan, print_backtest_results,
    print_help, status_bar,
)
from ui.charts import ChartEngine
from utils.helpers import parse_query, get_date_range, is_market_hours

logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")


class ScalperBot:
    def __init__(self):
        self.api = AngelOneAPI()
        self.ta = TechnicalAnalysis()
        self.va = VolatilityAnalysis()
        self.vola = VolumeAnalysis()
        self.ea = ExpiryAnalysis()
        self.prob = ProbabilityCalculator()
        self.engine = ScalpingEngine()
        self.db = DatabaseManager()
        self.paper = PaperTradingDashboard(self.db)
        self.charts = ChartEngine()
        self._cache: Dict[str, pd.DataFrame] = {}
        self._cache_ts: Dict[str, datetime] = {}
        self._refresh_thread: Optional[threading.Thread] = None
        self._running = False

    # ── API & Data ────────────────────────────────────────────────────────

    def connect(self) -> bool:
        console.print("[cyan]Connecting to AngelOne...[/cyan]")
        ok = self.api.connect()
        if ok:
            console.print(f"[bold green]Connected ✓[/bold green]  Client: {self.api.obj and 'authenticated'}")
        else:
            console.print("[bold yellow]Running in OFFLINE mode (no API credentials or connection failed)[/bold yellow]")
            console.print("[dim]Set credentials in .env file for live data. Using cached/demo data.[/dim]")
        return ok

    def get_data(self, symbol: str, force: bool = False) -> Optional[pd.DataFrame]:
        sym = symbol.upper()
        now = datetime.now()
        cached_ts = self._cache_ts.get(sym)

        if not force and sym in self._cache and cached_ts:
            age = (now - cached_ts).seconds
            if age < trading_config.update_interval:
                return self._cache[sym]

        if self.api.connected:
            df = self.api.get_candle_data(sym, days_back=10)
            if df is not None and not df.empty:
                self._cache[sym] = df
                self._cache_ts[sym] = now
                self.db.cache_candles(sym, "FIVE_MINUTE",
                    [[str(idx), row["open"], row["high"], row["low"], row["close"], row["volume"]]
                     for idx, row in df.iterrows()])
                return df

        # Fallback to cached DB data
        cached = self.db.get_cached_candles(sym, "FIVE_MINUTE", 200)
        if cached:
            df = pd.DataFrame(cached)
            df["timestamp"] = pd.to_datetime(df["timestamp"])
            df = df.set_index("timestamp").sort_index()
            df = df[["open", "high", "low", "close", "volume"]].astype(float)
            self._cache[sym] = df
            return df

        console.print(f"[yellow]No data available for {sym}[/yellow]")
        return None

    def _start_refresh_loop(self):
        def _loop():
            while self._running:
                for sym in list(self._cache.keys()):
                    self.get_data(sym, force=True)
                time.sleep(trading_config.update_interval)

        self._running = True
        self._refresh_thread = threading.Thread(target=_loop, daemon=True)
        self._refresh_thread.start()

    # ── Command Handlers ──────────────────────────────────────────────────

    def cmd_analyze(self, symbol: str, analysis_type: str = "all"):
        df = self.get_data(symbol)
        if df is None:
            return

        sym = symbol.upper()
        ta_data = self.ta.full_analysis(df)
        vol_data = self.va.full_analysis(df)
        expiry_data = self.ea.full_analysis(sym.replace("50", ""))

        prob_data = self.prob.quick_probability(df, sym)
        print_analysis(sym, ta_data, prob_data, expiry_data)

        if analysis_type in ("all", "volatility"):
            console.print()
            console.print("[bold cyan]Volatility Analysis[/bold cyan]")
            from rich.table import Table
            from rich import box
            t = Table(box=box.SIMPLE, show_header=False)
            t.add_column(style="dim")
            t.add_column()
            t.add_row("HV 5-day", f"{vol_data.get('hv_5day', 0)}%")
            t.add_row("HV 20-day", f"{vol_data.get('hv_20day', 0)}%")
            t.add_row("Vol Regime", vol_data.get("vol_regime", ""))
            t.add_row("ATR", str(vol_data.get("atr", "")))
            t.add_row("T1↑", str(vol_data.get("t1_up", "")))
            t.add_row("T2↑", str(vol_data.get("t2_up", "")))
            t.add_row("T1↓", str(vol_data.get("t1_dn", "")))
            console.print(t)

        if analysis_type in ("all", "volume"):
            vol_ana = self.vola.full_analysis(df)
            console.print()
            console.print("[bold cyan]Volume & Momentum[/bold cyan]")
            from rich.table import Table
            from rich import box
            t = Table(box=box.SIMPLE, show_header=False)
            t.add_column(style="dim")
            t.add_column()
            t.add_row("VWAP", str(vol_ana.get("vwap", "")))
            t.add_row("Relative Volume", str(vol_ana.get("relative_volume", "")))
            t.add_row("Volume Signal", vol_ana.get("volume_signal", ""))
            t.add_row("Momentum", f"{vol_ana.get('roc_pct', 0)}%")
            t.add_row("Momentum Signal", vol_ana.get("momentum_signal", ""))
            t.add_row("Divergence", vol_ana.get("divergence", ""))
            poc = vol_ana.get("volume_profile", {}).get("poc")
            if poc:
                t.add_row("POC (Max Volume)", str(poc))
            console.print(t)

        self.db.log_analysis(sym, {**ta_data, "probability": prob_data.get("probability")})

    def cmd_signal(self, symbol: str):
        df = self.get_data(symbol)
        if df is None:
            return
        sig = self.engine.generate_signal(df, symbol.upper())
        print_signal(sig)

    def cmd_scan(self):
        console.print("[cyan]Scanning all instruments...[/cyan]")
        data_map = {}
        for sym in INSTRUMENTS:
            df = self.get_data(sym)
            if df is not None:
                data_map[sym] = df
        signals = self.engine.scan_all_instruments(data_map)
        print_market_scan(signals)

    def cmd_probability(self, symbol: str, direction: str = None):
        df = self.get_data(symbol)
        if df is None:
            return
        sym = symbol.upper()
        if direction:
            result = self.prob.calculate(df, direction.upper(), sym)
        else:
            result = self.prob.quick_probability(df, sym)

        from ui.cli_display import _print_probability
        _print_probability(result)
        console.print(f"\n[dim]Buy probability:  [green]{result.get('buy_probability', result.get('probability', ''))}%[/green]")
        console.print(f"Sell probability: [red]{result.get('sell_probability', '')}%[/red][/dim]")

    def cmd_expiry(self, symbol: str = "NIFTY"):
        data = self.ea.expiry_volatility_pattern(symbol)
        from ui.cli_display import _print_expiry
        _print_expiry(data)

        if self.api.connected:
            ltp = self.api.get_ltp(symbol.replace("WK", "").replace("MO", "").upper() + ("50" if "NIFTY" in symbol.upper() and "BANK" not in symbol.upper() else ""))
            if ltp:
                console.print(f"\n[dim]Current LTP: {ltp}[/dim]")
                from utils.helpers import strikes_around_price
                strikes = strikes_around_price(ltp, 3, 50)
                console.print(f"[dim]ATM Strike: {strikes[3]}  Nearby: {strikes}[/dim]")

    def cmd_paper_trade(self, parts: list):
        if len(parts) < 4:
            console.print("[red]Usage: paper buy/sell SYMBOL PRICE QTY [CE/PE STRIKE][/red]")
            return
        action = parts[1].upper()
        sym = parts[2].upper()
        try:
            price = float(parts[3])
            qty = int(parts[4]) if len(parts) > 4 else 1
        except ValueError:
            console.print("[red]Invalid price or quantity[/red]")
            return

        option_type = parts[5].upper() if len(parts) > 5 else None
        strike = float(parts[6]) if len(parts) > 6 else None

        trade = self.paper.enter_trade(sym, action, price, qty, option_type, strike)
        console.print(f"[bold green]Paper trade entered:[/bold green] #{trade['id']}  {action} {sym} @ {price} x {qty}")

    def cmd_paper_exit(self, parts: list):
        if len(parts) < 3:
            console.print("[red]Usage: paper exit TRADE_ID EXIT_PRICE[/red]")
            return
        try:
            trade_id = int(parts[2])
            exit_price = float(parts[3]) if len(parts) > 3 else None
        except (ValueError, IndexError):
            console.print("[red]Invalid trade ID or price[/red]")
            return

        if not exit_price:
            sym_hint = Prompt.ask("Enter symbol to get LTP")
            exit_price = self.api.get_ltp(sym_hint.upper()) if self.api.connected else 0
            if not exit_price:
                exit_price = float(Prompt.ask("Enter exit price manually"))

        result = self.paper.exit_trade(trade_id, exit_price)
        if result:
            pnl = result.get("pnl", 0) or 0
            color = "green" if pnl >= 0 else "red"
            console.print(f"Trade #{trade_id} closed.  P&L: [{color}]{pnl:+.2f}[/{color}]")

    def cmd_chart(self, symbol: str):
        df = self.get_data(symbol)
        if df is None:
            return
        ta_data = self.ta.full_analysis(df)
        console.print(f"[cyan]Generating chart for {symbol.upper()}...[/cyan]")
        path = self.charts.candlestick_with_indicators(df, symbol.upper(), ta_data)
        if path:
            console.print(f"[green]Chart saved: {path}[/green]")
            self.charts.open_chart(path)
        else:
            console.print("[yellow]plotly not installed. Run: pip install plotly kaleido[/yellow]")

    def cmd_backtest(self, symbol: str):
        console.print(f"[cyan]Running backtest for {symbol.upper()}...[/cyan]")
        df = self.get_data(symbol)
        if df is None:
            return
        data_map = {symbol.upper(): df}
        result = self.paper.backtest_strategy(data_map, self.engine.generate_signal)
        print_backtest_results(result)

    def cmd_ask(self, query: str):
        """Process natural language trading queries."""
        parsed = parse_query(query)
        symbol = parsed.get("symbol") or "NIFTY50"
        intent = parsed.get("intent")
        direction = None

        console.print(f"\n[dim]Query: {query}[/dim]")
        console.print(f"[dim]Parsed: intent={intent}, symbol={symbol}[/dim]\n")

        df = self.get_data(symbol)
        if df is None:
            console.print(f"[yellow]Could not fetch data for {symbol}[/yellow]")
            return

        ta_data = self.ta.full_analysis(df)
        expiry_data = self.ea.expiry_volatility_pattern(symbol.replace("50", ""))

        if intent == "trade_recommendation":
            option_type = parsed.get("option_type", "CE")
            strike = parsed.get("strike")
            direction = "BUY" if option_type == "CE" else "SELL"
            prob_result = self.prob.calculate(df, direction, symbol)
            sig = self.engine.generate_signal(df, symbol)

            console.print(f"[bold]Query Analysis: {symbol} {option_type} {'at ' + str(strike) if strike else ''}[/bold]")
            print_analysis(symbol, ta_data, prob_result, expiry_data)
            print_signal(sig)

            if strike:
                current = ta_data.get("price", 0)
                target_prob = self.prob.target_reach_probability(df, current, strike)
                console.print(f"\n[bold]Strike {strike} reach probability: [{('green' if target_prob['probability'] > 55 else 'red')}]{target_prob['probability']}%[/{'green' if target_prob['probability'] > 55 else 'red'}][/bold]")
                console.print(f"[dim]Distance: {target_prob['distance']} pts ({target_prob['atr_multiples']} ATR)[/dim]")

        elif intent == "probability":
            target = parsed.get("target_price")
            current = ta_data.get("price", 0)
            prob_result = self.prob.quick_probability(df, symbol)
            print_analysis(symbol, ta_data, prob_result, expiry_data)

            if target and current:
                tp = self.prob.target_reach_probability(df, current, target)
                color = "green" if tp["probability"] > 55 else "yellow" if tp["probability"] > 40 else "red"
                console.print(f"\n[bold]Probability of {symbol} reaching {target}: [{color}]{tp['probability']}%[/{color}][/bold]")
                console.print(f"[dim]Current: {current}  Distance: {tp['distance']} pts  Direction: {tp['direction']}[/dim]")

        elif intent == "setup_quality":
            prob_result = self.prob.quick_probability(df, symbol)
            sig = self.engine.generate_signal(df, symbol)
            print_analysis(symbol, ta_data, prob_result, expiry_data)
            print_signal(sig)
            p = prob_result.get("probability", 50)
            console.print(f"\n[bold]Setup quality assessment: Entry chances = [{('green' if p >= 60 else 'yellow' if p >= 50 else 'red')}]{p}%[/{'green' if p >= 60 else 'yellow' if p >= 50 else 'red'}][/bold]")

        else:  # analysis
            prob_result = self.prob.quick_probability(df, symbol)
            print_analysis(symbol, ta_data, prob_result, expiry_data)
            print_signal(self.engine.generate_signal(df, symbol))

    # ── Main Loop ─────────────────────────────────────────────────────────

    def run(self):
        print_banner()
        self.connect()
        self._start_refresh_loop()

        console.print()
        status_bar()
        console.print("[dim]Type [bold]help[/bold] for commands, [bold]quit[/bold] to exit[/dim]\n")

        while True:
            try:
                raw = Prompt.ask("[bold cyan]scalper>[/bold cyan]")
            except (KeyboardInterrupt, EOFError):
                break

            line = raw.strip()
            if not line:
                continue
            parts = line.split()
            cmd = parts[0].lower()

            try:
                if cmd in ("quit", "exit", "q"):
                    break
                elif cmd == "help":
                    print_help()
                elif cmd == "analyze":
                    sym = parts[1].upper() if len(parts) > 1 else "NIFTY50"
                    atype = parts[2].lower() if len(parts) > 2 else "all"
                    self.cmd_analyze(sym, atype)
                elif cmd == "signal":
                    sym = parts[1].upper() if len(parts) > 1 else "NIFTY50"
                    self.cmd_signal(sym)
                elif cmd == "scan":
                    self.cmd_scan()
                elif cmd in ("prob", "probability"):
                    sym = parts[1].upper() if len(parts) > 1 else "NIFTY50"
                    direction = parts[2].upper() if len(parts) > 2 else None
                    self.cmd_probability(sym, direction)
                elif cmd == "expiry":
                    sym = parts[1].upper() if len(parts) > 1 else "NIFTY"
                    self.cmd_expiry(sym)
                elif cmd == "paper":
                    if len(parts) > 1 and parts[1].lower() == "exit":
                        self.cmd_paper_exit(parts)
                    else:
                        self.cmd_paper_trade(parts)
                elif cmd in ("portfolio", "port"):
                    portfolio = self.paper.get_portfolio()
                    print_portfolio(portfolio)
                elif cmd == "chart":
                    sym = parts[1].upper() if len(parts) > 1 else "NIFTY50"
                    self.cmd_chart(sym)
                elif cmd == "backtest":
                    sym = parts[1].upper() if len(parts) > 1 else "NIFTY50"
                    self.cmd_backtest(sym)
                elif cmd == "ask":
                    query = " ".join(parts[1:])
                    if query:
                        self.cmd_ask(query)
                    else:
                        query = Prompt.ask("Your trading query")
                        self.cmd_ask(query)
                elif cmd == "status":
                    status_bar()
                    console.print(f"[dim]Connected: {self.api.connected}  Cached symbols: {list(self._cache.keys())}[/dim]")
                else:
                    # Try natural language for unrecognized input
                    if len(line) > 10:
                        self.cmd_ask(line)
                    else:
                        console.print(f"[yellow]Unknown command: {cmd}. Type help for commands.[/yellow]")
            except Exception as e:
                console.print(f"[red]Error: {e}[/red]")
                logging.exception("Command error")

        self._running = False
        self.api.disconnect()
        console.print("\n[dim]Goodbye. Trade safe![/dim]")


def main():
    bot = ScalperBot()
    bot.run()


if __name__ == "__main__":
    main()
