from __future__ import annotations

from typing import Any
import random


def build_signal_snapshot(symbols: list[str], threshold: float) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []

    for symbol in symbols:
        seed = sum(ord(c) for c in symbol)
        random.seed(seed)
        trend = random.uniform(-1.0, 1.0)
        momentum = random.uniform(-1.0, 1.0)
        volume = random.uniform(-1.0, 1.0)
        score = round((trend * 0.45 + momentum * 0.35 + volume * 0.20 + 1) / 2, 4)

        if score >= threshold:
            side = "buy" if trend >= 0 else "sell"
            reasons = []
            reasons.append("trend strong" if abs(trend) > 0.45 else "trend neutral")
            reasons.append("momentum positive" if momentum > 0 else "momentum weak")
            reasons.append("volume expansion" if volume > 0.25 else "volume normal")

            out.append(
                {
                    "symbol": symbol,
                    "side": side,
                    "score": score,
                    "trend": round(trend, 4),
                    "momentum": round(momentum, 4),
                    "volume": round(volume, 4),
                    "reasons": ", ".join(reasons),
                }
            )

    out.sort(key=lambda x: x["score"], reverse=True)
    return out
