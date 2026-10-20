# Quotex Signals Pro — starter project

Mobile-first signal dashboard with a Python backend, real OHLC data via Twelve Data, technical indicators, and a timeframe-aligned countdown.

## Important
- This is a **signals/education dashboard**, not an official Quotex product and not an auto-trader.
- No win rate or profit is guaranteed.
- The Twelve Data feed may differ from Quotex OTC prices. OTC markets may not be available from public market-data providers.
- Never put API keys, Quotex passwords, or SSIDs in frontend files or public GitHub.
- Start with demo/paper testing. This project does not place trades.

## Run locally / on a Python host
1. Install Python 3.10+.
2. Copy `.env.example` to `.env` and add your Twelve Data API key.
3. Install requirements: `pip install -r requirements.txt`
4. Start: `python app.py`
5. Open `http://localhost:8000`

## Deploy
Deploy the whole folder to a Python web host that supports persistent environment variables. Set `TWELVE_DATA_API_KEY` in the host's private environment settings. Do not commit `.env`.

## Current scope
- Real OHLC candles from Twelve Data for supported regular forex symbols
- EMA 9 / EMA 21, RSI 14, and momentum-based explanation
- CALL / PUT / WAIT with a rule-based confidence score (not a probability of winning)
- Timeframe selection and expiry countdown
- Clear data-source / stale-data warnings
- No automatic trading and no claims of 90% accuracy


## Update note
The signal display refreshes every 0.5 seconds from the latest received candles. External price data is requested every 15 seconds to reduce API usage; actual price update frequency depends on the provider and plan. The website does not fabricate ticks.
