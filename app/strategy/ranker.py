from __future__ import annotations

from typing import Any


def build_winrate_ranking(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}

    for row in results:
        symbol = row.get("symbol", "")
        if not symbol:
            continue
        grouped.setdefault(symbol, []).append(row)

    ranking: list[dict[str, Any]] = []

    for symbol, rows in grouped.items():
        trades = len(rows)
        if trades == 0:
            continue

        avg_winrate = sum(float(r.get("winrate", 0.0)) for r in rows) / trades
        avg_balance = sum(float(r.get("balance", 1000.0)) for r in rows) / trades
        ranking.append(
            {
                "symbol": symbol,
                "trades": trades,
                "avg_winrate": round(avg_winrate, 3),
                "avg_balance": round(avg_balance, 2),
            }
        )

    ranking.sort(key=lambda x: (x["avg_winrate"], x["avg_balance"], x["trades"]), reverse=True)
    return ranking[:20]


def filter_high_probability_signals(
    longs: list[dict[str, Any]],
    shorts: list[dict[str, Any]],
    threshold: float = 0.72,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    long_filtered = [x for x in longs if float(x.get("score", 0)) >= threshold]
    short_filtered = [x for x in shorts if float(x.get("score", 0)) >= threshold]
    return long_filtered, short_filtered
