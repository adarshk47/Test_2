from datetime import datetime
from typing import Dict, List, Optional

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.columns import Columns
from rich.text import Text
from rich.rule import Rule
from rich import box
from rich.progress import Progress, SpinnerColumn, TextColumn

from utils.helpers import format_currency, format_pnl, is_market_hours, time_to_close

console = Console()


def _color_for_value(value: float, positive_good: bool = True) -> str:
    if value > 0:
        return "green" if positive_good else "red"
    if value < 0:
        return "red" if positive_good else "green"
    return "yellow"


def _prob_color(prob: float) -> str:
    if prob >= 70:
        return "bright_green"
    if prob >= 55:
        return "green"
    if prob >= 45:
        return "yellow"
    return "red"


def print_banner():
    console.print()
    console.print(Panel(
        "[bold cyan]SCALPER BOT[/bold cyan]  [dim]Intraday Scalping Assistant[/dim]\n"
        "[dim]AngelOne SmartAPI  ·  NSE/BSE  ·  5-min candles[/dim]",
        border_style="cyan",
        padding=(0, 2),
    ))


def print_analysis(symbol: str, ta: Dict, prob: Dict = None, expiry: Dict = None):
    console.print()
    console.print(Rule(f"[bold white]{symbol}[/bold white]  Analysis", style="blue"))

    # Price & Indicators
    price_color = "green" if ta.get("above_vwap") else "red"
    trend = ta.get("trend", "UNKNOWN")
    trend_color = "green" if "UP" in trend else "red" if "DOWN" in trend else "yellow"

    table = Table(box=box.SIMPLE, show_header=False, padding=(0, 2))
    table.add_column(style="dim")
    table.add_column()
    table.add_column(style="dim")
    table.add_column()

    table.add_row("Price", f"[{price_color}]{ta.get('price', '—')}[/{price_color}]",
                  "Trend", f"[{trend_color}]{trend}[/{trend_color}]")
    table.add_row("RSI(14)", _rsi_display(ta.get("rsi", 50)),
                  "MACD Signal", _signal_badge(ta.get("macd_signal_str", "")))
    table.add_row("VWAP", str(ta.get("vwap", "—")),
                  "ATR", str(ta.get("atr", "—")))
    table.add_row("BB Upper", str(ta.get("bb_upper", "—")),
                  "BB Lower", str(ta.get("bb_lower", "—")))
    table.add_row("BB Position", f"{ta.get('bb_position_pct', 0):.1f}%",
                  "Structure", ta.get("structure", "—"))

    sr = {}
    for k in ("support", "resistance", "nearest_support", "nearest_resistance"):
        sr[k] = ta.get(k)
    if sr.get("support"):
        table.add_row("Supports", str(sr.get("support", [])), "Resistances", str(sr.get("resistance", [])))

    console.print(table)

    # Probability panel
    if prob:
        _print_probability(prob)

    # Expiry info
    if expiry:
        _print_expiry(expiry)


def _rsi_display(rsi: float) -> str:
    if rsi is None:
        return "—"
    if rsi < 30:
        return f"[bold bright_green]{rsi}[/bold bright_green] (Oversold)"
    if rsi < 40:
        return f"[green]{rsi}[/green] (Near OS)"
    if rsi > 70:
        return f"[bold bright_red]{rsi}[/bold bright_red] (Overbought)"
    if rsi > 60:
        return f"[red]{rsi}[/red] (Near OB)"
    return f"[yellow]{rsi}[/yellow]"


def _signal_badge(signal: str) -> str:
    colors = {
        "BULLISH_CROSSOVER": "bold bright_green",
        "BULLISH": "green",
        "BEARISH_CROSSOVER": "bold bright_red",
        "BEARISH": "red",
    }
    return f"[{colors.get(signal, 'yellow')}]{signal}[/{colors.get(signal, 'yellow')}]"


def _print_probability(prob: Dict):
    p = prob.get("probability", 50)
    direction = prob.get("direction", "")
    verdict = prob.get("verdict", "")
    rec = prob.get("recommendation", "WAIT")
    color = _prob_color(p)

    rec_colors = {"BUY": "bright_green", "SELL": "bright_red", "WAIT": "yellow", "AVOID": "dim red"}
    rec_color = rec_colors.get(rec, "white")

    factors = prob.get("factor_breakdown", {})
    factor_str = "  ".join([f"[dim]{k.replace('_score', '')}:[/dim][cyan]{v}[/cyan]"
                            for k, v in factors.items()])

    console.print(Panel(
        f"[bold]Entry Chances: [{color}]{p}%[/{color}][/bold]   "
        f"[dim]→[/dim]  [{rec_color}][bold]{rec}[/bold][/{rec_color}]   "
        f"[dim]Confidence: {prob.get('confidence', 0)}%[/dim]\n"
        f"[dim]Verdict:[/dim] {verdict}   [dim]Direction:[/dim] {direction}\n"
        f"{factor_str}",
        title="[bold]Trade Probability[/bold]",
        border_style=color,
        padding=(0, 1),
    ))


def _print_expiry(expiry: Dict):
    is_expiry = expiry.get("is_expiry", False)
    dte = expiry.get("dte", 0)
    mult = expiry.get("target_multiplier", 1.0)
    color = "bright_yellow" if is_expiry else "dim"
    badge = "[bold bright_yellow] EXPIRY DAY [/bold bright_yellow]" if is_expiry else f"DTE: {dte}"

    console.print(Panel(
        f"{badge}   Expiry: {expiry.get('expiry_date', '')}   "
        f"Target Multiplier: [bold]{mult}x[/bold]\n"
        f"[dim]{expiry.get('phase_pattern', '')}[/dim]\n"
        f"IV Crush Risk: [{color}]{expiry.get('iv_crush_risk', '')}[/{color}]   "
        f"Targets: {expiry.get('recommended_targets', '')}",
        title="[bold]Expiry Analysis[/bold]",
        border_style=color,
        padding=(0, 1),
    ))


def print_signal(sig: Dict):
    console.print()
    signal = sig.get("signal", "WAIT")
    quality = sig.get("quality", "")
    sig_colors = {"BUY": "bright_green", "SELL": "bright_red", "WAIT": "yellow"}
    color = sig_colors.get(signal, "yellow")

    lines = [
        f"Signal: [{color}][bold]{signal}[/bold][/{color}]  [{quality == 'STRONG' and 'bright_white' or 'dim'}]({quality})[/{quality == 'STRONG' and 'bright_white' or 'dim'}]",
        f"Entry: [bold]{sig.get('entry', '—')}[/bold]   SL: [red]{sig.get('stop_loss', '—')}[/red]   R/R: {sig.get('risk_reward', 0)}",
    ]
    if sig.get("targets"):
        t = sig["targets"]
        lines.append(f"Targets: [green]T1={t[0]}  T2={t[1] if len(t) > 1 else '—'}  T3={t[2] if len(t) > 2 else '—'}[/green]")
    if sig.get("time_warnings"):
        for w in sig["time_warnings"]:
            lines.append(f"[bold yellow]⚠ {w}[/bold yellow]")
    conditions = sig.get("conditions_met", [])
    if conditions:
        lines.append(f"[dim]Conditions: {', '.join(conditions)}[/dim]")

    console.print(Panel("\n".join(lines), title=f"[bold]{sig.get('symbol', '')} Signal[/bold]",
                        border_style=color, padding=(0, 1)))


def print_portfolio(portfolio: Dict):
    console.print()
    console.print(Rule("[bold white]Paper Trading Portfolio[/bold white]", style="magenta"))
    metrics = portfolio.get("metrics", {})

    # Summary row
    pnl = portfolio.get("realized_pnl", 0)
    pnl_color = _color_for_value(pnl)
    summary = Table(box=box.SIMPLE, show_header=False)
    summary.add_column(style="dim")
    summary.add_column()
    summary.add_row("Capital", format_currency(portfolio.get("capital", 0)))
    summary.add_row("Realized P&L", f"[{pnl_color}]{format_pnl(pnl)}[/{pnl_color}]")
    summary.add_row("Open Positions", str(portfolio.get("open_positions", 0)))
    summary.add_row("Win Rate", f"{metrics.get('win_rate', 0)}%")
    summary.add_row("Total Trades", str(metrics.get("total_trades", 0)))
    summary.add_row("Max Drawdown", f"[red]{format_currency(metrics.get('max_drawdown', 0))}[/red]")
    summary.add_row("Profit Factor", str(metrics.get("profit_factor", 0)))
    console.print(summary)

    # Open trades
    open_trades = portfolio.get("open_trades", [])
    if open_trades:
        console.print("\n[bold]Open Positions:[/bold]")
        t = Table(box=box.SIMPLE_HEAVY, header_style="bold cyan")
        t.add_column("ID")
        t.add_column("Symbol")
        t.add_column("Type")
        t.add_column("Entry")
        t.add_column("Qty")
        t.add_column("Time")
        for trade in open_trades:
            t.add_row(
                str(trade.get("id")),
                trade.get("symbol", ""),
                f"[{'green' if trade.get('trade_type') == 'BUY' else 'red'}]{trade.get('trade_type', '')}[/]",
                str(trade.get("entry_price", "")),
                str(trade.get("quantity", "")),
                trade.get("entry_time", "")[-8:],
            )
        console.print(t)

    # Recent closed trades
    closed = portfolio.get("closed_trades", [])
    if closed:
        console.print("\n[bold]Recent Trades:[/bold]")
        t = Table(box=box.SIMPLE_HEAVY, header_style="bold cyan")
        t.add_column("Symbol")
        t.add_column("Type")
        t.add_column("Entry")
        t.add_column("Exit")
        t.add_column("P&L")
        for trade in closed[:8]:
            pnl_val = trade.get("pnl", 0) or 0
            pnl_color = _color_for_value(pnl_val)
            t.add_row(
                trade.get("symbol", ""),
                trade.get("trade_type", ""),
                str(trade.get("entry_price", "")),
                str(trade.get("exit_price", "")),
                f"[{pnl_color}]{format_pnl(pnl_val)}[/{pnl_color}]",
            )
        console.print(t)


def print_market_scan(signals: List[Dict]):
    console.print()
    console.print(Rule("[bold white]Market Scan Results[/bold white]", style="green"))
    if not signals:
        console.print("[dim]No actionable signals found. Market may be consolidating.[/dim]")
        return

    t = Table(box=box.SIMPLE_HEAVY, header_style="bold cyan")
    t.add_column("Symbol")
    t.add_column("Signal")
    t.add_column("Quality")
    t.add_column("Entry")
    t.add_column("T1")
    t.add_column("SL")
    t.add_column("R/R")
    t.add_column("RSI")
    t.add_column("Trend")

    for sig in signals:
        sc = "bright_green" if sig.get("signal") == "BUY" else "bright_red"
        ta = sig.get("ta", {})
        targets = sig.get("targets", [])
        t.add_row(
            sig.get("symbol", ""),
            f"[{sc}]{sig.get('signal', '')}[/{sc}]",
            sig.get("quality", ""),
            str(sig.get("entry", "")),
            str(targets[0] if targets else "—"),
            str(sig.get("stop_loss", "—")),
            str(sig.get("risk_reward", "—")),
            str(ta.get("rsi", "—")),
            ta.get("trend", "—"),
        )
    console.print(t)


def print_backtest_results(result: Dict):
    console.print()
    console.print(Rule("[bold white]Backtest Results[/bold white]", style="cyan"))
    t = Table(box=box.SIMPLE, show_header=False)
    t.add_column(style="dim")
    t.add_column()
    t.add_row("Total Trades", str(result.get("total_trades", 0)))
    t.add_row("Win Rate", f"{result.get('win_rate', 0)}%")
    pnl = result.get("total_pnl", 0)
    t.add_row("Total P&L", f"[{_color_for_value(pnl)}]{format_pnl(pnl)}[/{_color_for_value(pnl)}]")
    t.add_row("Max Drawdown", f"[red]{result.get('max_drawdown', 0)}[/red]")
    t.add_row("Avg P&L/Trade", f"{result.get('avg_pnl_per_trade', 0)}")
    console.print(t)


def print_help():
    console.print()
    console.print(Panel(
        "[bold cyan]COMMANDS[/bold cyan]\n\n"
        "[bold]analyze[/bold] SYMBOL         Full technical analysis\n"
        "[bold]signal[/bold] SYMBOL           Get trading signal\n"
        "[bold]scan[/bold]                     Scan all instruments\n"
        "[bold]prob[/bold] SYMBOL BUY/SELL     Trade probability\n"
        "[bold]expiry[/bold] NIFTY/BANKNIFTY  Expiry analysis\n"
        "[bold]paper buy[/bold] SYM PRICE QTY Enter paper trade\n"
        "[bold]paper sell[/bold] SYM PRICE QTY Enter paper short\n"
        "[bold]paper exit[/bold] ID PRICE      Exit paper trade\n"
        "[bold]portfolio[/bold]                Paper trading portfolio\n"
        "[bold]backtest[/bold] SYMBOL          Backtest strategy\n"
        "[bold]chart[/bold] SYMBOL             Open chart in browser\n"
        "[bold]ask[/bold] <natural query>       Natural language query\n"
        "[bold]help[/bold]                      Show this help\n"
        "[bold]quit[/bold]                      Exit\n\n"
        "[dim]Examples:[/dim]\n"
        "  analyze NIFTY50\n"
        "  ask Should I take NIFTY call at 24100?\n"
        "  ask What is the probability of SBIN reaching 550?\n"
        "  paper buy NIFTY50 24100 50",
        title="[bold]Help[/bold]",
        border_style="cyan",
        padding=(0, 2),
    ))


def status_bar():
    mkt = "[bold green]OPEN[/bold green]" if is_market_hours() else "[bold red]CLOSED[/bold red]"
    ttc = time_to_close()
    now = datetime.now().strftime("%H:%M:%S")
    console.print(f"[dim]{now}  Market: {mkt}  Time to close: {ttc} min[/dim]")
