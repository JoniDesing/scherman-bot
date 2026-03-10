"""
SCHERMAN BOT - Backend
Consulta Open BYMA Data y sirve precios reales al frontend.
"""

import requests
import json
import time
import urllib3
from flask import Flask, jsonify
from flask_cors import CORS
from datetime import datetime

# BYMA usa certificado SSL con cadena incompleta en algunos servidores
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)
CORS(app)

cache = {"data": None, "last_update": 0, "ttl": 300}

ACTIVOS = {
    "cedears": ["SPY", "QQQ", "MELI", "GLD", "AAPL", "MSFT", "GOOGL"],
    "acciones": ["GGAL", "YPFD", "BMA", "TXAR", "ALUA", "TECO2", "PAMP"],
}

BYMA_BASE = "https://open.bymadata.com.ar/vanoms-be-core/rest/api/bymadata/free"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "es-AR,es;q=0.9",
    "Referer": "https://open.bymadata.com.ar/",
    "Origin": "https://open.bymadata.com.ar",
    "Content-Type": "application/json",
}

def fetch_get(endpoint):
    try:
        r = requests.get(f"{BYMA_BASE}/{endpoint}", headers=HEADERS, timeout=15, verify=False)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"Error GET {endpoint}: {e}")
        return None

def fetch_post(endpoint, body=None):
    try:
        r = requests.post(f"{BYMA_BASE}/{endpoint}", headers=HEADERS, json=body or {}, timeout=15, verify=False)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"Error POST {endpoint}: {e}")
        return None

def parse_item(item):
    sym = (item.get("symbol") or item.get("descripcionAbreviada") or "")
    sym = sym.replace(" - CI", "").replace(" - 48hs", "").strip()
    price = float(item.get("trade") or item.get("ultimo") or item.get("settlPrice") or item.get("c") or 0)
    chg = float(item.get("changePercentage") or item.get("variacion") or item.get("pctChange") or 0)
    return sym, price, chg

def get_items(data):
    if not data:
        return []
    if isinstance(data, list):
        return data
    return data.get("data", data.get("content", data.get("result", [])))

def get_cotizaciones():
    now = time.time()
    if cache["data"] and (now - cache["last_update"]) < cache["ttl"]:
        return cache["data"]

    result = {
        "cedears": [], "acciones": [],
        "timestamp": datetime.now().strftime("%H:%M:%S"),
        "fuente": "Open BYMA Data",
        "error": None
    }

    # CEDEARs
    raw = fetch_get("cedears") or fetch_post("cedears", {"excludeZeroPxAndQty": True, "T2": True, "T1": False, "T0": False})
    for item in get_items(raw):
        sym, price, chg = parse_item(item)
        if any(a in sym.upper() for a in ACTIVOS["cedears"]) and price > 0:
            matched = next((a for a in ACTIVOS["cedears"] if a in sym.upper()), sym)
            if not any(x["symbol"] == matched for x in result["cedears"]):
                result["cedears"].append({"symbol": matched, "price": round(price, 2), "change_pct": round(chg, 2)})

    # Acciones
    raw2 = fetch_get("equities") or fetch_post("equities", {"excludeZeroPxAndQty": True, "T2": True, "T1": False, "T0": False})
    for item in get_items(raw2):
        sym, price, chg = parse_item(item)
        if any(a in sym.upper() for a in ACTIVOS["acciones"]) and price > 0:
            matched = next((a for a in ACTIVOS["acciones"] if a in sym.upper()), sym)
            if not any(x["symbol"] == matched for x in result["acciones"]):
                result["acciones"].append({"symbol": matched, "price": round(price, 2), "change_pct": round(chg, 2)})

    # Fallback Yahoo si BYMA no tiene datos
    if not result["cedears"]:
        print("BYMA sin datos, usando Yahoo Finance...")
        result["cedears"] = fetch_yahoo()
        result["fuente"] = "Yahoo Finance (.BA) - BYMA sin datos"

    cache["data"] = result
    cache["last_update"] = time.time()
    print(f"[OK] CEDEARs:{len(result['cedears'])} Acciones:{len(result['acciones'])} Fuente:{result['fuente']}")
    return result

def fetch_yahoo():
    tickers = {"SPY":"SPY.BA","QQQ":"QQQ.BA","MELI":"MELI.BA","GLD":"GLD.BA","AAPL":"AAPL.BA","MSFT":"MSFT.BA"}
    result = []
    for sym, ticker in tickers.items():
        try:
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1d&range=1d"
            r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=8)
            meta = r.json()["chart"]["result"][0]["meta"]
            price = meta.get("regularMarketPrice", 0)
            prev = meta.get("previousClose", price)
            chg = ((price - prev) / prev * 100) if prev else 0
            if price > 0:
                result.append({"symbol": sym, "price": round(price, 2), "change_pct": round(chg, 2)})
                print(f"[Yahoo] {sym}: ${price}")
        except Exception as e:
            print(f"[Yahoo] Error {sym}: {e}")
    return result

def get_bonos():
    bonos_target = ["AL30", "AL35", "GD30", "GD35", "AE38"]
    result = []
    raw = fetch_get("bonds") or fetch_post("publicBonds", {"excludeZeroPxAndQty": True, "T2": True})
    for item in get_items(raw):
        sym, price, chg = parse_item(item)
        if any(b in sym.upper() for b in bonos_target) and price > 0:
            result.append({"symbol": sym, "price": round(price, 2), "change_pct": round(chg, 2)})
    return result

@app.route("/")
def index():
    return jsonify({"status": "ok", "message": "Scherman Bot API", "endpoints": ["/api/cotizaciones", "/api/bonos", "/api/health"]})

@app.route("/api/cotizaciones")
def api_cotizaciones():
    return jsonify(get_cotizaciones())

@app.route("/api/bonos")
def api_bonos():
    return jsonify({"bonos": get_bonos(), "timestamp": datetime.now().strftime("%H:%M:%S")})

@app.route("/api/health")
def health():
    return jsonify({"status": "ok", "cache_age_seconds": int(time.time() - cache["last_update"]) if cache["last_update"] else None, "timestamp": datetime.now().isoformat()})

@app.route("/api/all")
def api_all():
    c = get_cotizaciones()
    return jsonify({**c, "bonos": get_bonos()})

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
