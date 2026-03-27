from __future__ import annotations
import httpx
import pandas as pd


class WeexClient:

    def __init__(self, api_key, secret_key, passphrase):
        self.api_key = api_key

    # 🔥 取得 Top 幣
    def get_top_symbols(self, limit=50):
        url = "https://api.binance.com/api/v3/ticker/24hr"
        data = httpx.get(url).json()

        usdt_pairs = [d for d in data if "USDT" in d["symbol"]]
        sorted_pairs = sorted(usdt_pairs, key=lambda x: float(x["quoteVolume"]), reverse=True)

        return [p["symbol"] for p in sorted_pairs[:limit]]

    # 🔥 真實價格
    def get_live_prices(self, symbols):
        prices = {}
        for s in symbols:
            try:
                url = f"https://api.binance.com/api/v3/ticker/price?symbol={s}"
                prices[s] = float(httpx.get(url).json()["price"])
            except:
                prices[s] = 0
        return prices

    # 🔥 K線
    def get_klines(self, symbol):
        url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=5m&limit=100"
        data = httpx.get(url).json()

        df = pd.DataFrame(data, columns=[
            "time","open","high","low","close","volume",
            "_","_","_","_","_","_"
        ])

        df["close"] = df["close"].astype(float)
        return df

    # 🔥 指標
    def add_indicators(self, df):

        df["ema20"] = df["close"].ewm(span=20).mean()
        df["ema50"] = df["close"].ewm(span=50).mean()

        # RSI
        delta = df["close"].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        df["rsi"] = 100 - (100 / (1 + rs))

        # MACD
        ema12 = df["close"].ewm(span=12).mean()
        ema26 = df["close"].ewm(span=26).mean()
        df["macd"] = ema12 - ema26

        return df
