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

def fetch_byma(endpoint, params=None):
    """Llama a Open BYMA Data con headers correctos."""
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json, text/plain, */*",
        "Referer": "https://open.bymadata.com.ar/",
        "Origin": "https://open.bymadata.com.ar",
    }
    try:
        url = f"{BYMA_BASE}/{endpoint}"
        r = requests.get(url, headers=headers, params=params, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"Error BYMA {endpoint}: {e}")
        return None

def get_cotizaciones():
    """Obtiene cotizaciones de CEDEARs y acciones argentinas."""
    now = time.time()

    # Devolver cache si es reciente
    if cache["data"] and (now - cache["last_update"]) < cache["ttl"]:
        return cache["data"]

    result = {
        "cedears": [],
        "acciones": [],
        "timestamp": datetime.now().strftime("%H:%M:%S"),
        "fuente": "Open BYMA Data (20 min delay)",
        "error": None
    }

    # CEDEARs
    try:
        data = fetch_byma("cedears")
        if data and "data" in data:
            for item in data["data"]:
                sym = item.get("symbol", "").replace(" - CI", "").strip()
                if sym in ACTIVOS["cedears"]:
                    result["cedears"].append({
                        "symbol": sym,
                        "price": item.get("trade", item.get("settlPrice", 0)),
                        "change": item.get("imbalance", 0),
                        "change_pct": item.get("changePercentage", 0),
                        "volume": item.get("quantityBuy", 0),
                        "bid": item.get("bidPrice", 0),
                        "ask": item.get("offerPrice", 0),
                    })
    except Exception as e:
        result["error"] = str(e)

    # Acciones locales (MERVAL)
    try:
        data = fetch_byma("equities")
        if data and "data" in data:
            for item in data["data"]:
                sym = item.get("symbol", "").replace(" - CI", "").strip()
                if sym in ACTIVOS["acciones"]:
                    result["acciones"].append({
                        "symbol": sym,
                        "price": item.get("trade", item.get("settlPrice", 0)),
                        "change": item.get("imbalance", 0),
                        "change_pct": item.get("changePercentage", 0),
                        "volume": item.get("quantityBuy", 0),
                        "bid": item.get("bidPrice", 0),
                        "ask": item.get("offerPrice", 0),
                    })
    except Exception as e:
        if not result["error"]:
            result["error"] = str(e)

    # Guardar en cache
    cache["data"] = result
    cache["last_update"] = time.time()

    return result

def get_bonos():
    """Obtiene cotizaciones de bonos soberanos."""
    try:
        data = fetch_byma("bonds")
        if not data or "data" not in data:
            return []
        bonos_target = ["AL30", "AL35", "GD30", "GD35", "AE38"]
        result = []
        for item in data["data"]:
            sym = item.get("symbol", "").strip()
            if any(b in sym for b in bonos_target):
                result.append({
                    "symbol": sym,
                    "price": item.get("trade", 0),
                    "change_pct": item.get("changePercentage", 0),
                })
        return result
    except Exception as e:
        print(f"Error bonos: {e}")
        return []

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
