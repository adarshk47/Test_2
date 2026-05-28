from datetime import datetime
from typing import Dict, List, Optional

from config import trading_config
from database.db_manager import DatabaseManager


class PaperTradingDashboard:
    def __init__(self, db: DatabaseManager = None, capital: float = None):
        self.db = db or DatabaseManager()
        self.capital = capital or trading_config.default_capital
        self._open_trades: List[Dict] = []
        self._load_open_trades()

    def _load_open_trades(self):
        self._open_trades = self.db.get_open_trades()

    def enter_trade(
        self,
        symbol: str,
        trade_type: str,
        entry_price: float,
        quantity: int,
        option_type: str = None,
        strike: float = None,
        notes: str = None,
    ) -> Dict:
        trade = {
            "symbol": symbol,
            "trade_type": trade_type.upper(),
            "option_type": option_type,
            "strike": strike,
            "entry_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "entry_price": entry_price,
            "quantity": quantity,
            "notes": notes,
        }
        trade_id = self.db.save_paper_trade(trade)
        trade["id"] = trade_id
        self._open_trades.append(trade)
        return trade

    def exit_trade(self, trade_id: int, exit_price: float) -> Dict:
        result = self.db.close_paper_trade(trade_id, exit_price)
        self._open_trades = [t for t in self._open_trades if t.get("id") != trade_id]
        return result

    def exit_all(self, price_map: Dict[str, float]) -> List[Dict]:
        """Exit all open trades at current prices."""
        results = []
        for trade in list(self._open_trades):
            sym = trade.get("symbol", "")
            price = price_map.get(sym)
            if price:
                results.append(self.exit_trade(trade["id"], price))
        return results

    def get_portfolio(self) -> Dict:
        open_trades = self.db.get_open_trades()
        closed_trades = self.db.get_closed_trades(50)
        metrics = self.db.get_performance_metrics()

        unrealized_pnl = 0.0
        for t in open_trades:
            # Can't calculate without current price here; shows entry info
            unrealized_pnl += 0

        realized_pnl = sum(t.get("pnl", 0) or 0 for t in closed_trades)

        return {
            "capital": self.capital,
            "open_positions": len(open_trades),
            "open_trades": open_trades,
            "closed_trades": closed_trades[:10],
            "realized_pnl": round(realized_pnl, 2),
            "metrics": metrics,
        }

    def get_trade_history(self, limit: int = 20) -> List[Dict]:
        return self.db.get_closed_trades(limit)

    def backtest_strategy(self, df_map: Dict, strategy_fn, lookback_days: int = 30) -> Dict:
        """Simple backtest: apply strategy to historical data and simulate trades."""
        from analysis.technical import TechnicalAnalysis
        ta = TechnicalAnalysis()
        results = []
        total_pnl = 0
        wins = 0
        losses = 0
        max_drawdown = 0
        equity_curve = [0]

        for symbol, df in df_map.items():
            if df is None or len(df) < 40:
                continue

            # Walk-forward simulation
            for i in range(30, len(df) - 1):
                window = df.iloc[:i]
                signal = strategy_fn(window, symbol)

                if signal.get("signal") not in ("BUY", "SELL"):
                    continue

                entry = float(df["close"].iloc[i])
                exit_price = float(df["close"].iloc[i + 1])
                direction = signal["signal"]
                targets = signal.get("targets", [])
                stop_loss = signal.get("stop_loss")

                # Simulate outcome
                if direction == "BUY":
                    if stop_loss and exit_price <= stop_loss:
                        pnl = exit_price - entry
                    elif targets and exit_price >= targets[0]:
                        pnl = targets[0] - entry
                    else:
                        pnl = exit_price - entry
                else:
                    if stop_loss and exit_price >= stop_loss:
                        pnl = entry - exit_price
                    elif targets and exit_price <= targets[0]:
                        pnl = entry - targets[0]
                    else:
                        pnl = entry - exit_price

                total_pnl += pnl
                equity_curve.append(equity_curve[-1] + pnl)
                if pnl > 0:
                    wins += 1
                else:
                    losses += 1

                peak = max(equity_curve)
                dd = peak - equity_curve[-1]
                max_drawdown = max(max_drawdown, dd)

                results.append({
                    "symbol": symbol,
                    "direction": direction,
                    "entry": round(entry, 2),
                    "exit": round(exit_price, 2),
                    "pnl": round(pnl, 2),
                    "time": str(df.index[i]) if hasattr(df.index, "__iter__") else "",
                })

        total_trades = wins + losses
        return {
            "total_trades": total_trades,
            "winning_trades": wins,
            "losing_trades": losses,
            "win_rate": round(wins / total_trades * 100, 2) if total_trades > 0 else 0,
            "total_pnl": round(total_pnl, 2),
            "max_drawdown": round(max_drawdown, 2),
            "avg_pnl_per_trade": round(total_pnl / total_trades, 2) if total_trades > 0 else 0,
            "equity_curve": equity_curve,
            "trades": results[-20:],
        }
