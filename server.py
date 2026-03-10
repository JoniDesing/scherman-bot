"""
SCHERMAN BOT - Backend v3
Usa Yahoo Finance (.BA) para todos los datos - 100% funcional
"""

import requests
import time
import urllib3
from flask import Flask, jsonify
from flask_cors import CORS
from datetime import datetime

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)
CORS(app)

cache = {"data": None, "last_update": 0, "ttl": 300}

# Tickers Yahoo Finance con sufijo .BA (mercado argentino en pesos)
CEDEARS_YF = {
    "SPY":   "SPY.BA",
    "QQQ":   "QQQ.BA",
    "MELI":  "MELI.BA",
    "GLD":   "GLD.BA",
    "AAPL":  "AAPL.BA",
    "MSFT":  "MSFT.BA",
    "GOOGL": "GOOGL.BA",
    "AMZN":  "AMZN.BA",
    "NVDA":  "NVDA.BA",
}

ACCIONES_YF = {
    "GGAL":  "GGAL.BA",
    "YPFD":  "YPFD.BA",
    "BMA":   "BMA.BA",
    "TXAR":  "TXAR.BA",
    "ALUA":  "ALUA.BA",
    "TECO2": "TECO2.BA",
    "PAMP":  "PAMP.BA",
    "LOMA":  "LOMA.BA",
    "SUPV":  "SUPV.BA",
}

BONOS_YF = {
    "AL30":  "AL30.BA",
    "AL35":  "AL35.BA",
    "GD30":  "GD30.BA",
    "GD35":  "GD35.BA",
    "AE38":  "AE38.BA",
}

YF_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json",
}

def fetch_yf(ticker):
    """Obtiene precio y variacion de Yahoo Finance para un ticker."""
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1d&range=2d"
        r = requests.get(url, headers=YF_HEADERS, timeout=10)
        data = r.json()
        result = data["chart"]["result"][0]
        meta = result["meta"]
        price = float(meta.get("regularMarketPrice") or 0)
        prev  = float(meta.get("previousClose") or meta.get("chartPreviousClose") or price)
        change_pct = round(((price - prev) / prev * 100), 2) if prev and prev != 0 else 0.0
        return round(price, 2), change_pct
    except Exception as e:
        print(f"[YF] Error {ticker}: {e}")
        return 0, 0.0

def fetch_batch(tickers_dict):
    """Descarga todos los tickers de un dict en paralelo usando threads."""
    from concurrent.futures import ThreadPoolExecutor, as_completed
    results = []
    def fetch_one(sym, ticker):
        price, chg = fetch_yf(ticker)
        return sym, price, chg
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(fetch_one, sym, ticker): sym for sym, ticker in tickers_dict.items()}
        for future in as_completed(futures):
            sym, price, chg = future.result()
            if price > 0:
                results.append({"symbol": sym, "price": price, "change_pct": chg})
                print(f"[YF] {sym}: ${price:,.2f} ({chg:+.2f}%)")
    return sorted(results, key=lambda x: x["symbol"])

def get_cotizaciones():
    now = time.time()
    if cache["data"] and (now - cache["last_update"]) < cache["ttl"]:
        return cache["data"]

    print("[START] Fetching market data from Yahoo Finance...")
    cedears  = fetch_batch(CEDEARS_YF)
    acciones = fetch_batch(ACCIONES_YF)

    result = {
        "cedears":   cedears,
        "acciones":  acciones,
        "timestamp": datetime.now().strftime("%H:%M:%S"),
        "fuente":    "Yahoo Finance · Precios en ARS (.BA) · Delay ~15min",
        "error":     None,
    }

    cache["data"] = result
    cache["last_update"] = time.time()
    print(f"[DONE] CEDEARs:{len(cedears)} Acciones:{len(acciones)}")
    return result

def get_bonos():
    bonos = fetch_batch(BONOS_YF)
    return bonos

# ============================================================
# ENDPOINTS
# ============================================================

@app.route("/")
def index():
    return jsonify({
        "status": "ok",
        "message": "Scherman Bot API v3 - Yahoo Finance",
        "endpoints": ["/api/cotizaciones", "/api/bonos", "/api/health", "/api/all"]
    })

@app.route("/api/cotizaciones")
def api_cotizaciones():
    return jsonify(get_cotizaciones())

@app.route("/api/bonos")
def api_bonos():
    return jsonify({
        "bonos": get_bonos(),
        "timestamp": datetime.now().strftime("%H:%M:%S")
    })

@app.route("/api/health")
def health():
    return jsonify({
        "status": "ok",
        "cache_age_seconds": int(time.time() - cache["last_update"]) if cache["last_update"] else None,
        "timestamp": datetime.now().isoformat()
    })

@app.route("/api/all")
def api_all():
    c = get_cotizaciones()
    return jsonify({**c, "bonos": get_bonos()})

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
