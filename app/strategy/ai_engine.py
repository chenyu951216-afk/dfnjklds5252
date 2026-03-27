from __future__ import annotations

from typing import Any
import math


def clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, value))


def safe_float(v: Any, default: float = 0.0) -> float:
    try:
        if v is None:
            return default
        if isinstance(v, float) and math.isnan(v):
            return default
        return float(v)
    except Exception:
        return default


def build_ai_features(last_row: dict[str, Any]) -> dict[str, float]:
    price = safe_float(last_row.get("close"))
    ema20 = safe_float(last_row.get("ema20"))
    ema50 = safe_float(last_row.get("ema50"))
    rsi = safe_float(last_row.get("rsi"))
    macd = safe_float(last_row.get("macd"))
    volume = safe_float(last_row.get("volume"))
    vol_ma = safe_float(last_row.get("vol_ma20"), 1.0)
    atr_pct = safe_float(last_row.get("atr_pct"))

    trend_strength = 0.0
    if price > 0:
        trend_strength = ((price - ema20) / price) * 8 + ((ema20 - ema50) / price) * 12

    rsi_long = clamp((rsi - 50) / 20, 0.0, 1.0)
    rsi_short = clamp((50 - rsi) / 20, 0.0, 1.0)

    macd_long = clamp(macd * 5 + 0.5, 0.0, 1.0)
    macd_short = clamp((-macd) * 5 + 0.5, 0.0, 1.0)

    volume_ratio = volume / max(vol_ma, 1e-9)
    volume_score = clamp((volume_ratio - 0.8) / 0.8, 0.0, 1.0)

    # atr_pct 越大代表波動越大，過高會扣分
    volatility_penalty = clamp((atr_pct - 0.015) / 0.03, 0.0, 1.0)

    trend_long = clamp(0.5 + trend_strength, 0.0, 1.0)
    trend_short = clamp(0.5 - trend_strength, 0.0, 1.0)

    return {
        "trend_long": trend_long,
        "trend_short": trend_short,
        "rsi_long": rsi_long,
        "rsi_short": rsi_short,
        "macd_long": macd_long,
        "macd_short": macd_short,
        "volume_score": volume_score,
        "volatility_penalty": volatility_penalty,
        "atr_pct": atr_pct,
    }


def score_signal(last_row: dict[str, Any]) -> dict[str, Any]:
    f = build_ai_features(last_row)

    long_score = (
        f["trend_long"] * 0.35
        + f["rsi_long"] * 0.20
        + f["macd_long"] * 0.25
        + f["volume_score"] * 0.20
        - f["volatility_penalty"] * 0.15
    )

    short_score = (
        f["trend_short"] * 0.35
        + f["rsi_short"] * 0.20
        + f["macd_short"] * 0.25
        + f["volume_score"] * 0.20
        - f["volatility_penalty"] * 0.15
    )

    long_score = round(clamp(long_score, 0.0, 1.0), 4)
    short_score = round(clamp(short_score, 0.0, 1.0), 4)

    price = safe_float(last_row.get("close"))
    atr_pct = max(safe_float(last_row.get("atr_pct"), 0.015), 0.005)

    long_plan = {
        "entry": round(price, 4),
        "stop_loss": round(price * (1 - max(atr_pct * 1.2, 0.012)), 4),
        "take_profit_1": round(price * (1 + max(atr_pct * 1.4, 0.015)), 4),
        "take_profit_2": round(price * (1 + max(atr_pct * 2.5, 0.03)), 4),
    }

    short_plan = {
        "entry": round(price, 4),
        "stop_loss": round(price * (1 + max(atr_pct * 1.2, 0.012)), 4),
        "take_profit_1": round(price * (1 - max(atr_pct * 1.4, 0.015)), 4),
        "take_profit_2": round(price * (1 - max(atr_pct * 2.5, 0.03)), 4),
    }

    reasons_long = []
    reasons_short = []

    if f["trend_long"] > 0.6:
        reasons_long.append("EMA 多頭")
    if f["trend_short"] > 0.6:
        reasons_short.append("EMA 空頭")

    if f["rsi_long"] > 0.55:
        reasons_long.append("RSI 偏強")
    if f["rsi_short"] > 0.55:
        reasons_short.append("RSI 偏弱")

    if f["macd_long"] > 0.55:
        reasons_long.append("MACD 正向")
    if f["macd_short"] > 0.55:
        reasons_short.append("MACD 負向")

    if f["volume_score"] > 0.55:
        reasons_long.append("量能支撐")
        reasons_short.append("量能支撐")

    if f["volatility_penalty"] > 0.5:
        reasons_long.append("波動偏大")
        reasons_short.append("波動偏大")

    return {
        "long_score": long_score,
        "short_score": short_score,
        "long_plan": long_plan,
        "short_plan": short_plan,
        "long_reasons": ", ".join(reasons_long) if reasons_long else "條件一般",
        "short_reasons": ", ".join(reasons_short) if reasons_short else "條件一般",
        "features": f,
    }
