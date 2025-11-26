# app/infra/detectors/fraude_model.py
import hashlib
from datetime import datetime
from typing import Dict, Any, List

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

# Entrenamiento sintético (igual idea que tenías)
np.random.seed(42)
base = pd.DataFrame(
    {
        "monto": np.concatenate(
            [
                np.random.normal(3000, 800, 400),
                np.random.normal(15000, 5000, 50),
                np.random.normal(100, 50, 50),
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

_isoforest = IsolationForest(contamination=0.03, random_state=42)
_isoforest.fit(base[["monto", "hora"]])


def _hash_cliente(customer_id: int | None) -> str:
    if customer_id is None:
        return "anon"
    return hashlib.sha256(str(customer_id).encode("utf-8")).hexdigest()[:16]


def _evaluar_reglas(
    monto_src: float,
    monto_dop: float,
    moneda: str,
    hora: int,
    pais: str | None,
) -> List[str]:
    factores: List[str] = []

    ## Reglas de riesgo por monto
    if moneda in ("DOP") and monto_dop > 12000:
        factores.append("MONTO_ELEVADO")

    if monto_dop < 50:
        factores.append("MONTO_MUY_BAJO")

    ## Reglas por moneda
    if moneda in ("USD", "EUR"):
        factores.append("TRANSACCION_DIVISA")

    if moneda in ("USD") and monto_src >= 200:
        factores.append("DIVISA_MONTO_ELEVADO")
    
    if moneda in ("EUR") and monto_dop > 15000:
        factores.append("DIVISA_MONTO_ELEVADO")

    ## Reglas por horario
    if 0 <= hora <= 5:
        factores.append("HORARIO_NOCTURNO")

    ## Reglas por país
    if pais in ("VE", "HT"): 
        factores.append("PAIS_ALTO_RIESGO") 
    elif pais and pais not in ("DO", "US"): 
        factores.append("PAIS_RIESGO_MEDIO")

    ## Regla combinada
    if "MONTO_ELEVADO" in factores and "HORARIO_NOCTURNO" in factores:
        factores.append("MONTO_ALTO_HORARIO_SOSPECHOSO")


    return factores


def analizar(
    *,
    monto_src: float,
    monto_dop: float,
    moneda: str,
    hora_local: int,
    pais_cliente: str | None,
    customer_id: int | None,
) -> Dict[str, Any]:
    """
    Devuelve:
      - fraude_detectado
      - probabilidad_fraude
      - nivel_riesgo
      - factores_riesgo
      - mensaje
      - recomendacion
      - score_anomalia
      - cliente_hash
    """
    # Isolation Forest
    X = np.array([[monto_dop, hora_local]])
    score = float(_isoforest.decision_function(X)[0])
    is_outlier = bool(_isoforest.predict(X)[0] == -1)

    factores = _evaluar_reglas(monto_src, monto_dop, moneda, hora_local, pais_cliente)

    # Ponderar puntuación
    riesgo_score = 0.0
    riesgo_score += ( -score ) * 2  # más negativo -> más riesgo
    riesgo_score += len(factores)

    if riesgo_score >= 6:
        nivel = "ALTO"
        fraude = True
    elif riesgo_score >= 3:
        nivel = "MEDIO"
        fraude = is_outlier
    else:
        nivel = "BAJO"
        fraude = False

    prob = max(0.01, min(0.99, 0.4 + riesgo_score / 10))

    if fraude:
        mensaje = "ALERTA: Transacción potencialmente fraudulenta."
        recomendacion = "Revisar manualmente y contactar al cliente."
    elif nivel == "MEDIO":
        mensaje = "Transacción de riesgo medio."
        recomendacion = "Permitir, pero monitorear actividad futura."
    else:
        mensaje = "Transacción dentro de patrones normales."
        recomendacion = "Aprobada automáticamente."

    return {
        "fraude_detectado": fraude,
        "probabilidad_fraude": round(float(prob), 4),
        "nivel_riesgo": nivel,
        "factores_riesgo": factores,
        "mensaje": mensaje,
        "recomendacion": recomendacion,
        "score_anomalia": float(score),
        "cliente_hash": _hash_cliente(customer_id),
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }
