from app.exchange.weex_client import WeexClient

client = WeexClient("", "", "")

def build_signal_snapshot(symbols, prices, threshold):

    longs = []
    shorts = []

    for symbol in symbols:

        df = client.get_klines(symbol)
        df = client.add_indicators(df)

        last = df.iloc[-1]

        price = last["close"]
        ema20 = last["ema20"]
        ema50 = last["ema50"]
        rsi = last["rsi"]
        macd = last["macd"]

        # 🔵 做多條件
        if price > ema20 > ema50 and rsi > 55 and macd > 0:

            longs.append({
                "symbol": symbol,
                "entry": round(price, 4),
                "sl": round(price * 0.98, 4),
                "tp1": round(price * 1.02, 4),
                "tp2": round(price * 1.04, 4),
            })

        # 🔴 做空條件
        if price < ema20 < ema50 and rsi < 45 and macd < 0:

            shorts.append({
                "symbol": symbol,
                "entry": round(price, 4),
                "sl": round(price * 1.02, 4),
                "tp1": round(price * 0.98, 4),
                "tp2": round(price * 0.96, 4),
            })

    return longs[:10], shorts[:10]
