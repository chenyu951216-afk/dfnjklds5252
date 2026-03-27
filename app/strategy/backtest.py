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
