from __future__ import annotations

import json
import asyncio
from fastapi import FastAPI, Form, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

from app.config import settings
from app.exchange.weex_client import WeexClient
from app.strategy.signal_engine import build_signal_snapshot

app = FastAPI(title=settings.app_name)

client = WeexClient(
    api_key=settings.weex_api_key,
    secret_key=settings.weex_secret_key,
    passphrase=settings.weex_passphrase,
)

MANUAL_ORDER_STATE = {
    "symbol": settings.default_symbol,
    "side": settings.default_side,
    "leverage": settings.default_leverage,
    "notional_usdt": settings.default_notional_usdt,
}


# =========================
# UI 渲染
# =========================

def render_positions_table(positions: list[dict]) -> str:
    if not positions:
        return "<tr><td colspan='7'>目前無持倉</td></tr>"

    if "error" in positions[0]:
        return f"<tr><td colspan='7'>持倉讀取失敗：{positions[0]['error']}</td></tr>"

    rows = []
    for p in positions:
        rows.append(f"""
        <tr>
            <td>{p['symbol']}</td>
            <td>{p['side']}</td>
            <td>{p['size']}</td>
            <td>{p['entry_price']}</td>
            <td>{p['mark_price']}</td>
            <td>{p['unrealized_pnl']}</td>
            <td>{p['leverage']}</td>
        </tr>
        """)
    return "".join(rows)


def render_signals_table(signals: list[dict]) -> str:
    if not signals:
        return "<tr><td colspan='10'>目前無訊號</td></tr>"

    rows = []
    for s in signals[:20]:
        rows.append(f"""
        <tr>
            <td>{s['symbol']}</td>
            <td>{s['side']}</td>
            <td>{s['score']}</td>
            <td>{s['price']}</td>
            <td>{s['entry_zone']}</td>
            <td>{s['stop_loss']}</td>
            <td>{s['take_profit_1']}</td>
            <td>{s['take_profit_2']}</td>
            <td>{s['volatility']}</td>
            <td>{s['reasons']}</td>
        </tr>
        """)
    return "".join(rows)


# =========================
# 首頁
# =========================

@app.get("/", response_class=HTMLResponse)
def home():
    account = client.get_account_summary()
    positions = client.get_positions()

    symbols = client.get_top_symbols(settings.top_n_volume)
    prices = client.get_live_prices(symbols)
    signals = build_signal_snapshot(symbols, prices, settings.signal_threshold)

    html = f"""
    <html>
    <head>
        <title>{settings.app_name}</title>
        <style>
            body {{
                background:#0b1220;
                color:white;
                font-family:Arial;
                padding:20px;
            }}
            .card {{
                background:#111827;
                padding:20px;
                margin-bottom:20px;
                border-radius:10px;
            }}
            table {{
                width:100%;
                border-collapse: collapse;
            }}
            td, th {{
                border-bottom:1px solid #333;
                padding:8px;
            }}
        </style>
    </head>
    <body>

    <h1>🚀 {settings.app_name}</h1>

    <div class="card">
        <h2>帳戶</h2>
        <p>總資產: <span id="eq">{account["total_equity"]}</span></p>
        <p>可用: <span id="ab">{account["available_balance"]}</span></p>
        <p>未實現: <span id="up">{account["unrealized_pnl"]}</span></p>
    </div>

    <div class="card">
        <h2>持倉</h2>
        <table>
            <tbody id="positions-body">
                {render_positions_table(positions)}
            </tbody>
        </table>
    </div>

    <div class="card">
        <h2>訊號</h2>
        <table>
            <tbody id="signals-body">
                {render_signals_table(signals)}
            </tbody>
        </table>
    </div>

    <script>
        const protocol = location.protocol === "https:" ? "wss" : "ws";
        const ws = new WebSocket(protocol + "://" + location.host + "/ws/live");

        ws.onmessage = function(event) {{
            const data = JSON.parse(event.data);

            document.getElementById("eq").innerText = data.account.total_equity;
            document.getElementById("ab").innerText = data.account.available_balance;
            document.getElementById("up").innerText = data.account.unrealized_pnl;

            document.getElementById("positions-body").innerHTML = data.positions_html;
            document.getElementById("signals-body").innerHTML = data.signals_html;
        }};
    </script>

    </body>
    </html>
    """

    return HTMLResponse(html)


# =========================
# WebSocket 即時更新
# =========================

@app.websocket("/ws/live")
async def ws_live(websocket: WebSocket):
    await websocket.accept()

    try:
        while True:
            account = client.get_account_summary()
            positions = client.get_positions()

            symbols = client.get_top_symbols(settings.top_n_volume)
            prices = client.get_live_prices(symbols)
            signals = build_signal_snapshot(symbols, prices, settings.signal_threshold)

            await websocket.send_text(json.dumps({
                "account": account,
                "positions_html": render_positions_table(positions),
                "signals_html": render_signals_table(signals)
            }))

            await asyncio.sleep(2)

    except WebSocketDisconnect:
        return
