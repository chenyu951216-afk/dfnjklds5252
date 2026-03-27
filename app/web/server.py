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


def render_positions_table(positions: list[dict]) -> str:
    if not positions:
        return "<tr><td colspan='7'>目前無持倉</td></tr>"

    if "error" in positions[0]:
        return f"<tr><td colspan='7'>持倉讀取失敗：{positions[0]['error']}</td></tr>"

    rows = []
    for p in positions:
        rows.append(
            f"""
            <tr>
              <td>{p['symbol']}</td>
              <td>{p['side']}</td>
              <td>{p['size']}</td>
              <td>{p['entry_price']}</td>
              <td>{p['mark_price']}</td>
              <td>{p['unrealized_pnl']}</td>
              <td>{p['leverage']}</td>
            </tr>
            """
        )
    return "".join(rows)


def render_signals_table(signals: list[dict]) -> str:
    if not signals:
        return "<tr><td colspan='10'>目前無訊號</td></tr>"

    rows = []
    for s in signals[:20]:
        rows.append(
            f"""
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
            """
        )
    return "".join(rows)


def page_shell(body: str, title: str) -> HTMLResponse:
    return HTMLResponse(
        f"""
        <html>
          <head>
            <title>{title}</title>
            <meta name="viewport" content="width=device-width, initial-scale=1.0" />
            <style>
              body {{ font-family: Inter, Arial, sans-serif; background:#0b1220; color:#e5e7eb; margin:0; padding:20px; }}
              .topbar {{ display:flex; justify-content:space-between; align-items:center; margin-bottom:16px; gap:12px; flex-wrap:wrap; }}
              .title {{ font-size:28px; font-weight:700; }}
              .muted {{ color:#94a3b8; }}
              .grid {{ display:grid; grid-template-columns: repeat(auto-fit, minmax(320px,1fr)); gap:16px; }}
              .card {{ background:#111827; border:1px solid #1f2937; border-radius:18px; padding:18px; box-shadow:0 10px 30px rgba(0,0,0,.22); }}
              .kpi {{ display:grid; grid-template-columns: repeat(2, minmax(120px,1fr)); gap:12px; }}
              .kpi-item {{ background:#0f172a; border:1px solid #1e293b; border-radius:14px; padding:12px; }}
              .kpi-label {{ color:#94a3b8; font-size:12px; margin-bottom:6px; }}
              .kpi-value {{ font-size:20px; font-weight:700; }}
              table {{ width:100%; border-collapse: collapse; }}
              th, td {{ padding:10px 8px; border-bottom:1px solid rgba(255,255,255,.06); text-align:left; font-size:13px; vertical-align:top; }}
              th {{ color:#93c5fd; position:sticky; top:0; background:#111827; }}
              input, select, button {{
                width:100%;
                padding:11px 12px;
                margin-top:6px;
                margin-bottom:12px;
                border-radius:12px;
                border:1px solid #334155;
                background:#0f172a;
                color:#e5e7eb;
              }}
              button {{
                cursor:pointer;
                background:#2563eb;
                border:none;
                font-weight:700;
              }}
              .tag {{
                display:inline-block;
                padding:4px 10px;
                border-radius:999px;
                background:#1d4ed8;
                font-size:12px;
                margin-right:6px;
              }}
              .table-wrap {{ overflow:auto; }}
              .live-dot {{
                display:inline-block;
                width:10px;
                height:10px;
                background:#22c55e;
                border-radius:999px;
                margin-right:8px;
              }}
              a {{ color:#93c5fd; }}
              .note {{ color:#facc15; }}
            </style>
          </head>
          <body>{body}</body>
        </html>
        """
    )


@app.get("/", response_class=HTMLResponse)
def home() -> HTMLResponse:
    account = client.get_account_summary()
    positions = client.get_positions()
    symbols = client.get_top_symbols(settings.top_n_volume)
    prices = client.get_live_prices(symbols)
    signals = build_signal_snapshot(symbols, prices, settings.signal_threshold)

    buy_selected = "selected" if MANUAL_ORDER_STATE["side"] == "buy" else ""
    sell_selected = "selected" if MANUAL_ORDER_STATE["side"] == "sell" else ""

    account_error = ""
    if account.get("error"):
        account_error = f"<p style='color:#fca5a5;'>帳戶讀取失敗：{account['error']}</p>"

    body = f"""
    <div class="topbar">
      <div>
        <div class="title">{settings.app_name}</div>
        <div class="muted"><span class="live-dot"></span>Live dashboard / 真實帳戶與持倉讀取</div>
      </div>
      <div>
        <span class="tag">Top 70 Symbols</span>
        <span class="tag">Signal Enhanced</span>
        <span class="tag">WebSocket Refresh</span>
      </div>
    </div>

    <div class="grid">
      <div class="card">
        <h2>帳戶摘要</h2>
        {account_error}
        <div class="kpi">
          <div class="kpi-item"><div class="kpi-label">總權益</div><div class="kpi-value" id="eq">{account["total_equity"]}</div></div>
          <div class="kpi-item"><div class="kpi-label">可用餘額</div><div class="kpi-value" id="ab">{account["available_balance"]}</div></div>
          <div class="kpi-item"><div class="kpi-label">已用保證金</div><div class="kpi-value" id="um">{account["used_margin"]}</div></div>
          <div class="kpi-item"><div class="kpi-label">未實現 PnL</div><div class="kpi-value" id="up">{account["unrealized_pnl"]}</div></div>
          <div class="kpi-item"><div class="kpi-label">已實現 PnL</div><div class="kpi-value" id="rp">{account["realized_pnl"]}</div></div>
        </div>
      </div>

      <div class="card">
        <h2>手動下單預覽</h2>
        <form method="post" action="/preview-order">
          <label>Symbol</label>
          <input name="symbol" value="{MANUAL_ORDER_STATE['symbol']}" />

          <label>Side</label>
          <select name="side">
            <option value="buy" {buy_selected}>buy</option>
            <option value="sell" {sell_selected}>sell</option>
          </select>

          <label>Leverage</label>
          <input type="number" name="leverage" min="1" max="20" value="{MANUAL_ORDER_STATE['leverage']}" />

          <label>Notional (USDT)</label>
          <input type="number" name="notional_usdt" min="1" step="0.01" value="{MANUAL_ORDER_STATE['notional_usdt']}" />

          <button type="submit">預覽交易計畫</button>
        </form>
      </div>
    </div>

    <div class="card" style="margin-top:16px;">
      <h2>目前持倉</h2>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Symbol</th>
              <th>Side</th>
              <th>Size</th>
              <th>Entry</th>
              <th>Mark</th>
              <th>Unrealized PnL</th>
              <th>Leverage</th>
            </tr>
          </thead>
          <tbody id="positions-body">{render_positions_table(positions)}</tbody>
        </table>
      </div>
    </div>

    <div class="card" style="margin-top:16px;">
      <h2>訊號排行（前 20）</h2>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Symbol</th>
              <th>Side</th>
              <th>Score</th>
              <th>Price</th>
              <th>Entry Zone</th>
              <th>SL</th>
              <th>TP1</th>
              <th>TP2</th>
              <th>Volatility</th>
              <th>Reasons</th>
            </tr>
          </thead>
          <tbody id="signals-body">{render_signals_table(signals)}</tbody>
        </table>
      </div>
    </div>

    <script>
      const protocol = location.protocol === "https:" ? "wss" : "ws";
      const ws = new WebSocket(`${protocol}://${location.host}/ws/live`);
      ws.onmessage = (event) => {{
        const data = JSON.parse(event.data);
        document.getElementById("eq").textContent = data.account.total_equity;
        document.getElementById("ab").textContent = data.account.available_balance;
        document.getElementById("um").textContent = data.account.used_margin;
        document.getElementById("up").textContent = data.account.unrealized_pnl;
        document.getElementById("rp").textContent = data.account.realized_pnl;
        document.getElementById("positions-body").innerHTML = data.positions_html;
        document.getElementById("signals-body").innerHTML = data.signals_html;
      }};
    </script>
    """
    return page_shell(body, settings.app_name)


@app.post("/preview-order", response_class=HTMLResponse)
def preview_order(
    symbol: str = Form(...),
    side: str = Form(...),
    leverage: int = Form(...),
    notional_usdt: float = Form(...),
) -> HTMLResponse:
    MANUAL_ORDER_STATE["symbol"] = symbol
    MANUAL_ORDER_STATE["side"] = side
    MANUAL_ORDER_STATE["leverage"] = leverage
    MANUAL_ORDER_STATE["notional_usdt"] = notional_usdt

    preview = client.preview_manual_order(symbol, side, leverage, notional_usdt)

    body = f"""
    <h1>交易計畫預覽</h1>
    <p>Symbol: {preview["symbol"]}</p>
    <p>Side: {preview["side"]}</p>
    <p>Leverage: {preview["leverage"]}</p>
    <p>Notional: {preview["notional_usdt"]} USDT</p>
    <p>Estimated Price: {preview["estimated_price"]}</p>
    <p>Estimated Qty: {preview["estimated_qty"]}</p>
    <p>Entry Zone: {preview["entry_zone"]}</p>
    <p>Stop Loss: {preview["stop_loss"]}</p>
    <p>Take Profit 1: {preview["take_profit_1"]}</p>
    <p>Take Profit 2: {preview["take_profit_2"]}</p>
    <p>{preview["message"]}</p>
    <p><a href="/">返回首頁</a></p>
    """
    return page_shell(body, "交易計畫預覽")


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

            payload = {
                "account": account,
                "positions_html": render_positions_table(positions),
                "signals_html": render_signals_table(signals),
            }
            await websocket.send_text(json.dumps(payload))
            await asyncio.sleep(2)
    except WebSocketDisconnect:
        return
