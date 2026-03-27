from __future__ import annotations

from fastapi import FastAPI, Form
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
        return "<tr><td colspan='6'>目前無訊號</td></tr>"

    rows = []
    for s in signals[:20]:
        rows.append(
            f"""
            <tr>
              <td>{s['symbol']}</td>
              <td>{s['side']}</td>
              <td>{s['score']}</td>
              <td>{s['trend']}</td>
              <td>{s['momentum']}</td>
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
              body {{ font-family: Arial, sans-serif; background:#0f172a; color:#e2e8f0; margin:0; padding:24px; }}
              .grid {{ display:grid; grid-template-columns: repeat(auto-fit, minmax(320px,1fr)); gap:16px; }}
              .card {{ background:#1e293b; border-radius:16px; padding:16px; box-shadow:0 6px 16px rgba(0,0,0,.2); }}
              table {{ width:100%; border-collapse: collapse; }}
              th, td {{ padding:8px; border-bottom:1px solid rgba(255,255,255,.08); text-align:left; font-size:14px; }}
              input, select, button {{ width:100%; padding:10px; margin-top:6px; margin-bottom:12px; border-radius:10px; border:1px solid #475569; }}
              button {{ cursor:pointer; }}
              .muted {{ color:#94a3b8; }}
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
    signals = build_signal_snapshot(symbols, settings.signal_threshold)

    buy_selected = "selected" if MANUAL_ORDER_STATE["side"] == "buy" else ""
    sell_selected = "selected" if MANUAL_ORDER_STATE["side"] == "sell" else ""

    account_error = ""
    if account.get("error"):
        account_error = f"<p style='color:#fca5a5;'>帳戶讀取失敗：{account['error']}</p>"

    body = f"""
    <h1>{settings.app_name}</h1>
    <p class="muted">真實帳戶 / 持倉讀取 + 訊號監控 + 手動預覽</p>

    <div class="grid">
      <div class="card">
        <h2>帳戶摘要</h2>
        {account_error}
        <p>總權益：{account["total_equity"]}</p>
        <p>可用餘額：{account["available_balance"]}</p>
        <p>已用保證金：{account["used_margin"]}</p>
        <p>未實現 PnL：{account["unrealized_pnl"]}</p>
        <p>已實現 PnL：{account["realized_pnl"]}</p>
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

          <button type="submit">預覽</button>
        </form>
      </div>
    </div>

    <div class="card" style="margin-top:16px;">
      <h2>目前持倉</h2>
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
        <tbody>{render_positions_table(positions)}</tbody>
      </table>
    </div>

    <div class="card" style="margin-top:16px;">
      <h2>前 70 幣訊號排行（顯示前 20）</h2>
      <table>
        <thead>
          <tr>
            <th>Symbol</th>
            <th>Side</th>
            <th>Score</th>
            <th>Trend</th>
            <th>Momentum</th>
            <th>Reasons</th>
          </tr>
        </thead>
        <tbody>{render_signals_table(signals)}</tbody>
      </table>
    </div>
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
    <h1>下單預覽</h1>
    <p>Symbol: {preview["symbol"]}</p>
    <p>Side: {preview["side"]}</p>
    <p>Leverage: {preview["leverage"]}</p>
    <p>Notional: {preview["notional_usdt"]} USDT</p>
    <p>Estimated Price: {preview["estimated_price"]}</p>
    <p>Estimated Qty: {preview["estimated_qty"]}</p>

    <h2>示範型計畫</h2>
    <p>進場區間：{preview["entry_zone"]}</p>
    <p>止損：{preview["stop_loss"]}</p>
    <p>第一止盈：{preview["take_profit_1"]}</p>
    <p>第二止盈：{preview["take_profit_2"]}</p>
    <p class="note">{preview["message"]}</p>

    <p><a href="/">返回首頁</a></p>
    """
    return page_shell(body, "下單預覽")
