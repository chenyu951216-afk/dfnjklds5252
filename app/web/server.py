from __future__ import annotations

import json
import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

from app.config import settings
from app.exchange.weex_client import WeexClient
from app.strategy.signal_engine import build_signal_snapshot
from app.strategy.backtest import run_backtest

app = FastAPI(title=settings.app_name)

client = WeexClient(
    settings.weex_api_key,
    settings.weex_secret_key,
    settings.weex_passphrase
)


def table(data):
    header = """
    <tr>
        <th>Symbol</th>
        <th>Entry Price</th>
        <th>Stop Loss</th>
        <th>TP1</th>
        <th>TP2</th>
    </tr>
    """

    rows = ""
    for d in data:
        rows += f"""
        <tr>
            <td>{d['symbol']}</td>
            <td>{d['entry']}</td>
            <td>{d['sl']}</td>
            <td>{d['tp1']}</td>
            <td>{d['tp2']}</td>
        </tr>
        """
    return header + rows


@app.get("/", response_class=HTMLResponse)
def home():
    symbols = client.get_top_symbols(70)
    prices = client.get_live_prices(symbols)
    longs, shorts = build_signal_snapshot(symbols, prices, 0.6)

    backtest_result = {
        "balance": "-",
        "winrate": "-",
        "trades": "-"
    }

    try:
        if symbols:
            df = client.get_klines(symbols[0])
            df = client.add_indicators(df)
            backtest_result = run_backtest(df)
    except Exception:
        pass

    html = f"""
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{settings.app_name}</title>
        <script src="https://s3.tradingview.com/tv.js"></script>
        <style>
        body {{
            background:#0b1220;
            color:white;
            font-family:Arial;
            padding:20px;
            margin:0;
        }}
        .box {{
            background:#111827;
            padding:20px;
            margin-bottom:20px;
            border-radius:12px;
            box-shadow:0 6px 20px rgba(0,0,0,0.25);
        }}
        table {{
            width:100%;
            border-collapse: collapse;
        }}
        th, td {{
            padding:8px;
            border-bottom:1px solid #333;
            text-align:left;
            font-size:14px;
        }}
        h1 {{
            color:#fff;
            margin-bottom:20px;
        }}
        h2 {{
            color:#60a5fa;
            margin-top:0;
        }}
        .grid {{
            display:grid;
            grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
            gap:16px;
        }}
        .stat {{
            font-size:18px;
            margin:8px 0;
        }}
        .muted {{
            color:#94a3b8;
            font-size:13px;
        }}
        </style>
    </head>

    <body>

    <h1>🚀 QUANT PRO v3</h1>

    <div class="box">
        <h2>K線圖</h2>
        <div id="tv_chart" style="height:500px;"></div>
    </div>

    <div class="grid">
        <div class="box">
            <h2>回測摘要</h2>
            <div class="stat">期末資金：{backtest_result["balance"]}</div>
            <div class="stat">勝率：{backtest_result["winrate"]}</div>
            <div class="stat">交易次數：{backtest_result["trades"]}</div>
            <div class="muted">目前示範使用第一個熱門幣做快速回測。</div>
        </div>

        <div class="box">
            <h2>市場狀態</h2>
            <div class="stat">掃描幣數：70</div>
            <div class="stat">Long 候選：{len(longs)}</div>
            <div class="stat">Short 候選：{len(shorts)}</div>
            <div class="muted">每 2 秒自動更新一次訊號。</div>
        </div>
    </div>

    <div class="box">
        <h2>LONG</h2>
        <table id="long">
            {table(longs)}
        </table>
    </div>

    <div class="box">
        <h2>SHORT</h2>
        <table id="short">
            {table(shorts)}
        </table>
    </div>

    <script>
    new TradingView.widget({{
        "container_id": "tv_chart",
        "symbol": "BINANCE:BTCUSDT",
        "interval": "5",
        "theme": "dark",
        "style": "1",
        "locale": "zh_TW",
        "toolbar_bg": "#0b1220",
        "enable_publishing": false,
        "hide_top_toolbar": false,
        "hide_legend": false,
        "save_image": false,
        "studies": ["RSI@tv-basicstudies", "MACD@tv-basicstudies"]
    }});

    const ws = new WebSocket((location.protocol === "https:" ? "wss" : "ws") + "://" + location.host + "/ws");

    ws.onmessage = (e) => {{
        const data = JSON.parse(e.data);
        document.getElementById("long").innerHTML = data.long;
        document.getElementById("short").innerHTML = data.short;
    }};
    </script>

    </body>
    </html>
    """

    return HTMLResponse(html)


@app.websocket("/ws")
async def ws(websocket: WebSocket):
    await websocket.accept()

    try:
        while True:
            symbols = client.get_top_symbols(70)
            prices = client.get_live_prices(symbols)
            longs, shorts = build_signal_snapshot(symbols, prices, 0.6)

            await websocket.send_text(json.dumps({
                "long": table(longs),
                "short": table(shorts)
            }))

            await asyncio.sleep(2)

    except WebSocketDisconnect:
        return
