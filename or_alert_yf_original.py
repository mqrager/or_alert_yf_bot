from __future__ import annotations

import datetime as dt
import sys
import time
import warnings
from typing import List, Optional

import numpy as np
import pandas as pd
import requests
import yfinance as yf

warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning)

TICKERS: List[str] = [
    "SPY", "QQQ", "TSLA", "HOOD", "PLTR", "MSTR", "COIN", "ETHE","AMD","NVDA","MSTY","PLTY"
]
TIMEZONE_OFFSET = -7  # PST

DISCORD_WEBHOOK_URL = (
    "https://discord.com/api/webhooks/1402143718554992650/3pPPFXpZ_Yl22Pi9W046wub6ZpjiH13oVk7QdZIG3lKIIYGnInLxOC2VxlgknBmgv7h2"
)

MAX_DISCORD_LEN = 1900
PRE_MARKET_HOUR = 6
POST_MARKET_TIME = (13, 30)
HOURLY_RANGE = range(7, 14)

def send_discord(msg: str) -> None:
    for start in range(0, len(msg), MAX_DISCORD_LEN):
        chunk = msg[start : start + MAX_DISCORD_LEN]
        try:
            requests.post(DISCORD_WEBHOOK_URL, json={"content": chunk}, timeout=10)
        except Exception as exc:
            print("Discord error:", exc)

def get_today_5m(ticker: str) -> pd.DataFrame:
    now = dt.datetime.now(dt.timezone.utc)
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    return yf.download(
        ticker,
        start=start,
        end=start + dt.timedelta(days=1),
        interval="5m",
        progress=False,
        auto_adjust=False,
    )

def rsi(series: pd.Series, period: int = 14) -> float:
    delta = series.diff()
    up = delta.clip(lower=0)
    down = -delta.clip(upper=0)
    roll_up = up.rolling(period).mean()
    roll_down = down.rolling(period).mean()
    rs = roll_up / roll_down.replace(0, np.nan)
    return float((100 - 100 / (1 + rs)).iloc[-1])

def insight(px: float, hi: float, lo: float, s1: float, s2: float, s3: float) -> str:
    if px > hi:
        return "⬆️ Above OR-high (trend)"
    if px > lo:
        return "↔️ Between OR levels"
    if px <= s3:
        return "🛑 Deep flush"
    if px <= s2:
        return "⚠️ Oversold"
    if px <= s1:
        return "🔻 Weak"
    return "Testing OR-low"

def action_tag(ins_txt: str, rsi_val: float) -> str:
    if "Above OR-high" in ins_txt and rsi_val > 70:
        return "Trim / Take profit 🟠"
    if "Deep flush" in ins_txt and rsi_val < 30:
        return "Oversold bounce 🟢"
    if "Oversold" in ins_txt and rsi_val < 35:
        return "Watch for reversal 🟡"
    if "Weak" in ins_txt and rsi_val < 45:
        return "Tighten stops 🔴"
    return "Hold ⚪"

def most_liquid_option(ticker: yf.Ticker, dte_min: int, dte_max: int, opt_type: str) -> Optional[str]:
    today = dt.datetime.utcnow().date()
    try:
        dates = ticker.options
    except Exception:
        return None
    valid = [d for d in dates if dte_min <= (dt.datetime.strptime(d, "%Y-%m-%d").date() - today).days <= dte_max]
    if not valid:
        return None
    exp = min(valid)
    try:
        chain = ticker.option_chain(exp)
    except Exception:
        return None
    tbl = chain.calls if opt_type == "call" else chain.puts
    if tbl.empty:
        return None
    row = tbl.sort_values("volume", ascending=False).iloc[0]
    side = "C" if opt_type == "call" else "P"
    return f"{side} {row['strike']:.0f} {exp[5:]} Vol {int(row['volume'])}"

def build_snapshot() -> str:
    blocks: List[str] = []

    for t in TICKERS:
        df = get_today_5m(t)
        if df.empty or len(df) < 20:
            blocks.append(f"{t}: insufficient intraday data")
            continue

        hi, lo = float(df["High"].iloc[0]), float(df["Low"].iloc[0])
        rng = hi - lo
        s1, s2, s3 = lo - 1.0 * rng, lo - 1.618 * rng, lo - 3.618 * rng
        px = float(df["Close"].iloc[-1])
        pct = (px - lo) / lo * 100
        vol = int(df["Volume"].sum())
        r = rsi(df["Close"], 14)
        ins = insight(px, hi, lo, s1, s2, s3)
        act = action_tag(ins, r)

        tk = yf.Ticker(t)
        call_short = most_liquid_option(tk, 7, 14, "call") or "None"
        call_swing = most_liquid_option(tk, 17, 21, "call") or "None"
        put_swing = most_liquid_option(tk, 17, 21, "put") or "None"
        call_0dte = most_liquid_option(tk, 0, 0, "call") if t in {"SPY", "QQQ"} else None

        bias = "N/A"
        if "Above OR-high" in ins and r > 55 and call_short != "None":
            bias = f"Consider CALL → {call_short}"
        elif ("Weak" in ins or "Oversold" in ins or "Deep flush" in ins) and put_swing != "None":
            bias = f"Consider PUT  → {put_swing}"

        opts = [f"7-14D: {call_short}", f"17-21D: {call_swing} / {put_swing}"]
        if call_0dte:
            opts.append(f"0DTE: {call_0dte}")

        block = (
            f"{t}\n"
            f"  Price   : {px:.2f} (Δ {pct:+.2f}%)\n"
            f"  OR H/L  : {hi:.2f} / {lo:.2f}\n"
            f"  σ lvls  : −1σ {s1:.2f} | −1.618σ {s2:.2f} | −3.618σ {s3:.2f}\n"
            f"  Vol /RSI: {vol:,} | {r:.1f}\n"
            f"  Insight : {ins} → {act}\n"
            f"  Options : {' | '.join(opts)}\n"
            f"  Bias    : {bias}"
        )
        blocks.append(block)

    now_local = dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=TIMEZONE_OFFSET)
    payload = "\n".join([
        "```",
        f"Market Pulse – {now_local:%Y-%m-%d %H:%M PST}",
        "",
        *blocks,
        "```",
    ])
    return payload

def should_send(now: dt.datetime, last_key: str) -> bool:
    hour, minute = now.hour, now.minute
    key = f"{hour:02d}:{minute:02d}"

    if key == last_key:
        return False

    if hour == PRE_MARKET_HOUR and minute == 0:
        return True
    if hour in HOURLY_RANGE and minute == 0:
        return True
    if (hour, minute) == POST_MARKET_TIME:
        return True
    return False

if __name__ == "__main__":
    TEST_MODE = len(sys.argv) > 1 and sys.argv[1] == "--test"

    if TEST_MODE:
        snap = build_snapshot()
        print(snap)
        send_discord(snap)
        sys.exit()

    last_key_sent = ""

    while True:
        now_local = dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=TIMEZONE_OFFSET)

        if should_send(now_local, last_key_sent):
            last_key_sent = f"{now_local.hour:02d}:{now_local.minute:02d}"
            snap = build_snapshot()
            print(snap)
            send_discord(snap)
        else:
            print(f"{now_local:%H:%M} – waiting…", end="\r", flush=True)

        time_to_next_min = 60 - now_local.second
        time.sleep(max(time_to_next_min, 1))
