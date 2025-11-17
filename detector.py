# detector.py
import hashlib
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List

import logging
import requests

logger = logging.getLogger(__name__)

# Cache sencillo en memoria para tasas
_TASAS_CACHE: Dict[str, Any] = {
    "tasas": None,
    "timestamp": None,
}

# Puedes parametrizar esto si quieres
BHD_TASAS_URL = "https://www.bhd.com.do"  # placeholder demo


def hash_cliente(customer_ref_id: Optional[str]) -> Optional[str]:
    if not customer_ref_id:
        return None
    return hashlib.sha256(customer_ref_id.encode("utf-8")).hexdigest()


def _tasas_por_defecto() -> Dict[str, float]:
    return {
        "USD_venta": 59.5,
        "USD_compra": 58.5,
        "EUR_venta": 65.0,
        "EUR_compra": 64.0,
    }


def _fetch_tasas_bhd() -> Dict[str, float]:
    """
    Placeholder: aquí puedes integrar el scraping / API real del BHD.
    Si falla, devolvemos tasas por defecto.
    """
    try:
        # TODO: implementar lógica real. Por ahora devolvemos default.
        return _tasas_por_defecto()
    except Exception as e:
        logger.warning(f"No se pudieron obtener tasas del BHD: {e}")
        return _tasas_por_defecto()


def obtener_tasas_cambio() -> Dict[str, float]:
    """Obtiene tasas de cambio con cache de 30 minutos"""
    ahora = datetime.utcnow()
    if _TASAS_CACHE["tasas"] and _TASAS_CACHE["timestamp"]:
        delta = ahora - _TASAS_CACHE["timestamp"]
        if delta.total_seconds() < 30 * 60:
            return _TASAS_CACHE["tasas"]

    tasas = _fetch_tasas_bhd()
    _TASAS_CACHE["tasas"] = tasas
    _TASAS_CACHE["timestamp"] = ahora
    return tasas


def convertir_a_dop(monto: float, moneda: str, tasas: Dict[str, float]) -> Dict[str, Any]:
    """
    Convierte montos de USD/EUR a DOP. Si ya es DOP, devuelve igual.
    """
    moneda = moneda.upper()
    if moneda == "DOP":
        return {
            "monto_original": monto,
            "moneda_original": moneda,
            "monto_dop": monto,
            "tasa_aplicada": 1.0,
            "tipo_tasa": "n/a",
            "descripcion": "Monto ya en DOP",
            "conversion_requerida": False,
        }

    key = f"{moneda}_venta"
    tasa = tasas.get(key)
    if not tasa:
        # Fallback duro
        logger.warning(f"No se encontró tasa para {moneda}, usando fallback 1:1")
        tasa = 1.0

    monto_dop = monto * tasa
    return {
        "monto_original": monto,
        "moneda_original": moneda,
        "monto_dop": float(monto_dop),
        "tasa_aplicada": float(tasa),
        "tipo_tasa": "venta",
        "descripcion": f"{moneda} → DOP (tasa venta: {tasa})",
        "conversion_requerida": True,
    }


# ------------------------
# Reglas de negocio
# ------------------------

PAISES_ALTO_RIESGO = {"VE", "HT"}
PAISES_MEDIO_RIESGO = set()  # puedes llenarlo luego


def _extraer_pais_desde_name_loc(name_loc: Optional[str]) -> Optional[str]:
    """
    Heurística básica: toma el último token después de una coma y lo usa como país (ej. 'VE', 'DO', etc.)
    """
    if not name_loc:
        return None
    partes = [p.strip() for p in name_loc.split(",") if p.strip()]
    if not partes:
        return None
    ultimo = partes[-1]
    if len(ultimo) in (2, 3):
        return ultimo.upper()
    return None


def calcular_factores_basicos(monto_dop: float, moneda: str, hora_tx: int, name_loc: Optional[str]) -> List[str]:
    factores: List[str] = []
    pais = _extraer_pais_desde_name_loc(name_loc)

    # Montos
    if monto_dop > 10000:
        factores.append("MONTO_ELEVADO")
    if monto_dop < 50:
        factores.append("MONTO_MUY_BAJO")

    # Horario
    if 0 <= hora_tx < 6:
        factores.append("HORARIO_NOCTURNO")

    # País
    if pais in PAISES_ALTO_RIESGO:
        factores.append("PAIS_ALTO_RIESGO")
    elif pais and pais not in {"DO", "US"}:
        factores.append("PAIS_RIESGO_MEDIO")

    # Divisa
    if moneda in {"USD", "EUR"}:
        factores.append("TRANSACCION_DIVISA")
        if monto_dop > 15000:
            factores.append("DIVISA_MONTO_ELEVADO")
        if "MONTO_ELEVADO" in factores and "HORARIO_NOCTURNO" in factores:
            factores.append("MONTO_ALTO_HORARIO_SOSPECHOSO")

    return factores


def calcular_factores_historial(hist: Dict[str, Any]) -> List[str]:
    """
    hist = {
      'tx_24h': int,
      'tx_7d': int,
      'monto_promedio_30d': float | None,
      'monto_dop_actual': float
    }
    """
    factores: List[str] = []

    tx_24h = hist.get("tx_24h") or 0
    tx_7d = hist.get("tx_7d") or 0
    promedio_30d = hist.get("monto_promedio_30d")
    monto_actual = hist.get("monto_dop_actual") or 0.0

    if tx_24h >= 5:
        factores.append("FRECUENCIA_ALTA_24H")
    if tx_7d >= 20:
        factores.append("FRECUENCIA_ALTA_7D")

    if promedio_30d and promedio_30d > 0:
        if monto_actual > promedio_30d * 3:
            factores.append("DESVIO_MONTO_ALTO")
        elif monto_actual < promedio_30d * 0.3:
            factores.append("DESVIO_MONTO_BAJO")

    return factores


def calcular_factores_merchant(merchant_ctx: Dict[str, Any]) -> List[str]:
    factores: List[str] = []
    if merchant_ctx.get("merchant_permitido") is False:
        factores.append("MERCHANT_NO_PERMITIDO")
    if merchant_ctx.get("mcc_permitido") is False:
        factores.append("MCC_NO_PERMITIDO")
    if merchant_ctx.get("riesgo_merchant") == "ALTO":
        factores.append("MERCHANT_ALTO_RIESGO")
    if merchant_ctx.get("riesgo_mcc") == "ALTO":
        factores.append("MCC_ALTO_RIESGO")
    return factores


def analizar_riesgo(
    monto_dop: float,
    moneda_original: str,
    hora_tx: int,
    name_loc: Optional[str],
    hist_ctx: Dict[str, Any],
    merchant_ctx: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Devuelve un dict con:
      - fraude_detectado
      - probabilidad_fraude
      - nivel_riesgo
      - factores_riesgo
      - mensaje
      - recomendacion
      - score_anomalia (placeholder por ahora)
    """

    factores = []
    factores += calcular_factores_basicos(monto_dop, moneda_original, hora_tx, name_loc)
    factores += calcular_factores_historial(hist_ctx)
    factores += calcular_factores_merchant(merchant_ctx)

    # scoring simple por ahora (cada factor suma 1)
    riesgo_score = len(factores)

    # Merchant / MCC no permitido + países alto riesgo pesan más
    if "MERCHANT_NO_PERMITIDO" in factores or "MCC_NO_PERMITIDO" in factores:
        riesgo_score += 2
    if "PAIS_ALTO_RIESGO" in factores:
        riesgo_score += 2

    if riesgo_score >= 7:
        nivel = "ALTO"
        fraude = True
        prob = min(0.9, 0.5 + 0.05 * riesgo_score)
        mensaje = "ALERTA: Transacción identificada como de ALTO RIESGO"
        recomendacion = "Revisar manualmente y contactar al cliente"
    elif riesgo_score >= 3:
        nivel = "MEDIO"
        fraude = False
        prob = min(0.7, 0.2 + 0.05 * riesgo_score)
        mensaje = "Transacción con factores de riesgo moderados"
        recomendacion = "Evaluar según políticas internas o monitorear"
    else:
        nivel = "BAJO"
        fraude = False
        prob = 0.1 + 0.05 * riesgo_score
        mensaje = "Transacción dentro de parámetros normales"
        recomendacion = "Transacción aprobada automáticamente"

    return {
        "fraude_detectado": fraude,
        "probabilidad_fraude": round(prob, 4),
        "nivel_riesgo": nivel,
        "factores_riesgo": factores,
        "mensaje": mensaje,
        "recomendacion": recomendacion,
        "score_anomalia": -float(riesgo_score),  # placeholder
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


def cerrar_modelo():
    _TASAS_CACHE["tasas"] = None
    _TASAS_CACHE["timestamp"] = None
