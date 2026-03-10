"""
SCHERMAN BOT - Backend
Consulta Open BYMA Data y sirve precios reales al frontend.
"""

import requests
import json
import time
from flask import Flask, jsonify
from flask_cors import CORS
from datetime import datetime

app = Flask(__name__)
CORS(app)  # Permite que el frontend en GitHub Pages acceda

# Cache para no martillar la API de BYMA en cada request
cache = {
    "data": None,
    "last_update": 0,
    "ttl": 300  # actualizar cada 5 minutos
}

# Los activos que queremos monitorear
ACTIVOS = {
    "cedears": ["SPY", "QQQ", "MELI", "GLD", "AAPL", "MSFT", "GOOGL"],
    "acciones": ["GGAL", "YPFD", "BMA", "TXAR", "ALUA", "TECO2", "PAMP"],
}

BYMA_BASE = "https://open.bymadata.com.ar/vanoms-be-core/rest/api/bymadata/free"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "es-AR,es;q=0.9",
    "Referer": "https://open.bymadata.com.ar/",
    "Origin": "https://open.bymadata.com.ar",
    "Content-Type": "application/json",
}

def fetch_byma_post(endpoint, body=None):
    """POST a Open BYMA Data (algunos endpoints requieren POST)."""
    try:
        url = f"{BYMA_BASE}/{endpoint}"
        r = requests.post(url, headers=HEADERS, json=body or {}, timeout=15)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"Error BYMA POST {endpoint}: {e}")
        return None

def fetch_byma_get(endpoint, params=None):
    """GET a Open BYMA Data."""
    try:
        url = f"{BYMA_BASE}/{endpoint}"
        r = requests.get(url, headers=HEADERS, params=params, timeout=15)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"Error BYMA GET {endpoint}: {e}")
        return None

def parse_item(item):
    """Extrae campos clave de un item BYMA (maneja distintas estructuras)."""
    sym = (item.get("symbol") or item.get("descripcionAbreviada") or "").replace(" - CI", "").replace(" - 48hs", "").strip()
    price = (item.get("trade") or item.get("ultimo") or item.get("settlPrice") or item.get("c") or 0)
    change_pct = (item.get("changePercentage") or item.get("variacion") or item.get("pctChange") or 0)
    try:
        price = float(price)
        change_pct = float(change_pct)
    except:
        price = 0
        change_pct = 0
    return sym, price, change_pct

def get_cotizaciones():
    """Obtiene cotizaciones de CEDEARs y acciones argentinas."""
    now = time.time()
    if cache["data"] and (now - cache["last_update"]) < cache["ttl"]:
        return cache["data"]

    result = {
        "cedears": [],
        "acciones": [],
        "timestamp": datetime.now().strftime("%H:%M:%S"),
        "fuente": "Open BYMA Data (20 min delay)",
        "error": None
    }

    # --- CEDEARs ---
    # Intentar múltiples endpoints
    cedear_data = None
    for endpoint in ["cedears", "cedears?limit=100", "leadingCedears"]:
        cedear_data = fetch_byma_get(endpoint)
        if cedear_data:
            break
    if not cedear_data:
        cedear_data = fetch_byma_post("cedears", {"excludeZeroPxAndQty": True, "T2": True, "T1": False, "T0": False})

    if cedear_data:
        items = cedear_data if isinstance(cedear_data, list) else cedear_data.get("data", cedear_data.get("content", []))
        for item in (items or []):
            sym, price, change_pct = parse_item(item)
            clean = sym.upper()
            if any(a in clean for a in ACTIVOS["cedears"]) and price > 0:
                matched = next((a for a in ACTIVOS["cedears"] if a in clean), clean)
                if not any(x["symbol"] == matched for x in result["cedears"]):
                    result["cedears"].append({
                        "symbol": matched,
                        "price": round(price, 2),
                        "change_pct": round(change_pct, 2),
                    })

    # --- Acciones MERVAL ---
    accion_data = None
    for endpoint in ["equities", "leadingEquities", "bluechips"]:
        accion_data = fetch_byma_get(endpoint)
        if accion_data:
            break
    if not accion_data:
        accion_data = fetch_byma_post("equities", {"excludeZeroPxAndQty": True, "T2": True, "T1": False, "T0": False})

    if accion_data:
        items = accion_data if isinstance(accion_data, list) else accion_data.get("data", accion_data.get("content", []))
        for item in (items or []):
            sym, price, change_pct = parse_item(item)
            clean = sym.upper()
            if any(a in clean for a in ACTIVOS["acciones"]) and price > 0:
                matched = next((a for a in ACTIVOS["acciones"] if a in clean), clean)
                if not any(x["symbol"] == matched for x in result["acciones"]):
                    result["acciones"].append({
                        "symbol": matched,
                        "price": round(price, 2),
                        "change_pct": round(change_pct, 2),
                    })

    # Si BYMA no tiene datos (fuera de horario), usar datos de cierre previo de Yahoo Finance
    if not result["cedears"]:
        result["cedears"] = fetch_yahoo_fallback()

    cache["data"] = result
    cache["last_update"] = time.time()
    print(f"[BYMA] CEDEARs: {len(result['cedears'])} | Acciones: {len(result['acciones'])}")
    return result

def fetch_yahoo_fallback():
    """Fallback: Yahoo Finance para CEDEARs cuando BYMA no tiene datos (fuera de horario)."""
    # Tickers en Yahoo Finance con sufijo .BA para mercado argentino
    tickers_ba = {
        "SPY": "SPY.BA", "QQQ": "QQQ.BA", "MELI": "MELI.BA",
        "GLD": "GLD.BA", "AAPL": "AAPL.BA", "MSFT": "MSFT.BA",
    }
    result = []
    for sym, ticker in tickers_ba.items():
        try:
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1d&range=1d"
            r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=8)
            data = r.json()
            meta = data["chart"]["result"][0]["meta"]
            price = meta.get("regularMarketPrice", 0)
            prev  = meta.get("previousClose", price)
            change_pct = ((price - prev) / prev * 100) if prev else 0
            if price > 0:
                result.append({
                    "symbol": sym,
                    "price": round(price, 2),
                    "change_pct": round(change_pct, 2),
                })
        except Exception as e:
            print(f"Yahoo fallback error {sym}: {e}")
    return result

def get_bonos():
    """Obtiene cotizaciones de bonos soberanos."""
    bonos_target = ["AL30", "AL35", "GD30", "GD35", "AE38"]
    result = []
    try:
        data = fetch_byma_get("bonds") or fetch_byma_post("publicBonds", {"excludeZeroPxAndQty": True, "T2": True})
        if data:
            items = data if isinstance(data, list) else data.get("data", data.get("content", []))
            for item in (items or []):
                sym, price, change_pct = parse_item(item)
                if any(b in sym.upper() for b in bonos_target) and price > 0:
                    result.append({
                        "symbol": sym,
                        "price": round(price, 2),
                        "change_pct": round(change_pct, 2),
                    })
    except Exception as e:
        print(f"Error bonos: {e}")
    return result

# ============================================================
# ENDPOINTS
# ============================================================

@app.route("/")
def index():
    return jsonify({
        "status": "ok",
        "message": "Scherman Bot API corriendo",
        "endpoints": ["/api/cotizaciones", "/api/bonos", "/api/health"]
    })

@app.route("/api/cotizaciones")
def api_cotizaciones():
    data = get_cotizaciones()
    return jsonify(data)

@app.route("/api/bonos")
def api_bonos():
    data = get_bonos()
    return jsonify({"bonos": data, "timestamp": datetime.now().strftime("%H:%M:%S")})

@app.route("/api/health")
def health():
    return jsonify({
        "status": "ok",
        "cache_age_seconds": int(time.time() - cache["last_update"]) if cache["last_update"] else None,
        "timestamp": datetime.now().isoformat()
    })

@app.route("/api/all")
def api_all():
    cotizaciones = get_cotizaciones()
    bonos = get_bonos()
    return jsonify({
        **cotizaciones,
        "bonos": bonos
    })

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
