# app/infra/detectors/tasas.py
from datetime import datetime
from typing import Dict, Any, Optional
import requests
import logging

logger = logging.getLogger(__name__)

_TASAS_CACHE: Dict[str, Any] = {
    "tasas": None,
    "timestamp": None,
    "timeout_minutes": 30,
}


def obtener_tasas_cambio() -> Optional[Dict[str, float]]:
    """Obtiene tasas desde BHD con cache de 30 minutos."""
    global _TASAS_CACHE

    # -----------------------------
    # 1. Usar cache si aún es válido
    # -----------------------------
    if (
        _TASAS_CACHE["tasas"] is not None
        and _TASAS_CACHE["timestamp"] is not None
        and (datetime.now() - _TASAS_CACHE["timestamp"]).total_seconds()
        < _TASAS_CACHE["timeout_minutes"] * 60
    ):
        logger.info("✅ Usando tasas de cambio en cache")
        return _TASAS_CACHE["tasas"]

    # -----------------------------
    # 2. Consumir API del BHD
    # -----------------------------
    try:
        logger.info("🔄 Actualizando tasas de cambio desde BHD...")
        url = "https://backend.bhd.com.do/api/modal-cambio-rate?populate=deep"
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        data = r.json()

        # Estructura real confirmada por tu ejemplo JSON
        # data → attributes → exchangeRates → [{currency, buyingRate, sellingRate}]
        attributes = data["data"]["attributes"]
        items = attributes["exchangeRates"]

        tasas = {}

        for item in items:
            # monedas: USD, EUR
            cur = item["currency"].upper()

            # BHD usa buyingRate / sellingRate
            compra = float(item["buyingRate"])
            venta = float(item["sellingRate"])

            tasas[f"{cur}_compra"] = compra
            tasas[f"{cur}_venta"] = venta

        # Guardar en cache
        _TASAS_CACHE["tasas"] = tasas
        _TASAS_CACHE["timestamp"] = datetime.now()

        logger.info(f"📈 Tasas actualizadas: {tasas}")
        return tasas

    except Exception as e:
        logger.error(f"Error al obtener tasas de cambio: {e}")

        # fallback: último valor conocido o None
        return _TASAS_CACHE["tasas"]


def convertir_a_dop(monto: float, moneda: str, tasas: Dict[str, float]) -> Dict[str, Any]:
    """Convierte monto a DOP usando tasas de BHD."""
    if moneda == "DOP":
        return {
            "monto_original": monto,
            "moneda_original": moneda,
            "monto_dop": monto,
            "tasa_aplicada": 1.0,
            "tipo_tasa": "n/a",
            "conversion_requerida": False,
        }

    clave = f"{moneda}_venta"
    tasa = tasas.get(clave)

    if not tasa:
        return {
            "monto_original": monto,
            "moneda_original": moneda,
            "monto_dop": monto,
            "tasa_aplicada": 1.0,
            "tipo_tasa": "indefinida",
            "conversion_requerida": False,
        }

    monto_dop = monto * tasa
    return {
        "monto_original": monto,
        "moneda_original": moneda,
        "monto_dop": monto_dop,
        "tasa_aplicada": tasa,
        "tipo_tasa": "venta",
        "conversion_requerida": True,
    }


def obtener_estado_tasas() -> Dict[str, Any]:
    tasas = obtener_tasas_cambio()
    return {
        "tasas_actuales": tasas,
        "cache_actualizado": _TASAS_CACHE["timestamp"].isoformat()
        if _TASAS_CACHE["timestamp"]
        else None,
        "estado": "activo" if tasas else "error",
    }
