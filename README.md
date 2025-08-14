# OR Alert (YFinance) — Market Pulse to Discord

Intraday **Market Pulse** bot that posts clean, actionable snapshots to a Discord channel.
It pulls **5‑minute data from Yahoo Finance**, computes an **Opening Range (OR)** reference, basic **RSI**, and
**dynamic “standard deviation” levels** off the OR-low. It also highlights **most-liquid options**
(7–14 day calls, 17–21 day calls/puts, and **0DTE calls for SPY/QQQ**) plus a simple bias tag.

> ✅ Ships with an `.env` file pre-filled to match the current script defaults.
> Update values there instead of editing code.

---

## What it posts

For each ticker:
- **Price** and `% change from OR-low`
- **OR High/Low** (from the first intraday 5‑min bar; see notes below)
- **σ levels**: `−1σ`, `−1.618σ`, `−3.618σ` (derived from the OR range)
- **Volume (session sum)** and **RSI(14)**
- **Insight** (Above OR-high, Between levels, Weak/Oversold, Deep flush) + **Action hint**
- **Options**: most‑liquid by volume for:
    - `7–14D CALL`
    - `17–21D CALL` and `PUT`
    - `0DTE CALL` (SPY/QQQ only)
- **Bias**: “Consider CALL/PUT” when OR/RSI context and liquidity align

## Schedule (PST)
- **06:00** — premarket snapshot
- **Top of the hour** — `07:00` through `13:00`
- **13:30** — postmarket wrap

You can tweak these in `.env` without touching code.

---

## Quick start

```bash
# 1) Create venv (recommended)
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# 2) Install deps
pip install -r requirements.txt

# 3) Configure
cp .env.example .env    # (already provided)
# Edit .env and set your Discord webhook URL and tickers

# 4) Test one-shot (prints + posts once)
python or_alert_yf.py --test

# 5) Run continuously (cron/Task Scheduler/pm2/etc.)
python or_alert_yf.py
```

### Windows Task Scheduler (outline)
- Action: `python` with argument `or_alert_yf.py`
- Start in: repo folder path
- Trigger: At log on (or daily at 5:55 AM PST), run whether user is logged on or not.

---

## Configuration (.env)

```env
TICKERS=SPY,QQQ,TSLA,HOOD,PLTR,MSTR,COIN,ETHE,AMD,NVDA,MSTY,PLTY
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/REPLACE_ME/REPLACE_ME
TIMEZONE_OFFSET=-7
PRE_MARKET_HOUR=6
POST_MARKET_HOUR=13
POST_MARKET_MINUTE=30
HOURLY_RANGE=7,8,9,10,11,12,13
```

- `TICKERS`: Comma‑separated list (upper/lowercase OK)
- `DISCORD_WEBHOOK_URL`: Your Discord **incoming webhook**
- `TIMEZONE_OFFSET`: Local offset vs UTC (PST is `-7` during DST)
- `PRE_MARKET_HOUR`: Pre‑market snapshot hour (24h clock)
- `POST_MARKET_HOUR`/`POST_MARKET_MINUTE`: End‑of‑day post time
- `HOURLY_RANGE`: Hours (comma‑separated) that should post at `:00`

---

## How it works (principles)

1. **Data source**: Intraday 5‑minute bars from Yahoo Finance via `yfinance`.
2. **Opening Range (OR)**: Uses the **first intraday 5‑minute bar** for the day as a proxy.
   - *Note*: For exact “09:30–09:35 ET” OR, you can refine this later by slicing to NYSE session time.
3. **Context levels**:
   - Compute OR **range** = (first bar **High − Low**).
   - Project “σ levels” from OR‑low: `−1σ`, `−1.618σ`, `−3.618σ` (heuristic thresholds).
4. **RSI**: Plain RSI(14) on closing prices to gauge overbought/oversold.
5. **Insights & action tag**: Simple rule‑based text aligned to OR/RSI and “σ level” position
   (e.g., *Above OR‑high → Trim; Deep flush + RSI<30 → Oversold bounce*).
6. **Options picks**:
   - Query option chains and choose the **highest‑volume** contract in buckets:
     `7–14D` CALL, `17–21D` CALL/PUT; and **0DTE CALL** for SPY/QQQ.
   - *Purpose*: Provide a quick liquid contract reference; **not** trade advice.
7. **Posting cadence**: Pre‑market + hourly + post‑market per `.env` schedule.

---

## Notes & caveats

- Yahoo intraday data can be delayed and occasionally sparse outside RTH.
- OR proxy uses the first bar of the day; if you require the *exact* NY open window,
  adjust the code to slice 09:30–09:35 ET.
- Option chains may be limited/late; “most‑liquid” selection is a heuristic.
- Always validate signals against your own risk management.

---

## Files

- `or_alert_yf.py` – **env-driven** main bot (this repo’s default)
- `or_alert_yf_original.py` – original script you provided (unchanged)
- `.env` – pre-filled with your current config
- `.env.example` – template for other environments
- `requirements.txt`, `.gitignore`, `LICENSE`, `DESCRIPTION_350.txt`

---

## License

MIT