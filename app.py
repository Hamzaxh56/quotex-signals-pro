import os, time, math
from datetime import datetime, timezone
from flask import Flask, jsonify, request, send_from_directory
import requests
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__, static_folder="static")
API_KEY = os.getenv("TWELVE_DATA_API_KEY", "").strip()
PORT = int(os.getenv("PORT", "8000"))
SYMBOLS = {
    "EUR/USD": "EUR/USD", "GBP/USD": "GBP/USD", "USD/JPY": "USD/JPY",
    "AUD/USD": "AUD/USD", "USD/CAD": "USD/CAD", "USD/CHF": "USD/CHF",
    "NZD/USD": "NZD/USD"
}
INTERVALS = {"1m":"1min", "5m":"5min", "15m":"15min", "30m":"30min", "1h":"1h", "4h":"4h", "1d":"1day"}
CACHE = {}
CACHE_SECONDS = 20

def ema(values, period):
    if not values: return []
    alpha = 2 / (period + 1)
    out = [values[0]]
    for value in values[1:]:
        out.append(alpha * value + (1-alpha) * out[-1])
    return out

def rsi(values, period=14):
    if len(values) < period + 1: return None
    gains, losses = [], []
    for i in range(1, len(values)):
        d = values[i] - values[i-1]
        gains.append(max(d, 0)); losses.append(max(-d, 0))
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    for i in range(period, len(gains)):
        avg_gain = (avg_gain*(period-1)+gains[i])/period
        avg_loss = (avg_loss*(period-1)+losses[i])/period
    if avg_loss == 0: return 100.0
    return 100 - (100 / (1 + avg_gain/avg_loss))

def analyse(candles):
    closes = [c["close"] for c in candles]
    if len(closes) < 30:
        return {"signal":"WAIT","score":0,"rsi":None,"reason":"Not enough candles to analyze safely."}
    e9, e21 = ema(closes, 9), ema(closes, 21)
    rv = rsi(closes)
    delta = closes[-1] - closes[-4]
    votes = (1 if e9[-1] > e21[-1] else -1) + (1 if delta > 0 else -1)
    # RSI acts as a filter, not a guarantee.
    if rv is not None and rv >= 70: votes = min(votes, 0)
    if rv is not None and rv <= 30: votes = max(votes, 0)
    signal = "CALL" if votes == 2 else "PUT" if votes == -2 else "WAIT"
    score = 0 if signal == "WAIT" else 55 + (10 if abs(e9[-1]-e21[-1]) > abs(closes[-1])*0.00005 else 0)
    if rv is not None and 40 < rv < 60: score = max(0, score-5)
    if signal == "CALL":
        reason = "EMA 9 is above EMA 21 and recent momentum is positive."
    elif signal == "PUT":
        reason = "EMA 9 is below EMA 21 and recent momentum is negative."
    else:
        reason = "Trend and momentum are mixed, or RSI is stretched. Waiting is safer than forcing a trade."
    if rv is not None:
        reason += f" RSI(14) is {rv:.1f}."
    return {"signal":signal,"score":score,"rsi":round(rv,1) if rv is not None else None,"ema9":round(e9[-1],6),"ema21":round(e21[-1],6),"reason":reason}

@app.get("/")
def index():
    return send_from_directory("static", "index.html")

@app.get("/api/health")
def health():
    return jsonify({"ok":True,"provider":"Twelve Data","api_key_configured":bool(API_KEY),"time_utc":datetime.now(timezone.utc).isoformat()})

@app.get("/api/market")
def market():
    symbol = request.args.get("symbol", "EUR/USD")
    tf = request.args.get("tf", "1m")
    if symbol not in SYMBOLS or tf not in INTERVALS:
        return jsonify({"error":"Unsupported symbol or timeframe."}), 400
    if not API_KEY:
        return jsonify({"error":"Backend API key is not configured. Add TWELVE_DATA_API_KEY to the server's private environment settings."}), 503
    cache_key = (symbol, tf)
    now = time.time()
    if cache_key in CACHE and now-CACHE[cache_key][0] < CACHE_SECONDS:
        return jsonify(CACHE[cache_key][1])
    try:
        response = requests.get("https://api.twelvedata.com/time_series", params={
            "symbol": SYMBOLS[symbol], "interval": INTERVALS[tf],
            "outputsize": 120, "apikey": API_KEY, "format":"JSON"
        }, timeout=12)
        data = response.json()
        if response.status_code != 200 or "values" not in data:
            msg = data.get("message", "Market-data provider did not return candles.")
            return jsonify({"error":msg,"provider":"Twelve Data"}), 502
        candles = []
        for v in reversed(data["values"]):
            candles.append({
                "time": v["datetime"],
                "open": float(v["open"]), "high": float(v["high"]),
                "low": float(v["low"]), "close": float(v["close"])
            })
        result = {
            "symbol":symbol, "timeframe":tf, "candles":candles,
            "analysis":analyse(candles), "provider":"Twelve Data",
            "updated_at":datetime.now(timezone.utc).isoformat(),
            "note":"Regular-market feed; it may not match Quotex OTC prices."
        }
        CACHE[cache_key] = (now, result)
        return jsonify(result)
    except requests.RequestException:
        return jsonify({"error":"Could not reach market-data provider. Please retry."}), 502

@app.get("/<path:path>")
def static_files(path):
    return send_from_directory("static", path)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)
