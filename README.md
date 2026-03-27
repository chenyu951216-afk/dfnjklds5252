# WEEX Safe Manual Trader

這是最終安全版：

- 真實帳戶讀取
- 真實持倉讀取
- 前 70 幣訊號排行
- 網頁手動下單預覽
- 顯示示範型進場區 / 止損 / 止盈
- GitHub / Zeabur 可部署

## 執行

```bash
python -m venv .venv
```

Windows：

```bash
.venv\Scripts\activate
```

安裝：

```bash
pip install -r requirements.txt
```

建立環境檔：

```bash
copy .env.example .env
```

啟動：

```bash
uvicorn app.web.server:app --reload --port 8080
```

打開：

```text
http://127.0.0.1:8080
```
