import pandas as pd


def run_backtest(df):
    balance = 1000
    win = 0
    lose = 0

    for i in range(50, len(df)):
        price = df["close"].iloc[i]

        ema20 = df["ema20"].iloc[i]
        ema50 = df["ema50"].iloc[i]
        rsi = df["rsi"].iloc[i]

        # 多單策略
        if price > ema20 > ema50 and rsi > 55:
            tp = price * 1.02
            sl = price * 0.98

            future = df["close"].iloc[i+1:i+10]

            if future.max() >= tp:
                balance *= 1.02
                win += 1
            elif future.min() <= sl:
                balance *= 0.98
                lose += 1

    total = win + lose
    winrate = win / total if total > 0 else 0

    return {
        "balance": round(balance, 2),
        "winrate": round(winrate, 3),
        "trades": total
    }
    from __future__ import annotations

from typing import Any
import pandas as pd

from app.strategy.ai_engine import score_signal


def run_backtest(df: pd.DataFrame) -> dict[str, Any]:
    if df is None or df.empty or len(df) < 80:
        return {
            "balance": 1000.0,
            "winrate": 0.0,
            "trades": 0,
            "wins": 0,
            "losses": 0,
            "max_drawdown": 0.0,
        }

    balance = 1000.0
    peak = balance
    max_drawdown = 0.0
    wins = 0
    losses = 0
    trades = 0

    # 每次用單位風險模擬
    risk_fraction = 0.01

    records = df.to_dict("records")

    for i in range(60, len(records) - 12):
        row = records[i]
        result = score_signal(row)

        side = None
        plan = None

        if result["long_score"] >= 0.66 and result["long_score"] > result["short_score"]:
            side = "long"
            plan = result["long_plan"]
        elif result["short_score"] >= 0.66 and result["short_score"] > result["long_score"]:
            side = "short"
            plan = result["short_plan"]

        if not side or not plan:
            continue

        trades += 1
        entry = float(plan["entry"])
        sl = float(plan["stop_loss"])
        tp1 = float(plan["take_profit_1"])
        tp2 = float(plan["take_profit_2"])

        future = records[i + 1 : i + 11]
        trade_closed = False

        for candle in future:
            high = float(candle.get("high", candle.get("close", entry)))
            low = float(candle.get("low", candle.get("close", entry)))

            if side == "long":
                if low <= sl:
                    balance *= (1 - risk_fraction)
                    losses += 1
                    trade_closed = True
                    break
                if high >= tp2:
                    balance *= (1 + risk_fraction * 2.0)
                    wins += 1
                    trade_closed = True
                    break
                if high >= tp1:
                    balance *= (1 + risk_fraction)
                    wins += 1
                    trade_closed = True
                    break

            if side == "short":
                if high >= sl:
                    balance *= (1 - risk_fraction)
                    losses += 1
                    trade_closed = True
                    break
                if low <= tp2:
                    balance *= (1 + risk_fraction * 2.0)
                    wins += 1
                    trade_closed = True
                    break
                if low <= tp1:
                    balance *= (1 + risk_fraction)
                    wins += 1
                    trade_closed = True
                    break

        if not trade_closed:
            # 沒打到 SL/TP，就看最後收盤方向
            last_close = float(future[-1].get("close", entry))
            if side == "long":
                if last_close > entry:
                    balance *= (1 + risk_fraction * 0.5)
                    wins += 1
                else:
                    balance *= (1 - risk_fraction * 0.5)
                    losses += 1
            else:
                if last_close < entry:
                    balance *= (1 + risk_fraction * 0.5)
                    wins += 1
                else:
                    balance *= (1 - risk_fraction * 0.5)
                    losses += 1

        if balance > peak:
            peak = balance
        dd = (peak - balance) / peak if peak > 0 else 0
        if dd > max_drawdown:
            max_drawdown = dd

    total = wins + losses
    winrate = wins / total if total > 0 else 0.0

    return {
        "balance": round(balance, 2),
        "winrate": round(winrate, 3),
        "trades": trades,
        "wins": wins,
        "losses": losses,
        "max_drawdown": round(max_drawdown, 3),
    }
