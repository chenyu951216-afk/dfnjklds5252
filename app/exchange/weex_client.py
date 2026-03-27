from __future__ import annotations

from typing import Any
import random
import time
import hmac
import hashlib
import base64
import httpx


class WeexClient:
    """
    安全版：
    - 真實讀帳戶 / 持倉
    - 市場清單與幣價用示意資料
    - 下單只預覽，不送真單
    """

    BASE_URL = "https://api.weex.com"

    def __init__(self, api_key: str, secret_key: str, passphrase: str) -> None:
        self.api_key = api_key
        self.secret_key = secret_key
        self.passphrase = passphrase

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
        path = "/capi/v2/account/getAccounts"
        url = self.BASE_URL + path
        try:
            r = httpx.get(url, headers=self._headers("GET", path), timeout=10)
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
        path = "/capi/v2/position/getAllPosition"
        url = self.BASE_URL + path
        try:
            r = httpx.get(url, headers=self._headers("GET", path), timeout=10)
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
        bases = [
            "BTCUSDT","ETHUSDT","SOLUSDT","XRPUSDT","DOGEUSDT","BNBUSDT","ADAUSDT","TRXUSDT","AVAXUSDT","LINKUSDT",
            "LTCUSDT","SUIUSDT","DOTUSDT","BCHUSDT","NEARUSDT","APTUSDT","ARBUSDT","OPUSDT","ETCUSDT","UNIUSDT",
            "MATICUSDT","HBARUSDT","ATOMUSDT","PEPEUSDT","WIFUSDT","TIAUSDT","INJUSDT","SEIUSDT","FILUSDT","AAVEUSDT",
            "TAOUSDT","TONUSDT","ICPUSDT","VETUSDT","ALGOUSDT","RUNEUSDT","JUPUSDT","MKRUSDT","ENAUSDT","ONDOUSDT",
            "FETUSDT","RENDERUSDT","IMXUSDT","FLOWUSDT","SANDUSDT","GALAUSDT","XLMUSDT","EOSUSDT","KASUSDT","XMRUSDT",
            "PYTHUSDT","STXUSDT","WLDUSDT","CRVUSDT","PENDLEUSDT","JTOUSDT","BLURUSDT","DYDXUSDT","ARUSDT","ZKUSDT",
            "LDOUSDT","KAVAUSDT","EGLDUSDT","THETAUSDT","ORDIUSDT","BOMEUSDT","NOTUSDT","AEVOUSDT","MEMEUSDT","COMPUSDT"
        ]
        return bases[:limit]

    def get_last_price(self, symbol: str) -> float:
        seed = sum(ord(c) for c in symbol)
        random.seed(seed)
        return round(random.uniform(10, 70000), 4)

    def get_live_prices(self, symbols: list[str]) -> dict[str, float]:
        return {s: self.get_last_price(s) for s in symbols}

    def preview_manual_order(
        self,
        symbol: str,
        side: str,
        leverage: int,
        notional_usdt: float,
    ) -> dict[str, Any]:
        price = max(self.get_last_price(symbol), 0.01)
        est_qty = round(notional_usdt / price, 8)

        if side == "buy":
            stop_loss = round(price * 0.985, 4)
            take_profit_1 = round(price * 1.015, 4)
            take_profit_2 = round(price * 1.03, 4)
        else:
            stop_loss = round(price * 1.015, 4)
            take_profit_1 = round(price * 0.985, 4)
            take_profit_2 = round(price * 0.97, 4)

        return {
            "symbol": symbol,
            "side": side,
            "leverage": leverage,
            "notional_usdt": notional_usdt,
            "estimated_price": price,
            "estimated_qty": est_qty,
            "entry_zone": f"{round(price * 0.998, 4)} - {round(price * 1.002, 4)}",
            "stop_loss": stop_loss,
            "take_profit_1": take_profit_1,
            "take_profit_2": take_profit_2,
            "status": "preview_only",
            "message": "這是示範型風控預覽，不是實盤送單建議。",
        }
