from __future__ import annotations

import json
import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

from app.config import settings
from app.exchange.weex_client import WeexClient
from app.strategy.ai_engine import score_signal
from app.strategy.backtest import run_backtest

app = FastAPI(title=settings.app_name)

client = WeexClient(
    settings.weex_api_key,
    settings.weex_secret_key,
    settings.weex_passphrase
)


def build_ai_signal_snapshot(symbols: list[str], threshold: float = 0.66):
    longs = []
    shorts = []

    for symbol in symbols:
        try:
            df = client.get_klines(symbol)
            df = client.add_indicators(df)
            if df is None or df.empty:
                continue

            last = df.iloc[-1].to_dict()
            scored = score_signal(last)

            if scored["long_score"] >= threshold and scored["long_score"] > scored["short_score"]:
                longs.append({
                    "symbol": symbol,
                    "score": scored["long_score"],
                    "entry": scored["long_plan"]["entry"],
                    "sl": scored["long_plan"]["stop_loss"],
                    "tp1": scored["long_plan"]["take_profit_1"],
                    "tp2": scored["long_plan"]["take_profit_2"],
                    "reasons": scored["long_reasons"],
                })

            if scored["short_score"] >= threshold and scored["short_score"] > scored["long_score"]:
                shorts.append({
                    "symbol": symbol,
                    "score": scored["short_score"],
                    "entry": scored["short_plan"]["entry"],
                    "sl": scored["short_plan"]["stop_loss"],
                    "tp1": scored["short_plan"]["take_profit_1"],
                    "tp2": scored["short_plan"]["take_profit_2"],
                    "reasons": scored["short_reasons"],
                })

        except Exception:
            continue

    longs.sort(key=lambda x: x["score"], reverse=True)
    shorts.sort(key=lambda x: x["score"], reverse=True)

    return longs[:15], shorts[:15]


def table(data):
    header = """
    <tr>
        <th>Symbol</th>
        <th>AI Score</th>
        <th>Entry</th>
        <th>Stop Loss</th>
        <th>TP1</th>
        <th>TP2</th>
        <th>Reasons</th>
    </tr>
    """

    rows = ""
    for d in data:
        rows += f"""
        <tr>
            <td>{d['symbol']}</td>
            <td>{d['score']}</td>
            <td>{d['entry']}</td>
            <td>{d['sl']}</td>
            <td>{d['tp1']}</td>
            <td>{d['tp2']}</td>
            <td>{d['reasons']}</td>
        </tr>
        """
    return header + rows


@app.get("/", response_class=HTMLResponse)
def home():
    symbols = client.get_top_symbols(70)
    longs, shorts = build_ai_signal_snapshot(symbols, settings.signal_threshold)

    backtest_result = {
        "balance": "-",
        "winrate": "-",
        "trades": "-",
        "wins": "-",
        "losses": "-",
        "max_drawdown": "-"
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
            vertical-align: top;
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

    <h1>🚀 QUANT AI PRO</h1>

    <div class="box">
        <h2>K線圖</h2>
        <div id="tv_chart" style="height:500px;"></div>
    </div>

    <div class="grid">
        <div class="box">
            <h2>AI 回測摘要</h2>
            <div class="stat">期末資金：{backtest_result["balance"]}</div>
            <div class="stat">勝率：{backtest_result["winrate"]}</div>
            <div class="stat">交易次數：{backtest_result["trades"]}</div>
            <div class="stat">Wins：{backtest_result["wins"]}</div>
            <div class="stat">Losses：{backtest_result["losses"]}</div>
            <div class="stat">最大回撤：{backtest_result["max_drawdown"]}</div>
            <div class="muted">示範使用熱門幣歷史 K 線做快速回測。</div>
        </div>

        <div class="box">
            <h2>市場狀態</h2>
            <div class="stat">掃描幣數：70</div>
            <div class="stat">AI Long 候選：{len(longs)}</div>
            <div class="stat">AI Short 候選：{len(shorts)}</div>
            <div class="muted">每 5 秒自動更新一次訊號與 AI 排名。</div>
        </div>
    </div>

    <div class="box">
        <h2>AI LONG</h2>
        <table id="long">
            {table(longs)}
        </table>
    </div>

    <div class="box">
        <h2>AI SHORT</h2>
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
            longs, shorts = build_ai_signal_snapshot(symbols, settings.signal_threshold)

            await websocket.send_text(json.dumps({
                "long": table(longs),
                "short": table(shorts)
            }))

            await asyncio.sleep(5)

    except WebSocketDisconnect:
        return
