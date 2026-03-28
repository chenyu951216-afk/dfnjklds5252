from __future__ import annotations

from typing import Any
import time
import hmac
import hashlib
import base64

import httpx
import pandas as pd


class WeexClient:
    BASE_URL = "https://api.weex.com"
    BINANCE_BASE = "https://api.binance.com"

    def __init__(self, api_key: str, secret_key: str, passphrase: str) -> None:
        self.api_key = api_key or ""
        self.secret_key = secret_key or ""
        self.passphrase = passphrase or ""

    def _sign(self, timestamp: str, method: str, path: str, body: str = "") -> str:
        message = f"{timestamp}{method}{path}{body}"
        digest = hmac.new(
            self.secret_key.encode(),
            message.encode(),
            hashlib.sha256,
        ).digest()
        return base64.b64encode(digest).decode()

    def _headers(self, method: str, path: str, body: str = "") -> dict[str, str]:
        timestamp = str(int(time.time() * 1000))
        sign = self._sign(timestamp, method, path, body)
        return {
            "Content-Type": "application/json",
            "ACCESS-KEY": self.api_key,
            "ACCESS-SIGN": sign,
            "ACCESS-TIMESTAMP": timestamp,
            "ACCESS-PASSPHRASE": self.passphrase,
        }

    def get_account_summary(self) -> dict[str, Any]:
        if not self.api_key or not self.secret_key or not self.passphrase:
            return {
                "total_equity": 0.0,
                "available_balance": 0.0,
                "used_margin": 0.0,
                "unrealized_pnl": 0.0,
                "realized_pnl": 0.0,
                "error": "WEEX API credentials not set",
            }

        path = "/capi/v2/account/getAccounts"
        url = self.BASE_URL + path
        try:
            r = httpx.get(url, headers=self._headers("GET", path), timeout=12)
            data = r.json()
            account = (data.get("data") or [{}])[0]
            return {
                "total_equity": float(account.get("equity", 0)),
                "available_balance": float(account.get("available", 0)),
                "used_margin": float(account.get("usedMargin", 0)),
                "unrealized_pnl": float(account.get("unrealizedProfit", 0)),
                "realized_pnl": float(account.get("realizedProfit", 0)),
                "error": "",
            }
        except Exception as e:
            return {
                "total_equity": 0.0,
                "available_balance": 0.0,
                "used_margin": 0.0,
                "unrealized_pnl": 0.0,
                "realized_pnl": 0.0,
                "error": str(e),
            }

    def get_positions(self) -> list[dict[str, Any]]:
        if not self.api_key or not self.secret_key or not self.passphrase:
            return [{"error": "WEEX API credentials not set"}]

        path = "/capi/v2/position/getAllPosition"
        url = self.BASE_URL + path
        try:
            r = httpx.get(url, headers=self._headers("GET", path), timeout=12)
            data = r.json()
            out: list[dict[str, Any]] = []
            for p in data.get("data", []):
                out.append(
                    {
                        "symbol": p.get("symbol", ""),
                        "side": p.get("holdSide", ""),
                        "size": float(p.get("total", 0)),
                        "entry_price": float(p.get("openPrice", 0)),
                        "mark_price": float(p.get("markPrice", 0)),
                        "unrealized_pnl": float(p.get("unrealizedProfit", 0)),
                        "leverage": int(float(p.get("leverage", 1) or 1)),
                    }
                )
            return out
        except Exception as e:
            return [{"error": str(e)}]

    def get_top_symbols(self, limit: int = 70) -> list[str]:
        url = f"{self.BINANCE_BASE}/api/v3/ticker/24hr"
        data = httpx.get(url, timeout=15).json()
        usdt_pairs = [d for d in data if d["symbol"].endswith("USDT")]
        sorted_pairs = sorted(usdt_pairs, key=lambda x: float(x["quoteVolume"]), reverse=True)
        return [p["symbol"] for p in sorted_pairs[:limit]]

    def get_live_prices(self, symbols: list[str]) -> dict[str, float]:
        prices: dict[str, float] = {}
        for s in symbols:
            try:
                url = f"{self.BINANCE_BASE}/api/v3/ticker/price?symbol={s}"
                prices[s] = float(httpx.get(url, timeout=10).json()["price"])
            except Exception:
                prices[s] = 0.0
        return prices

    def get_klines(self, symbol: str, interval: str = "5m", limit: int = 200) -> pd.DataFrame:
        url = f"{self.BINANCE_BASE}/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
        data = httpx.get(url, timeout=15).json()

        df = pd.DataFrame(
            data,
            columns=[
                "open_time", "open", "high", "low", "close", "volume",
                "close_time", "quote_asset_volume", "number_of_trades",
                "taker_buy_base", "taker_buy_quote", "ignore",
            ],
        )

        for col in ["open", "high", "low", "close", "volume"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")

        return df[["open", "high", "low", "close", "volume"]].dropna().reset_index(drop=True)

    def add_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        out = df.copy()

        out["ema20"] = out["close"].ewm(span=20, adjust=False).mean()
        out["ema50"] = out["close"].ewm(span=50, adjust=False).mean()

        delta = out["close"].diff()
        gain = delta.where(delta > 0, 0.0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0.0)).rolling(14).mean()
        rs = gain / loss.replace(0, 1e-9)
        out["rsi"] = 100 - (100 / (1 + rs))

        ema12 = out["close"].ewm(span=12, adjust=False).mean()
        ema26 = out["close"].ewm(span=26, adjust=False).mean()
        out["macd"] = ema12 - ema26
        out["macd_signal"] = out["macd"].ewm(span=9, adjust=False).mean()
        out["macd_hist"] = out["macd"] - out["macd_signal"]

        out["vol_ma20"] = out["volume"].rolling(20).mean()

        tr1 = out["high"] - out["low"]
        tr2 = (out["high"] - out["close"].shift()).abs()
        tr3 = (out["low"] - out["close"].shift()).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        out["atr"] = tr.rolling(14).mean()
        out["atr_pct"] = out["atr"] / out["close"]

        return out.dropna().reset_index(drop=True)
