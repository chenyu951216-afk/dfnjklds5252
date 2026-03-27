from __future__ import annotations

from typing import Any
import random


def build_signal_snapshot(symbols: list[str], prices: dict[str, float], threshold: float) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []

    for symbol in symbols:
        seed = sum(ord(c) for c in symbol)
        random.seed(seed)

        trend = random.uniform(-1.0, 1.0)
        momentum = random.uniform(-1.0, 1.0)
        volume = random.uniform(-1.0, 1.0)
        volatility = random.uniform(0.0, 1.0)

        score = round(
            (trend * 0.38 + momentum * 0.32 + volume * 0.18 + (1 - volatility) * 0.12 + 1) / 2,
            4,
        )

        if score >= threshold:
            side = "buy" if trend >= 0 else "sell"
            price = float(prices.get(symbol, 0.0))

            if side == "buy":
                stop_loss = round(price * 0.985, 4)
                tp1 = round(price * 1.015, 4)
                tp2 = round(price * 1.03, 4)
            else:
                stop_loss = round(price * 1.015, 4)
                tp1 = round(price * 0.985, 4)
                tp2 = round(price * 0.97, 4)

            reasons = []
            reasons.append("trend strong" if abs(trend) > 0.45 else "trend neutral")
            reasons.append("momentum positive" if momentum > 0 else "momentum weak")
            reasons.append("volume expansion" if volume > 0.25 else "volume normal")
            reasons.append("volatility controlled" if volatility < 0.55 else "volatility elevated")

            out.append(
                {
                    "symbol": symbol,
                    "side": side,
                    "score": score,
                    "price": round(price, 4),
                    "trend": round(trend, 4),
                    "momentum": round(momentum, 4),
                    "volume": round(volume, 4),
                    "volatility": round(volatility, 4),
                    "entry_zone": f"{round(price * 0.998, 4)} - {round(price * 1.002, 4)}",
                    "stop_loss": stop_loss,
                    "take_profit_1": tp1,
                    "take_profit_2": tp2,
                    "reasons": ", ".join(reasons),
                }
            )

    out.sort(key=lambda x: x["score"], reverse=True)
    return out
