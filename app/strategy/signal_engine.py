from __future__ import annotations
from typing import Any
import random


def build_signal_snapshot(symbols, prices, threshold):

    longs = []
    shorts = []

    for symbol in symbols:
        seed = sum(ord(c) for c in symbol)
        random.seed(seed)

        trend = random.uniform(-1, 1)
        momentum = random.uniform(-1, 1)
        volume = random.uniform(-1, 1)

        score = (trend * 0.5 + momentum * 0.3 + volume * 0.2 + 1) / 2

        price = prices.get(symbol, 0)

        if price == 0:
            continue

        entry_low = round(price * 0.998, 4)
        entry_high = round(price * 1.002, 4)

        if trend > 0:
            sl = round(price * 0.985, 4)
            tp1 = round(price * 1.015, 4)
            tp2 = round(price * 1.03, 4)

            longs.append({
                "symbol": symbol,
                "score": round(score, 3),
                "entry": f"{entry_low} - {entry_high}",
                "sl": sl,
                "tp1": tp1,
                "tp2": tp2
            })

        else:
            sl = round(price * 1.015, 4)
            tp1 = round(price * 0.985, 4)
            tp2 = round(price * 0.97, 4)

            shorts.append({
                "symbol": symbol,
                "score": round(score, 3),
                "entry": f"{entry_low} - {entry_high}",
                "sl": sl,
                "tp1": tp1,
                "tp2": tp2
            })

    longs.sort(key=lambda x: x["score"], reverse=True)
    shorts.sort(key=lambda x: x["score"], reverse=True)

    return longs[:15], shorts[:15]
