import sqlite3
import json
import time
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any


def _default_db_path() -> str:
    """
    On Streamlit Cloud /data may be read-only → use /tmp.
    Locally use project data/ folder.
    """
    local = Path(__file__).parent.parent / "data" / "trading_bot.db"
    try:
        local.parent.mkdir(parents=True, exist_ok=True)
        # Quick write test
        test = local.parent / ".write_test"
        test.touch()
        test.unlink()
        return str(local)
    except (PermissionError, OSError):
        return "/tmp/scalper_bot.db"


DB_PATH = _default_db_path()


class DatabaseManager:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._setup_tables()

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(
            self.db_path,
            timeout=30,           # wait up to 30s for lock to release
            check_same_thread=False,
        )
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA busy_timeout=30000")  # 30s busy timeout
        return conn

    def _execute(self, fn, retries: int = 5):
        """Run fn(conn) with retry on OperationalError (locked)."""
        for attempt in range(retries):
            try:
                with self._conn() as conn:
                    return fn(conn)
            except sqlite3.OperationalError as e:
                if "locked" in str(e).lower() and attempt < retries - 1:
                    time.sleep(0.2 * (attempt + 1))
                else:
                    raise

    def _setup_tables(self):
        def _run(conn):
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS paper_trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    trade_type TEXT NOT NULL,
                    option_type TEXT,
                    strike REAL,
                    entry_time TEXT NOT NULL,
                    entry_price REAL NOT NULL,
                    quantity INTEGER NOT NULL,
                    exit_time TEXT,
                    exit_price REAL,
                    pnl REAL,
                    status TEXT DEFAULT 'OPEN',
                    notes TEXT,
                    created_at TEXT DEFAULT (datetime('now'))
                );

                CREATE TABLE IF NOT EXISTS candle_cache (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    interval TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    open REAL,
                    high REAL,
                    low REAL,
                    close REAL,
                    volume INTEGER,
                    UNIQUE(symbol, interval, timestamp)
                );

                CREATE TABLE IF NOT EXISTS analysis_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    rsi REAL,
                    macd REAL,
                    macd_signal REAL,
                    bb_upper REAL,
                    bb_lower REAL,
                    atr REAL,
                    trend TEXT,
                    probability REAL,
                    recommendation TEXT,
                    raw_data TEXT
                );

                CREATE TABLE IF NOT EXISTS performance_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    total_trades INTEGER,
                    winning_trades INTEGER,
                    losing_trades INTEGER,
                    total_pnl REAL,
                    max_drawdown REAL,
                    win_rate REAL,
                    created_at TEXT DEFAULT (datetime('now'))
                );
            """)
        try:
            self._execute(_run)
        except Exception as e:
            # Non-fatal: app still works without persistence
            import logging
            logging.getLogger(__name__).warning(f"DB setup warning: {e}")

    # ── Paper Trades ──────────────────────────────────────────────────────────

    def save_paper_trade(self, trade: Dict[str, Any]) -> int:
        def _run(conn):
            cur = conn.execute(
                """INSERT INTO paper_trades
                   (symbol, trade_type, option_type, strike,
                    entry_time, entry_price, quantity, notes)
                   VALUES (:symbol, :trade_type, :option_type, :strike,
                           :entry_time, :entry_price, :quantity, :notes)""",
                trade,
            )
            return cur.lastrowid
        return self._execute(_run) or 0

    def close_paper_trade(self, trade_id: int, exit_price: float, exit_time: str = None) -> Dict:
        if not exit_time:
            exit_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        def _run(conn):
            row = conn.execute(
                "SELECT * FROM paper_trades WHERE id=?", (trade_id,)
            ).fetchone()
            if not row:
                return {}
            row = dict(row)
            sign = 1 if row["trade_type"] == "BUY" else -1
            pnl  = sign * (exit_price - row["entry_price"]) * row["quantity"]
            conn.execute(
                "UPDATE paper_trades SET exit_time=?, exit_price=?, pnl=?, status='CLOSED' WHERE id=?",
                (exit_time, exit_price, pnl, trade_id),
            )
            row.update({"exit_price": exit_price, "exit_time": exit_time,
                        "pnl": pnl, "status": "CLOSED"})
            return row

        return self._execute(_run) or {}

    def get_open_trades(self) -> List[Dict]:
        def _run(conn):
            rows = conn.execute(
                "SELECT * FROM paper_trades WHERE status='OPEN' ORDER BY entry_time DESC"
            ).fetchall()
            return [dict(r) for r in rows]
        return self._execute(_run) or []

    def get_closed_trades(self, limit: int = 100) -> List[Dict]:
        def _run(conn):
            rows = conn.execute(
                "SELECT * FROM paper_trades WHERE status='CLOSED' ORDER BY exit_time DESC LIMIT ?",
                (limit,),
            ).fetchall()
            return [dict(r) for r in rows]
        return self._execute(_run) or []

    def get_performance_metrics(self) -> Dict:
        def _run(conn):
            trades = [dict(t) for t in
                      conn.execute("SELECT * FROM paper_trades WHERE status='CLOSED'").fetchall()]
            if not trades:
                return {"total_trades": 0, "win_rate": 0.0, "total_pnl": 0.0,
                        "max_drawdown": 0.0, "avg_win": 0.0, "avg_loss": 0.0,
                        "profit_factor": 0.0}

            wins   = [t for t in trades if (t["pnl"] or 0) > 0]
            losses = [t for t in trades if (t["pnl"] or 0) <= 0]
            total_pnl    = sum(t["pnl"] or 0 for t in trades)
            gross_profit = sum(t["pnl"] for t in wins)   if wins   else 0
            gross_loss   = abs(sum(t["pnl"] for t in losses)) if losses else 0

            cumulative, running = [], 0
            for t in sorted(trades, key=lambda x: x["exit_time"] or ""):
                running += t["pnl"] or 0
                cumulative.append(running)
            peak, max_dd = float("-inf"), 0
            for v in cumulative:
                peak  = max(peak, v)
                max_dd = max(max_dd, peak - v)

            return {
                "total_trades":   len(trades),
                "winning_trades": len(wins),
                "losing_trades":  len(losses),
                "win_rate":       round(len(wins) / len(trades) * 100, 2),
                "total_pnl":      round(total_pnl, 2),
                "max_drawdown":   round(max_dd, 2),
                "avg_win":        round(gross_profit / len(wins),   2) if wins   else 0,
                "avg_loss":       round(gross_loss   / len(losses), 2) if losses else 0,
                "profit_factor":  round(gross_profit / gross_loss,  2) if gross_loss > 0 else 0,
            }
        return self._execute(_run) or {}

    # ── Candle Cache ──────────────────────────────────────────────────────────

    def cache_candles(self, symbol: str, interval: str, candles: List[List]):
        def _run(conn):
            conn.executemany(
                """INSERT OR REPLACE INTO candle_cache
                   (symbol, interval, timestamp, open, high, low, close, volume)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                [(symbol, interval, c[0], c[1], c[2], c[3], c[4], c[5])
                 for c in candles],
            )
        try:
            self._execute(_run)
        except Exception:
            pass  # cache write failure is non-fatal

    def get_cached_candles(self, symbol: str, interval: str, limit: int = 200) -> List[Dict]:
        def _run(conn):
            rows = conn.execute(
                """SELECT * FROM candle_cache WHERE symbol=? AND interval=?
                   ORDER BY timestamp DESC LIMIT ?""",
                (symbol, interval, limit),
            ).fetchall()
            return [dict(r) for r in reversed(rows)]
        return self._execute(_run) or []

    # ── Analysis Log ──────────────────────────────────────────────────────────

    def log_analysis(self, symbol: str, data: Dict):
        def _run(conn):
            conn.execute(
                """INSERT INTO analysis_log
                   (symbol, timestamp, rsi, macd, macd_signal,
                    bb_upper, bb_lower, atr, trend, probability, recommendation, raw_data)
                   VALUES (:symbol,:timestamp,:rsi,:macd,:macd_signal,
                           :bb_upper,:bb_lower,:atr,:trend,:probability,:recommendation,:raw_data)""",
                {
                    "symbol":         symbol,
                    "timestamp":      datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "rsi":            data.get("rsi"),
                    "macd":           data.get("macd"),
                    "macd_signal":    data.get("macd_signal"),
                    "bb_upper":       data.get("bb_upper"),
                    "bb_lower":       data.get("bb_lower"),
                    "atr":            data.get("atr"),
                    "trend":          data.get("trend"),
                    "probability":    data.get("probability"),
                    "recommendation": data.get("recommendation"),
                    "raw_data":       json.dumps(data),
                },
            )
        try:
            self._execute(_run)
        except Exception:
            pass  # log failure is non-fatal
