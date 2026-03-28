from __future__ import annotations

import json
import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

from app.config import settings
from app.exchange.weex_client import WeexClient
from app.strategy.ai_engine import score_signal
from app.strategy.backtest import run_backtest
from app.strategy.optimizer import get_weights, optimize_weights_from_results, weighted_score
from app.strategy.ranker import build_winrate_ranking, filter_high_probability_signals
from app.strategy.storage import (
    append_jsonl,
    load_backtest_results,
    save_backtest_results,
)

app = FastAPI(title=settings.app_name)

client = WeexClient(
    settings.weex_api_key,
    settings.weex_secret_key,
    settings.weex_passphrase
)


def build_ai_signal_snapshot(symbols: list[str], threshold: float = 0.66):
    longs = []
    shorts = []
    weights = get_weights()

    for symbol in symbols:
        try:
            df = client.get_klines(symbol)
            df = client.add_indicators(df)
            if df is None or df.empty:
                continue

            last = df.iloc[-1].to_dict()
            scored = score_signal(last)

            long_score = weighted_score(scored["features"], "long", weights)
            short_score = weighted_score(scored["features"], "short", weights)

            if long_score >= threshold and long_score > short_score:
                longs.append({
                    "symbol": symbol,
                    "score": round(long_score, 4),
                    "entry": scored["long_plan"]["entry"],
                    "sl": scored["long_plan"]["stop_loss"],
                    "tp1": scored["long_plan"]["take_profit_1"],
                    "tp2": scored["long_plan"]["take_profit_2"],
                    "reasons": scored["long_reasons"],
                })

            if short_score >= threshold and short_score > long_score:
                shorts.append({
                    "symbol": symbol,
                    "score": round(short_score, 4),
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

    return longs[:20], shorts[:20], weights


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


def ranking_table(rows):
    header = """
    <tr>
        <th>Symbol</th>
        <th>Trades</th>
        <th>Avg Winrate</th>
        <th>Avg Balance</th>
    </tr>
    """
    html = ""
    for r in rows:
        html += f"""
        <tr>
            <td>{r['symbol']}</td>
            <td>{r['trades']}</td>
            <td>{r['avg_winrate']}</td>
            <td>{r['avg_balance']}</td>
        </tr>
        """
    return header + html


@app.get("/", response_class=HTMLResponse)
def home():
    symbols = client.get_top_symbols(70)
    longs, shorts, weights = build_ai_signal_snapshot(symbols, settings.signal_threshold)
    longs, shorts = filter_high_probability_signals(longs, shorts, max(settings.signal_threshold, 0.72))

    backtest_result = {
        "balance": "-",
        "winrate": "-",
        "trades": "-",
        "wins": "-",
        "losses": "-",
        "max_drawdown": "-"
    }

    try:
        results = load_backtest_results()

        if symbols:
            fresh_results = []
            for symbol in symbols[:10]:
                try:
                    df = client.get_klines(symbol)
                    df = client.add_indicators(df)
                    result = run_backtest(df)
                    result["symbol"] = symbol
                    fresh_results.append(result)
                except Exception:
                    continue

            if fresh_results:
                save_backtest_results(fresh_results)
                optimize_weights_from_results(fresh_results)
                results = fresh_results

            if results:
                best = sorted(results, key=lambda x: (x.get("winrate", 0), x.get("balance", 0)), reverse=True)[0]
                backtest_result = best

        ranking = build_winrate_ranking(results)

    except Exception:
        ranking = []

    append_jsonl("/data/trade_log.jsonl", {
        "type": "dashboard_snapshot",
        "long_count": len(longs),
        "short_count": len(shorts),
    })

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
        pre {{
            white-space: pre-wrap;
            word-break: break-word;
        }}
        </style>
    </head>

    <body>

    <h1>🚀 QUANT AI PRO+</h1>

    <div class="box">
        <h2>K線圖</h2>
        <div id="tv_chart" style="height:500px;"></div>
    </div>

    <div class="grid">
        <div class="box">
            <h2>AI 回測摘要</h2>
            <div class="stat">最佳幣：{backtest_result.get("symbol", "-")}</div>
            <div class="stat">期末資金：{backtest_result["balance"]}</div>
            <div class="stat">勝率：{backtest_result["winrate"]}</div>
            <div class="stat">交易次數：{backtest_result["trades"]}</div>
            <div class="stat">Wins：{backtest_result["wins"]}</div>
            <div class="stat">Losses：{backtest_result["losses"]}</div>
            <div class="stat">最大回撤：{backtest_result["max_drawdown"]}</div>
        </div>

        <div class="box">
            <h2>AI 權重</h2>
            <pre>{json.dumps(weights, ensure_ascii=False, indent=2)}</pre>
            <div class="muted">權重會根據近期回測結果微調並存到 /data/model.json</div>
        </div>

        <div class="box">
            <h2>市場狀態</h2>
            <div class="stat">掃描幣數：70</div>
            <div class="stat">高勝率 Long：{len(longs)}</div>
            <div class="stat">高勝率 Short：{len(shorts)}</div>
            <div class="muted">僅顯示高於門檻的訊號。</div>
        </div>
    </div>

    <div class="box">
        <h2>勝率排行榜</h2>
        <table id="ranking">
            {ranking_table(ranking)}
        </table>
    </div>

    <div class="box">
        <h2>AI LONG（高勝率）</h2>
        <table id="long">
            {table(longs)}
        </table>
    </div>

    <div class="box">
        <h2>AI SHORT（高勝率）</h2>
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
        document.getElementById("ranking").innerHTML = data.ranking;
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
            longs, shorts, _weights = build_ai_signal_snapshot(symbols, settings.signal_threshold)
            longs, shorts = filter_high_probability_signals(longs, shorts, max(settings.signal_threshold, 0.72))

            ranking = build_winrate_ranking(load_backtest_results())

            await websocket.send_text(json.dumps({
                "long": table(longs),
                "short": table(shorts),
                "ranking": ranking_table(ranking),
            }))

            await asyncio.sleep(5)

    except WebSocketDisconnect:
        return
