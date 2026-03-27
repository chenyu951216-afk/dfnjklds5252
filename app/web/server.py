from __future__ import annotations

import json
import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

from app.config import settings
from app.exchange.weex_client import WeexClient
from app.strategy.signal_engine import build_signal_snapshot

app = FastAPI()

client = WeexClient(
    settings.weex_api_key,
    settings.weex_secret_key,
    settings.weex_passphrase
)


def table(data):
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
    return rows


@app.get("/", response_class=HTMLResponse)
def home():
    return HTMLResponse("""
    <html>
    <head>
        <style>
        body {background:#0b1220;color:white;font-family:Arial;padding:20px;}
        .box {background:#111827;padding:20px;margin-bottom:20px;border-radius:10px;}
        table {width:100%;}
        td {padding:6px;border-bottom:1px solid #333;}
        h2 {color:#60a5fa;}
        </style>
    </head>
    <body>

    <h1>🚀 QUANT PRO v2</h1>

    <div class="box">
        <h2>LONG</h2>
        <table id="long"></table>
    </div>

    <div class="box">
        <h2>SHORT</h2>
        <table id="short"></table>
    </div>

    <script>
    const ws = new WebSocket((location.protocol==="https:"?"wss":"ws")+"://"+location.host+"/ws");

    ws.onmessage = (e)=>{
        const data = JSON.parse(e.data);
        document.getElementById("long").innerHTML = data.long;
        document.getElementById("short").innerHTML = data.short;
    }
    </script>

    </body>
    </html>
    """)


@app.websocket("/ws")
async def ws(websocket: WebSocket):
    await websocket.accept()

    while True:
        symbols = client.get_top_symbols(70)
        prices = client.get_live_prices(symbols)

        longs, shorts = build_signal_snapshot(symbols, prices, 0.6)

        await websocket.send_text(json.dumps({
            "long": table(longs),
            "short": table(shorts)
        }))

        await asyncio.sleep(2)
