# app/infra/detectors/fraude_model.py

import hashlib
from datetime import datetime
from typing import Dict, Any, List, Set, Tuple

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

from app.infra.cache.risk_factor_cache import RiskConfig

# ==========================================================
#  CONFIGURACIÓN MODELO DE ANOMALÍAS (IsolationForest)
# ==========================================================

# ⚠️ El modelo se inicializa globalmente, pero puedes re-entrenarlo
# con datos reales usando la función `entrenar_isolation_forest`
_isoforest: IsolationForest | None = None


def _hash_cliente(customer_id: int | None) -> str:
    """Hash corto y no reversible para identificar al cliente."""
    if customer_id is None:
        return "anon"
    return hashlib.sha256(str(customer_id).encode("utf-8")).hexdigest()[:16]


# ==========================================================
#  LÓGICA DE RIESGO / REGLAS
# ==========================================================

def es_critico(risk_config: RiskConfig, factores: Set[str]) -> bool:
    """
    Devuelve True si al menos uno de los factores está en la lista de críticos.
    Se asume que `risk_config.critical` es un set de códigos de factores.
    """
    return any(f in risk_config.critical for f in factores)


def aplicar_reglas_combinadas(risk_config: RiskConfig, factores: Set[str]) -> None:
    """
    Aplica reglas combinadas definidas en RiskConfig:
      - rule.trigger_factors: lista de factores que disparan la regla
      - rule.result_factor: factor resultante a agregar
      - rule.enabled: si la regla está activa
      - rule.weight_override: peso opcional para el factor resultante
    """
    for rule in risk_config.rules:
        if not rule.enabled:
            continue

        # Todos los factores de trigger deben estar presentes
        if all(f in factores for f in rule.trigger_factors):
            factores.add(rule.result_factor)
            if rule.weight_override is not None:
                # Sobrescribe el peso del factor resultante
                risk_config.weights[rule.result_factor] = rule.weight_override


def calcular_riesgo_final(
    risk_config: RiskConfig,
    factores: List[str],
    score_anomalia: float,
) -> Tuple[str, float, bool]:
    """
    Combina factores de riesgo (reglas) + anomalía estadística (IsolationForest)
    para definir el nivel final de riesgo.
    Devuelve: (nivel_riesgo, score_total, es_fraude_bool)
    """
    factores_set: Set[str] = set(factores)

    # 1) Aplicar reglas combinadas
    aplicar_reglas_combinadas(risk_config, factores_set)

    # 2) Si tiene algún factor crítico → directo HIGH
    if es_critico(risk_config, factores_set):
        return "HIGH", 999.0, True

    # 3) Score base por pesos de factores
    base_score = sum(risk_config.weights.get(f, 0.0) for f in factores_set)

    # 4) Ajuste por anomalía
    # IsolationForest: valores más negativos suelen ser más anómalos.
    # Aprovechamos solo la parte negativa del score.
    if score_anomalia < 0:
        # Factor de escala razonable; se puede tunear con datos reales
        anomaly_component = abs(score_anomalia) * 10.0
        base_score += anomaly_component

    # 5) Cortes de riesgo
    if base_score >= 10:
        return "HIGH", base_score, True
    elif base_score >= 5:
        return "MEDIUM", base_score, False
    else:
        return "LOW", base_score, False


def _evaluar_reglas(
    monto_src: float,
    monto_dop: float,
    moneda: str,
    hora: int,
    pais: str | None,
    hrc: Set[str],
    mrc: Set[str],
) -> List[str]:
    """
    Reglas básicas de negocio:
      - por monto
      - por moneda
      - por hora
      - por país (usando high-risk / medium-risk sets)
    """
    factores: List[str] = []

    moneda = (moneda or "").upper().strip()

    # ==============================
    #  Reglas de riesgo por monto
    # ==============================
    if moneda == "DOP" and monto_dop > 12000:
        factores.append("HIGH_AMOUNT")

    if monto_dop < 50:
        factores.append("AMOUNT_TOO_LOW")

    # ==============================
    #  Reglas por moneda
    # ==============================
    if moneda in ("USD", "EUR"):
        factores.append("FOREING_CURRENCY_TRNX")  # Mantengo el código tal cual

    if moneda == "USD" and monto_src >= 200:
        factores.append("HIGH_USD_TRNX")

    if moneda == "EUR" and monto_dop > 15000:
        factores.append("HIGH_EUR_TRNX")

    # ==============================
    #  Reglas por horario
    # ==============================
    if 0 <= hora <= 5:
        factores.append("NIGHT_TIME")

    # ==============================
    #  Reglas por país
    # ==============================
    pais = (pais or "").strip().upper()

    if not pais:
        factores.append("COUNTRY_NOT_PROVIDED")
    else:
        if pais in hrc:
            factores.append("HIGH_RISK_COUNTRY")
        elif pais in mrc:
            factores.append("MEDIUM_RISK_COUNTRY")
        else:
            factores.append("LOW_RISK_COUNTRY")

    # ==============================
    #  Regla combinada fija
    # ==============================
    # Idealmente esto debería ser una regla combinada configurada en RiskConfig,
    # pero lo mantenemos aquí como ejemplo legacy.
    if "HIGH_AMOUNT" in factores and "NIGHT_TIME" in factores:
        factores.append("HIGH_AMOUNT_SUSPESIOUS_TIME")

    return factores


# ==========================================================
#  FUNCIÓN PRINCIPAL DE ANÁLISIS
# ==========================================================

def analizar(
    *,
    monto_src: float,
    monto_dop: float,
    moneda: str,
    hora_local: int,
    pais_cliente: str | None,
    customer_id: int | None,
    hrc: Set[str],
    mrc: Set[str],
    risk_config: RiskConfig,
) -> Dict[str, Any]:
    """
    Analiza una transacción combinando:
      - Reglas de negocio (monto, moneda, horario, país).
      - Detección de anomalías con IsolationForest (monto_dop, hora_local).
      - Configuración dinámica de pesos / factores críticos / reglas combinadas.

    Devuelve:
      - is_fraud (bool)
      - fraud_prob (0–1)
      - risk_level ("LOW" / "MEDIUM" / "HIGH")
      - risk_factor (lista de códigos de factores)
      - message (texto)
      - advice (recomendación)
      - anomaly_score (float)
      - anomaly_flag (bool)
      - customer_hash (string)
      - timestamp (ISO8601)
    """
    global _isoforest

    if _isoforest is None:
        # Fallback minimalista si alguien llama a analizar sin entrenar nada.
        # Idealmente deberías llamar a `entrenar_isolation_forest` al arrancar.
        df_fallback = generar_dataset_sintetico_basico()
        entrenar_isolation_forest(df_fallback)

    # 1) IsolationForest: sólo usa monto_dop y hora_local (normalizados a DOP)
    X = np.array([[monto_dop, hora_local]])
    score = float(_isoforest.decision_function(X)[0])
    is_outlier = bool(_isoforest.predict(X)[0] == -1)

    # 2) Reglas base
    factores = _evaluar_reglas(
        monto_src, monto_dop, moneda, hora_local,
        pais_cliente, hrc, mrc
    )

    # 3) Factor explícito por anomalía
    if is_outlier:
        factores.append("ANOMALY_DETECTED")

    # 4) Cálculo de riesgo final
    nivel, riesgo_score, fraude = calcular_riesgo_final(
        risk_config,
        factores,
        score,
    )

    # 5) Probabilidad “calibrada” de fraude (simple, pero acotada)
    #   - base ~ 0.35
    #   - agregamos influencia del score de riesgo (riesgo_score/15)
    prob = 0.35 + (riesgo_score / 15.0)
    prob = max(0.01, min(0.99, prob))

    # 6) Mensajes y recomendaciones
    if fraude:
        mensaje = "ALERT: Potentially fraudulent transaction."
        recomendacion = "Manual review and customer verification required."
    elif nivel == "MEDIUM":
        mensaje = "Medium risk transaction."
        recomendacion = "Allow but closely monitor future activity."
    else:
        mensaje = "Transaction within normal behavior patterns."
        recomendacion = "Automatically approved."

    return {
        "is_fraud": fraude,
        "fraud_prob": round(float(prob), 4),
        "risk_level": nivel,
        "risk_factor": factores,
        "message": mensaje,
        "advice": recomendacion,
        "anomaly_score": float(score),
        "anomaly_flag": is_outlier,
        "customer_hash": _hash_cliente(customer_id),
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }


# ==========================================================
#  GENERACIÓN DE DATASET SINTÉTICO “REALISTA”
#  PARA ENTRENAR ISOLATIONFOREST
# ==========================================================

def generar_dataset_sintetico_transacciones(
    n_normales: int = 4000,
    n_fraude_monto: int = 300,
    n_fraude_noche: int = 300,
    n_fraude_pais: int = 200,
    seed: int = 42,
) -> pd.DataFrame:
    """
    Genera un dataset sintético con columnas:
      - monto (en DOP)
      - hora (0–23)
      - moneda
      - pais
      - is_fraud (0/1)
      - escenario (str)

    Este dataset NO es real, pero está diseñado para parecerse
    a patrones típicos de uso y fraude para entrenar modelos
    no supervisados (IsolationForest) y hacer pruebas.
    """
    rng = np.random.default_rng(seed)

    # ------------------------------------
    # 1) Transacciones "normales"
    # ------------------------------------
    # Monto típico ~ lognormal alrededor de ~2,500 DOP
    montos_normales = np.exp(rng.normal(np.log(2500), 0.6, n_normales))
    montos_normales = np.clip(montos_normales, 50, 150000)

    horas_normales = np.clip(
        rng.normal(14, 4, n_normales).astype(int),
        0, 23
    )

    monedas_normales = rng.choice(
        ["DOP", "USD", "EUR"],
        size=n_normales,
        p=[0.85, 0.12, 0.03],
    )

    paises_normales = rng.choice(
        ["DO", "US", "ES", "PA", "MX", "CO"],
        size=n_normales,
        p=[0.6, 0.2, 0.05, 0.05, 0.05, 0.05],
    )

    df_normales = pd.DataFrame(
        {
            "monto": montos_normales,
            "hora": horas_normales,
            "moneda": monedas_normales,
            "pais": paises_normales,
            "is_fraud": 0,
            "escenario": "normal",
        }
    )

    # ------------------------------------
    # 2) Escenario fraude por monto alto
    # ------------------------------------
    montos_fraude_monto = rng.uniform(80000, 250000, n_fraude_monto)
    horas_fraude_monto = rng.integers(8, 20, n_fraude_monto)
    monedas_fraude_monto = rng.choice(["DOP", "USD"], size=n_fraude_monto, p=[0.7, 0.3])
    paises_fraude_monto = rng.choice(["DO", "US", "VE", "HT"], size=n_fraude_monto)

    df_fraude_monto = pd.DataFrame(
        {
            "monto": montos_fraude_monto,
            "hora": horas_fraude_monto,
            "moneda": monedas_fraude_monto,
            "pais": paises_fraude_monto,
            "is_fraud": 1,
            "escenario": "fraude_monto_alto",
        }
    )

    # ------------------------------------
    # 3) Escenario fraude por horario nocturno
    # ------------------------------------
    montos_fraude_noche = np.exp(rng.normal(np.log(3500), 0.5, n_fraude_noche))
    montos_fraude_noche = np.clip(montos_fraude_noche, 200, 80000)

    horas_fraude_noche = rng.integers(0, 5, n_fraude_noche)
    monedas_fraude_noche = rng.choice(["DOP", "USD"], size=n_fraude_noche, p=[0.75, 0.25])
    paises_fraude_noche = rng.choice(["DO", "VE", "HT", "BR"], size=n_fraude_noche)

    df_fraude_noche = pd.DataFrame(
        {
            "monto": montos_fraude_noche,
            "hora": horas_fraude_noche,
            "moneda": monedas_fraude_noche,
            "pais": paises_fraude_noche,
            "is_fraud": 1,
            "escenario": "fraude_noche",
        }
    )

    # ------------------------------------
    # 4) Escenario fraude por país de alto riesgo
    # ------------------------------------
    montos_fraude_pais = np.exp(rng.normal(np.log(5000), 0.7, n_fraude_pais))
    montos_fraude_pais = np.clip(montos_fraude_pais, 100, 120000)

    horas_fraude_pais = rng.integers(6, 22, n_fraude_pais)
    monedas_fraude_pais = rng.choice(["DOP", "USD", "EUR"], size=n_fraude_pais, p=[0.5, 0.4, 0.1])
    paises_fraude_pais = rng.choice(["VE", "HT", "NI", "CU"], size=n_fraude_pais)

    df_fraude_pais = pd.DataFrame(
        {
            "monto": montos_fraude_pais,
            "hora": horas_fraude_pais,
            "moneda": monedas_fraude_pais,
            "pais": paises_fraude_pais,
            "is_fraud": 1,
            "escenario": "fraude_pais_alto_riesgo",
        }
    )

    # ------------------------------------
    # 5) Concatenar todo
    # ------------------------------------
    df = pd.concat(
        [df_normales, df_fraude_monto, df_fraude_noche, df_fraude_pais],
        ignore_index=True,
    )

    # Shuffle del dataset
    df = df.sample(frac=1.0, random_state=seed).reset_index(drop=True)
    return df


def generar_dataset_sintetico_basico() -> pd.DataFrame:
    """
    Versión simplificada para fallback por si no quieres el dataset completo.
    Solo genera montos + horas sin etiquetas adicionales.
    """
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
    return base


def entrenar_isolation_forest(
    df: pd.DataFrame,
    contamination: float = 0.03,
    random_state: int = 42,
) -> IsolationForest:
    """
    Entrena y reemplaza el modelo global IsolationForest usando
    las columnas `monto` y `hora` del DataFrame df.

    - contamination ≈ proporción esperada de anomalías.
    """
    global _isoforest

    if not {"monto", "hora"}.issubset(df.columns):
        raise ValueError("El DataFrame debe contener columnas 'monto' y 'hora'.")

    modelo = IsolationForest(
        contamination=contamination,
        random_state=random_state,
        n_estimators=200,
        max_samples="auto",
        n_jobs=-1,
    )
    modelo.fit(df[["monto", "hora"]])
    _isoforest = modelo
    return modelo


# Inicialización por defecto al importar el módulo
# (puedes quitar esto si prefieres entrenar siempre afuera)
try:
    _df_init = generar_dataset_sintetico_basico()
    entrenar_isolation_forest(_df_init)
except Exception:
    # En caso de error, dejamos _isoforest = None para que analizar() lo gestione
    _isoforest = None
