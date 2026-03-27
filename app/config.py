from __future__ import annotations

import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    app_name: str = os.getenv("APP_NAME", "WEEX Safe Manual Trader")
    port: int = int(os.getenv("PORT", "8080"))
    tz: str = os.getenv("TZ", "Asia/Taipei")

    weex_api_key: str = os.getenv("WEEX_API_KEY", "")
    weex_secret_key: str = os.getenv("WEEX_SECRET_KEY", "")
    weex_passphrase: str = os.getenv("WEEX_PASSPHRASE", "")

    default_symbol: str = os.getenv("DEFAULT_SYMBOL", "BTCUSDT")
    default_side: str = os.getenv("DEFAULT_SIDE", "buy")
    default_leverage: int = int(os.getenv("DEFAULT_LEVERAGE", "3"))
    default_notional_usdt: float = float(os.getenv("DEFAULT_NOTIONAL_USDT", "50"))

    top_n_volume: int = int(os.getenv("TOP_N_VOLUME", "70"))
    signal_threshold: float = float(os.getenv("SIGNAL_THRESHOLD", "0.65"))


settings = Settings()
