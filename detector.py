# detector.py
import hashlib
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from datetime import datetime, timedelta
import json
import os
import requests
import logging
from typing import Dict, Any, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Cache para tasas de cambio BHD ---
_TASAS_CACHE: Dict[str, Any] = {
    "tasas": None,
    "timestamp": None,
    "timeout_minutes": 30,
}

# --- Modelo ML (Isolation Forest) entrenado con datos sintéticos razonables ---
np.random.seed(42)
base = pd.DataFrame(
    {
        "monto": np.concatenate(
            [
                np.random.normal(3000, 800, 400),   # Normal DOP
                np.random.normal(15000, 5000, 50),  # Altos
                np.random.normal(100, 50, 50),      # Muy bajos
            ]
        ).clip(1, 50000),
        "hora": np.concatenate(
            [
                np.random.normal(14, 4, 400).clip(0, 23).astype(int),
                np.random.randint(0, 6, 50),
                np.random.randint(22, 24, 50),
            ]
        ),
    }
)

model = IsolationForest(contamination=0.03, random_state=42)
model.fit(base[["monto", "hora"]])

LOG_PATH = "auditoria/alertas.json"
os.makedirs("auditoria", exist_ok=True)


def _log_alerta(resultado: Dict[str, Any]) -> None:
    try:
        if os.path.exists(LOG_PATH):
            with open(LOG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
        else:
            data = []
        data.append(resultado)
        with open(LOG_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Error guardando alerta de auditoría: {e}")


def obtener_tasas_cambio() -> Dict[str, Any]:
    """Obtiene tasas desde BHD con cache de 30 min; usa fallback si falla."""
    ahora = datetime.now()
    if (
        _TASAS_CACHE["tasas"] is not None
        and _TASAS_CACHE["timestamp"] is not None
        and ahora - _TASAS_CACHE["timestamp"]
        < timedelta(minutes=_TASAS_CACHE["timeout_minutes"])
    ):
        return _TASAS_CACHE["tasas"]

    try:
        url = "https://www.bhd.com.do/_api/web/lists/getbytitle('ExchangeRates')/items"
        logger.info("Obteniendo tasas de cambio desde BHD...")
        resp = requests.get(url, timeout=5)
        resp.raise_for_status()
        data = resp.json()

        exchange_rates = (
            data.get("data", {})
            .get("attributes", {})
            .get("exchangeRates", [])
        )

        tasas: Dict[str, Any] = {}
        for rate in exchange_rates:
            currency = rate.get("currency", "")
            if currency == "USD":
                tasas["USD_compra"] = float(rate.get("buyingRate", 0))
                tasas["USD_venta"] = float(rate.get("sellingRate", 0))
            elif currency == "EUR":
                tasas["EUR_compra"] = float(rate.get("buyingRate", 0))
                tasas["EUR_venta"] = float(rate.get("sellingRate", 0))

        if not tasas:
            raise ValueError("Respuesta de tasas sin datos útiles")

        tasas["actualizado"] = datetime.now().isoformat()
        _TASAS_CACHE["tasas"] = tasas
        _TASAS_CACHE["timestamp"] = datetime.now()
        return tasas

    except Exception as e:
        logger.error(f"Error obteniendo tasas de cambio, usando fallback: {e}")
        tasas_default = {
            "USD_compra": 58.0,
            "USD_venta": 59.5,
            "EUR_compra": 62.0,
            "EUR_venta": 64.0,
            "actualizado": datetime.now().isoformat(),
        }
        _TASAS_CACHE["tasas"] = tasas_default
        _TASAS_CACHE["timestamp"] = datetime.now()
        return tasas_default


def convertir_a_dop(
    monto: float, moneda: str, tasas: Dict[str, Any]
) -> Dict[str, Any]:
    """Convierte un monto a DOP usando tasas de venta (simple, lado tarjeta)."""
    moneda = moneda.upper()
    if moneda == "DOP":
        return {
            "monto_dop": round(monto, 2),
            "tasa_aplicada": 1.0,
            "tipo_tasa": "1:1",
            "descripcion": "Monto ya en DOP",
            "conversion_requerida": False,
        }

    info = {
        "monto_original": monto,
        "moneda_original": moneda,
        "conversion_requerida": True,
    }

    if moneda == "USD":
        tasa = tasas.get("USD_venta", 59.5)
        info.update(
            {
                "monto_dop": round(monto * tasa, 2),
                "tasa_aplicada": tasa,
                "tipo_tasa": "venta",
                "descripcion": f"USD → DOP (tasa venta: {tasa})",
            }
        )
    elif moneda == "EUR":
        tasa = tasas.get("EUR_venta", 64.0)
        info.update(
            {
                "monto_dop": round(monto * tasa, 2),
                "tasa_aplicada": tasa,
                "tipo_tasa": "venta",
                "descripcion": f"EUR → DOP (tasa venta: {tasa})",
            }
        )
    else:
        # Moneda desconocida: asumimos DOP
        info.update(
            {
                "monto_dop": round(monto, 2),
                "tasa_aplicada": 1.0,
                "tipo_tasa": "desconocida",
                "descripcion": f"Moneda desconocida {moneda}, tratado como DOP",
            }
        )

    return info


def analizar_riesgo(
    monto_dop: float,
    hora: int,
    pais: str,
    moneda_original: str,
    contexto_cliente: Optional[Dict[str, Any]] = None,
    contexto_merchant: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Analiza factores de riesgo:
    - Monto, hora, país, divisa
    - Historial del cliente
    - MCC / Merchant permitido
    """
    factores_riesgo = []
    score_riesgo = 0

    # --- Reglas base por monto ---
    if monto_dop > 10000:
        factores_riesgo.append("MONTO_ELEVADO")
        score_riesgo += 2
    elif monto_dop < 50:
        factores_riesgo.append("MONTO_MUY_BAJO")
        score_riesgo += 1

    # --- Reglas por horario ---
    if 0 <= hora <= 6:
        factores_riesgo.append("HORARIO_NOCTURNO")
        score_riesgo += 1
    elif hora >= 22:
        factores_riesgo.append("HORARIO_NOCTURNO_TARDIO")
        score_riesgo += 1

    # --- País ---
    paises_alto_riesgo = ["VE", "HT"]
    if pais in paises_alto_riesgo:
        factores_riesgo.append("PAIS_ALTO_RIESGO")
        score_riesgo += 2
    elif pais not in ["DO", "US"]:
        factores_riesgo.append("PAIS_RIESGO_MEDIO")
        score_riesgo += 1

    # --- Moneda ---
    if moneda_original != "DOP":
        factores_riesgo.append("TRANSACCION_DIVISA")
        score_riesgo += 1

    if monto_dop > 15000 and (hora <= 6 or hora >= 22):
        factores_riesgo.append("MONTO_ALTO_HORARIO_SOSPECHOSO")
        score_riesgo += 2

    # --- Historial del cliente ---
    if contexto_cliente and contexto_cliente.get("tiene_historial"):
        prom = contexto_cliente.get("promedio_monto")
        desv = contexto_cliente.get("desviacion_monto")
        trans_1h = contexto_cliente.get("trans_1h", 0)
        trans_10m = contexto_cliente.get("trans_10m", 0)

        if prom is not None and desv and desv > 0:
            z = (monto_dop - prom) / desv
            if z >= 3:
                factores_riesgo.append("DESVIO_MONTO_HISTORICO")
                score_riesgo += 2

        if trans_1h >= 5:
            factores_riesgo.append("FRECUENCIA_ALTA_1H")
            score_riesgo += 2

        if trans_10m >= 3:
            factores_riesgo.append("FRECUENCIA_ALTA_10M")
            score_riesgo += 2

    # --- Merchant / MCC ---
    if contexto_merchant:
        if not contexto_merchant.get("permitido", True):
            factores_riesgo.append("MERCHANT_NO_PERMITIDO")
            score_riesgo += 3

        riesgo_merchant = contexto_merchant.get("riesgo_merchant", "MEDIO")
        riesgo_mcc = contexto_merchant.get("riesgo_mcc", "MEDIO")

        if riesgo_mcc == "ALTO":
            factores_riesgo.append("MCC_ALTO_RIESGO")
            score_riesgo += 2

        if riesgo_merchant == "ALTO":
            factores_riesgo.append("MERCHANT_ALTO_RIESGO")
            score_riesgo += 2

    if score_riesgo >= 6:
        nivel = "ALTO"
    elif score_riesgo >= 2:
        nivel = "MEDIO"
    else:
        nivel = "BAJO"

    return {
        "factores_riesgo": factores_riesgo,
        "score_riesgo": score_riesgo,
        "nivel_riesgo": nivel,
    }


def detectar_fraude(
    cliente_id: str,
    monto: float,
    moneda: str,
    hora: int,
    pais: str,
    contexto_cliente: Optional[Dict[str, Any]] = None,
    contexto_merchant: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Motor híbrido de fraude:
    - Conversión de moneda
    - Modelo ML (IsolationForest)
    - Reglas de negocio
    - Historial del cliente
    - MCC / Merchant permitido
    """
    tasas = obtener_tasas_cambio()
    conv = convertir_a_dop(monto, moneda, tasas)
    monto_dop = conv["monto_dop"]

    cliente_hash = hashlib.sha256(cliente_id.encode()).hexdigest()[:16]

    features = pd.DataFrame([[monto_dop, hora]], columns=["monto", "hora"])
    pred = model.predict(features)[0]  # -1 anomalía, 1 normal
    score = model.decision_function(features)[0]

    probabilidad_fraude = max(0.0, min(1.0, (0.5 - score) * 2))

    analisis_riesgo = analizar_riesgo(
        monto_dop,
        hora,
        pais,
        moneda,
        contexto_cliente=contexto_cliente,
        contexto_merchant=contexto_merchant,
    )

    es_fraude_ml = pred == -1
    es_fraude_reglas = analisis_riesgo["nivel_riesgo"] == "ALTO"
    es_fraude = es_fraude_ml or es_fraude_reglas

    if es_fraude:
        if es_fraude_ml and es_fraude_reglas:
            mensaje = (
                "ALERTA: Transacción identificada como fraudulenta por "
                "modelo ML y reglas de negocio"
            )
        elif es_fraude_ml:
            mensaje = "ALERTA: Patrón anómalo detectado por modelo de Machine Learning"
        else:
            mensaje = "ALERTA: Múltiples factores de riesgo identificados"
    else:
        mensaje = "Transacción dentro de parámetros normales"

    if es_fraude:
        recomendacion = (
            "Recomendación: Revisar transacción manualmente y contactar al cliente"
        )
    elif analisis_riesgo["nivel_riesgo"] == "MEDIO":
        recomendacion = (
            "Recomendación: Monitorear transacción y verificar con el cliente"
        )
    else:
        recomendacion = "Recomendación: Transacción aprobada automáticamente"

    resultado = {
        "cliente_hash": cliente_hash,
        "pais": pais,
        "monto_original": float(monto),
        "moneda_original": moneda,
        "monto_dop": float(monto_dop),
        "hora": hora,
        "es_fraude": bool(es_fraude),
        "probabilidad_fraude": round(float(probabilidad_fraude), 4),
        "score_anomalia": float(score),
        "analisis_riesgo": analisis_riesgo,
        "mensaje": mensaje,
        "recomendacion": recomendacion,
        "conversion_moneda": conv,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "datos_recibidos": {
            "cliente_id": cliente_id,
            "pais": pais,
            "contexto_cliente": contexto_cliente or {},
            "contexto_merchant": contexto_merchant or {},
        },
    }

    if es_fraude:
        _log_alerta(resultado)

    return resultado


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
