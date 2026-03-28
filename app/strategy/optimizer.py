from __future__ import annotations

from typing import Any

from app.strategy.storage import load_model, save_model

DEFAULT_WEIGHTS = {
    "trend": 0.35,
    "rsi": 0.20,
    "macd": 0.25,
    "volume": 0.20,
    "volatility_penalty": -0.15,
}


def get_weights() -> dict[str, float]:
    return load_model(DEFAULT_WEIGHTS)


def weighted_score(features: dict[str, float], side: str, weights: dict[str, float]) -> float:
    if side == "long":
        score = (
            features["trend_long"] * weights["trend"]
            + features["rsi_long"] * weights["rsi"]
            + features["macd_long"] * weights["macd"]
            + features["volume_score"] * weights["volume"]
            + features["volatility_penalty"] * weights["volatility_penalty"]
        )
    else:
        score = (
            features["trend_short"] * weights["trend"]
            + features["rsi_short"] * weights["rsi"]
            + features["macd_short"] * weights["macd"]
            + features["volume_score"] * weights["volume"]
            + features["volatility_penalty"] * weights["volatility_penalty"]
        )

    return max(0.0, min(1.0, round(score, 4)))


def optimize_weights_from_results(results: list[dict[str, Any]]) -> dict[str, float]:
    weights = get_weights()
    if not results:
        return weights

    recent = results[-50:]
    wins = sum(1 for r in recent if float(r.get("winrate", 0)) >= 0.5)
    avg_balance = sum(float(r.get("balance", 1000)) for r in recent) / max(len(recent), 1)

    if wins / max(len(recent), 1) >= 0.55:
        weights["trend"] = min(0.50, weights["trend"] + 0.01)
        weights["macd"] = min(0.35, weights["macd"] + 0.01)
        weights["volatility_penalty"] = max(-0.25, weights["volatility_penalty"] - 0.01)
    else:
        weights["rsi"] = min(0.30, weights["rsi"] + 0.01)
        weights["volume"] = min(0.30, weights["volume"] + 0.01)

    if avg_balance < 980:
        weights["volatility_penalty"] = max(-0.30, weights["volatility_penalty"] - 0.02)

    total_positive = weights["trend"] + weights["rsi"] + weights["macd"] + weights["volume"]
    if total_positive > 0:
        scale = 1.0 / total_positive
        weights["trend"] = round(weights["trend"] * scale, 4)
        weights["rsi"] = round(weights["rsi"] * scale, 4)
        weights["macd"] = round(weights["macd"] * scale, 4)
        weights["volume"] = round(weights["volume"] * scale, 4)

    weights["volatility_penalty"] = round(weights["volatility_penalty"], 4)
    save_model(weights)
    return weights
