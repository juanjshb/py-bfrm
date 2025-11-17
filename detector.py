# [file name]: detector.py
# [file content begin]
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

# ... (Configuración de logging, Cache y Entrenamiento del Modelo sin cambios) ...
logger = logging.getLogger(__name__)
_TASAS_CACHE = {
    'tasas': None,
    'timestamp': None,
    'timeout_minutes': 30
}
np.random.seed(42)
base = pd.DataFrame({
    "monto": np.concatenate([
        np.random.normal(3000, 800, 400),
        np.random.normal(15000, 5000, 50),
        np.random.normal(100, 50, 50)
    ]).clip(1, 50000),
    "hora": np.concatenate([
        np.random.normal(14, 4, 400).clip(0, 23).astype(int),
        np.random.randint(0, 6, 50),
        np.random.randint(22, 24, 50)
    ])
})
model = IsolationForest(contamination=0.03, random_state=42)
model.fit(base[["monto","hora"]])
LOG_PATH = "auditoria/alertas.json"
os.makedirs("auditoria", exist_ok=True)

# ... (obtener_tasas_cambio y convertir_a_dop sin cambios) ...

def analizar_riesgo(
    monto_dop: float, 
    hora: int, 
    pais: str, 
    moneda_original: str,
    mcc_info: Optional[Dict[str, Any]] = None,
    mid_info: Optional[Dict[str, Any]] = None,
    client_profile: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Analiza múltiples factores de riesgo, incluyendo historial del cliente y reglas de comercio.
    """
    factores_riesgo = []
    score_riesgo = 0
    
    # --- 1. REGLAS DE COMERCIO (MCC y MID) ---
    if mcc_info:
        mcc_risk = mcc_info.get('risk_level', 'medium')
        if mcc_risk == 'blocked':
            factores_riesgo.append("MCC_BLOQUEADO")
            score_riesgo += 10 # Penalización muy alta
        elif mcc_risk == 'high':
            factores_riesgo.append("MCC_ALTO_RIESGO")
            score_riesgo += 3
            
    if mid_info:
        mid_status = mid_info.get('status', 'watch')
        if mid_status == 'denied':
            factores_riesgo.append("COMERCIO_BLOQUEADO")
            score_riesgo += 10 # Penalización muy alta
        elif mid_status == 'allowed':
            factores_riesgo.append("COMERCIO_CONFIABLE")
            score_riesgo -= 2 # Reduce el riesgo
            
    # --- 2. REGLAS GENERALES (Monto, Hora, País) ---
    if monto_dop > 10000:
        factores_riesgo.append("MONTO_ELEVADO")
        score_riesgo += 2
    elif monto_dop < 50:
        factores_riesgo.append("MONTO_MUY_BAJO")
        score_riesgo += 1
    
    if 0 <= hora <= 6:
        factores_riesgo.append("HORARIO_NOCTURNO")
        score_riesgo += 1
    
    paises_alto_riesgo = ["VE", "HT"]
    if pais in paises_alto_riesgo:
        factores_riesgo.append("PAIS_ALTO_RIESGO")
        score_riesgo += 2
    
    if moneda_original != "DOP":
        factores_riesgo.append("TRANSACCION_DIVISA")
        score_riesgo += 1

    # --- 3. REGLAS DE HISTORIAL DEL CLIENTE ---
    if client_profile:
        avg_amount = client_profile.get('avg_amount_dop', 0)
        countries = client_profile.get('countries_used', [])
        
        # Monto inusual para el cliente
        if avg_amount > 0 and monto_dop > (avg_amount * 5):
            factores_riesgo.append("MONTO_INUSUAL_CLIENTE")
            score_riesgo += 3
        
        # Primera transacción en un país nuevo
        if pais not in countries and pais != "DO":
            factores_riesgo.append("PAIS_NUEVO_CLIENTE")
            score_riesgo += 2
        
        # Transacciones muy rápidas (frecuencia)
        tx_count_last_hour = client_profile.get('tx_count_last_hour', 0)
        if tx_count_last_hour > 5:
            factores_riesgo.append("ALTA_FRECUENCIA_CLIENTE")
            score_riesgo += 3

    # --- 4. REGLAS COMBINADAS ---
    if monto_dop > 8000 and (hora <= 6 or hora >= 22):
        factores_riesgo.append("MONTO_ALTO_HORARIO_SOSPECHOSO")
        score_riesgo += 2
    
    # Asegurar que el score no sea negativo
    score_riesgo = max(0, score_riesgo)
    
    return {
        "factores_riesgo": list(set(factores_riesgo)), # Eliminar duplicados
        "score_riesgo": score_riesgo,
        "nivel_riesgo": "ALTO" if score_riesgo >= 5 else "MEDIO" if score_riesgo >= 1 else "BAJO"
    }

def detectar_fraude(
    cliente_id: str, 
    monto: float, 
    moneda: str, 
    hora: int, 
    pais: str,
    # Nuevos parámetros contextuales
    mcc_info: Optional[Dict[str, Any]] = None,
    mid_info: Optional[Dict[str, Any]] = None,
    client_profile: Optional[Dict[str, Any]] = None
) -> dict:
    """
    Detecta fraude con contexto de cliente y comercio.
    """
    tasas = obtener_tasas_cambio()
    conversion_info = convertir_a_dop(monto, moneda, tasas)
    monto_dop = conversion_info["monto_dop"]
    
    cliente_hash = hashlib.sha256(cliente_id.encode()).hexdigest()[:16]

    # Predecir con modelo ML (Análisis de Anomalía General)
    features = pd.DataFrame([[monto_dop, hora]], columns=["monto","hora"])
    pred_ml = model.predict(features)[0]  # -1 = anomalía
    score_ml = model.decision_function(features)[0]
    probabilidad_fraude_ml = max(0, min(1, (0.5 - score_ml) * 2))
    
    # Análisis de riesgo detallado (Reglas de Negocio + Contexto)
    analisis_riesgo = analizar_riesgo(
        monto_dop, hora, pais, moneda, 
        mcc_info, mid_info, client_profile
    )
    
    # Determinar si es fraude basado en ML y reglas
    es_fraude_ml = pred_ml == -1
    es_fraude_reglas = analisis_riesgo["nivel_riesgo"] == "ALTO"
    
    es_fraude = es_fraude_ml or es_fraude_reglas
    
    # Mensaje descriptivo
    if es_fraude:
        if es_fraude_ml and es_fraude_reglas:
            mensaje = "ALERTA: Patrón anómalo (ML) y múltiples factores de riesgo (Reglas) detectados"
        elif es_fraude_ml:
            mensaje = "ALERTA: Patrón anómalo detectado por modelo de Machine Learning"
        else:
            mensaje = "ALERTA: Múltiples factores de riesgo identificados por reglas de negocio"
    else:
        mensaje = "Transacción dentro de parámetros normales"
    
    # Recomendación
    if es_fraude:
        recomendacion = "Recomendación: Revisar transacción manualmente y contactar al cliente"
    elif analisis_riesgo["nivel_riesgo"] == "MEDIO":
        recomendacion = "Recomendación: Monitorear transacción"
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
        "probabilidad_fraude": round(float(probabilidad_fraude_ml), 4), # Basado en ML
        "score_anomalia": float(score_ml),
        "analisis_riesgo": analisis_riesgo, # Resultado de las reglas
        "mensaje": mensaje,
        "recomendacion": recomendacion,
        "timestamp": datetime.utcnow().isoformat(),
        "conversion_moneda": conversion_info,
        "tasas_actualizadas": tasas.get('actualizado', ''),
        "datos_recibidos": {
            "cliente_id_length": len(cliente_id),
            "monto_original": float(monto),
            "moneda_original": moneda,
            "hora_transaccion": hora,
            "pais_origen": pais,
            "mcc": mcc_info.get('mcc') if mcc_info else None,
            "mid": mid_info.get('mid') if mid_info else None
        }
    }

    if resultado["es_fraude"]:
        _registrar_alerta(resultado)
    
    return resultado

# ... (_registrar_alerta, obtener_estado_tasas, cerrar_modelo sin cambios) ...
# [file content end]
