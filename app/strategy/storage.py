from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any

DATA_DIR = "/data"
MODEL_PATH = os.path.join(DATA_DIR, "model.json")
BACKTEST_PATH = os.path.join(DATA_DIR, "backtest_results.json")
TRADE_LOG_PATH = os.path.join(DATA_DIR, "trade_log.jsonl")


def ensure_data_dir() -> None:
    os.makedirs(DATA_DIR, exist_ok=True)


def load_json(path: str, default: Any):
    ensure_data_dir()
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def save_json(path: str, data: Any) -> None:
    ensure_data_dir()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def append_jsonl(path: str, data: dict[str, Any]) -> None:
    ensure_data_dir()
    payload = {
        "ts": datetime.utcnow().isoformat(),
        **data,
    }
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")


def load_model(default: dict[str, float]) -> dict[str, float]:
    data = load_json(MODEL_PATH, {})
    if not isinstance(data, dict):
        return default
    merged = default.copy()
    for k, v in data.items():
        try:
            merged[k] = float(v)
        except Exception:
            pass
    return merged


def save_model(weights: dict[str, float]) -> None:
    save_json(MODEL_PATH, weights)


def load_backtest_results() -> list[dict[str, Any]]:
    data = load_json(BACKTEST_PATH, [])
    return data if isinstance(data, list) else []


def save_backtest_results(results: list[dict[str, Any]]) -> None:
    save_json(BACKTEST_PATH, results)
