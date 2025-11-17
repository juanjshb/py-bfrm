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

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Cache para tasas de cambio ---
_TASAS_CACHE = {
    'tasas': None,
    'timestamp': None,
    'timeout_minutes': 30  # Actualizar cada 30 minutos
}

# --- Entrenamiento inicial con datos más realistas ---
np.random.seed(42)
base = pd.DataFrame({
    "monto": np.concatenate([
        np.random.normal(3000, 800, 400),  # Transacciones normales en DOP
        np.random.normal(15000, 5000, 50), # Transacciones altas
        np.random.normal(100, 50, 50)      # Transacciones muy bajas
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

def obtener_tasas_cambio() -> Optional[Dict[str, float]]:
    """
    Obtiene las tasas de cambio actualizadas del BHD
    Returns:
        Dict con tasas de cambio o None si hay error
    """
    global _TASAS_CACHE
    
    # Verificar si el cache es válido
    if (_TASAS_CACHE['tasas'] is not None and 
        _TASAS_CACHE['timestamp'] is not None and
        (datetime.now() - _TASAS_CACHE['timestamp']).total_seconds() < _TASAS_CACHE['timeout_minutes'] * 60):
        logger.info("✅ Usando tasas de cambio en cache")
        return _TASAS_CACHE['tasas']
    
    try:
        logger.info("🔄 Actualizando tasas de cambio desde BHD...")
        url = "https://backend.bhd.com.do/api/modal-cambio-rate?populate=deep"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        # Extraer tasas de la respuesta
        exchange_rates = data.get('data', {}).get('attributes', {}).get('exchangeRates', [])
        
        tasas = {}
        for rate in exchange_rates:
            currency = rate.get('currency', '')
            if currency == 'USD':
                tasas['USD_compra'] = float(rate.get('buyingRate', 0))
                tasas['USD_venta'] = float(rate.get('sellingRate', 0))
            elif currency == 'EUR':
                tasas['EUR_compra'] = float(rate.get('buyingRate', 0))
                tasas['EUR_venta'] = float(rate.get('sellingRate', 0))
        
        tasas['actualizado'] = datetime.now().isoformat()
        
        # Actualizar cache
        _TASAS_CACHE['tasas'] = tasas
        _TASAS_CACHE['timestamp'] = datetime.now()
        
        logger.info(f"✅ Tasas actualizadas: USD Compra {tasas.get('USD_compra')}, Venta {tasas.get('USD_venta')}")
        return tasas
        
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Error obteniendo tasas de cambio: {e}")
        # Usar tasas por defecto si hay error
        tasas_default = {
            'USD_compra': 58.5,
            'USD_venta': 59.5,
            'EUR_compra': 70.0,
            'EUR_venta': 75.0,
            'actualizado': datetime.now().isoformat(),
            'fuente': 'default_fallback'
        }
        _TASAS_CACHE['tasas'] = tasas_default
        _TASAS_CACHE['timestamp'] = datetime.now()
        return tasas_default

def convertir_a_dop(monto: float, moneda: str, tasas: Dict[str, float]) -> Dict[str, Any]:
    """
    Convierte montos de USD/EUR a DOP
    Returns:
        Dict con monto convertido y detalles de conversión
    """
    if moneda == "DOP":
        return {
            "monto_original": monto,
            "moneda_original": moneda,
            "monto_dop": monto,
            "tasa_aplicada": 1.0,
            "conversion_requerida": False
        }
    
    conversion_info = {
        "monto_original": monto,
        "moneda_original": moneda,
        "conversion_requerida": True
    }
    
    if moneda == "USD":
        # Usar tasa de venta (para convertir USD a DOP)
        tasa = tasas.get('USD_venta', 59.5)
        conversion_info.update({
            "monto_dop": round(monto * tasa, 2),
            "tasa_aplicada": tasa,
            "tipo_tasa": "venta",
            "descripcion": f"USD → DOP (tasa venta: {tasa})"
        })
    elif moneda == "EUR":
        # Usar tasa de venta (para convertir EUR a DOP)
        tasa = tasas.get('EUR_venta', 75.0)
        conversion_info.update({
            "monto_dop": round(monto * tasa, 2),
            "tasa_aplicada": tasa,
            "tipo_tasa": "venta",
            "descripcion": f"EUR → DOP (tasa venta: {tasa})"
        })
    
    return conversion_info

def analizar_riesgo(monto_dop: float, hora: int, pais: str, moneda_original: str) -> Dict[str, Any]:
    """Analiza múltiples factores de riesgo para la transacción"""
    factores_riesgo = []
    score_riesgo = 0
    
    # Análisis de monto en DOP
    if monto_dop > 10000:
        factores_riesgo.append("MONTO_ELEVADO")
        score_riesgo += 2
    elif monto_dop < 50:
        factores_riesgo.append("MONTO_MUY_BAJO")
        score_riesgo += 1
    
    # Análisis de hora
    if 0 <= hora <= 6:
        factores_riesgo.append("HORARIO_NOCTURNO")
        score_riesgo += 1
    elif hora >= 22:
        factores_riesgo.append("HORARIO_NOCTURNO_TARDIO")
        score_riesgo += 1
    
    # Análisis por país
    paises_alto_riesgo = ["VE", "HT"]  # Ejemplo: Venezuela y Haití
    if pais in paises_alto_riesgo:
        factores_riesgo.append("PAIS_ALTO_RIESGO")
        score_riesgo += 2
    elif pais not in ["DO", "US"]:
        factores_riesgo.append("PAIS_RIESGO_MEDIO")
        score_riesgo += 1
    
    # Análisis por moneda
    if moneda_original != "DOP":
        factores_riesgo.append("TRANSACCION_DIVISA")
        score_riesgo += 1
    
    # Combinación sospechosa
    if monto_dop > 8000 and (hora <= 6 or hora >= 22):
        factores_riesgo.append("MONTO_ALTO_HORARIO_SOSPECHOSO")
        score_riesgo += 2
    
    # Transacción en divisa + monto alto
    if moneda_original != "DOP" and monto_dop > 15000:
        factores_riesgo.append("DIVISA_MONTO_ELEVADO")
        score_riesgo += 2
    
    return {
        "factores_riesgo": factores_riesgo,
        "score_riesgo": score_riesgo,
        "nivel_riesgo": "ALTO" if score_riesgo >= 3 else "MEDIO" if score_riesgo >= 1 else "BAJO"
    }

def detectar_fraude(cliente_id: str, monto: float, moneda: str, hora: int, pais: str) -> dict:
    """
    Detecta fraude con soporte para múltiples monedas
    """
    # Obtener tasas de cambio actualizadas
    tasas = obtener_tasas_cambio()
    
    # Convertir a DOP si es necesario
    conversion_info = convertir_a_dop(monto, moneda, tasas)
    monto_dop = conversion_info["monto_dop"]
    
    # Anonimizar cliente_id según Ley 172-13
    cliente_hash = hashlib.sha256(cliente_id.encode()).hexdigest()[:16]

    # Predecir con modelo ML (usando monto en DOP)
    features = pd.DataFrame([[monto_dop, hora]], columns=["monto","hora"])
    pred = model.predict(features)[0]  # -1 = anomalía
    score = model.decision_function(features)[0]
    
    # Convertir score a probabilidad (0-1)
    probabilidad_fraude = max(0, min(1, (0.5 - score) * 2))
    
    # Análisis de riesgo detallado
    analisis_riesgo = analizar_riesgo(monto_dop, hora, pais, moneda)
    
    # Determinar si es fraude basado en ML y reglas de negocio
    es_fraude_ml = pred == -1
    es_fraude_reglas = analisis_riesgo["nivel_riesgo"] == "ALTO"
    es_fraude = es_fraude_ml or es_fraude_reglas
    
    # Mensaje descriptivo
    if es_fraude:
        if es_fraude_ml and es_fraude_reglas:
            mensaje = "ALERTA: Transacción identificada como fraudulenta por modelo ML y reglas de negocio"
        elif es_fraude_ml:
            mensaje = "ALERTA: Patrón anómalo detectado por modelo de Machine Learning"
        else:
            mensaje = "ALERTA: Múltiples factores de riesgo identificados"
    else:
        mensaje = "Transacción dentro de parámetros normales"
    
    # Recomendación basada en riesgo
    if es_fraude:
        recomendacion = "Recomendación: Revisar transacción manualmente y contactar al cliente"
    elif analisis_riesgo["nivel_riesgo"] == "MEDIO":
        recomendacion = "Recomendación: Monitorear transacción y verificar con el cliente"
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
        "timestamp": datetime.utcnow().isoformat(),
        "conversion_moneda": conversion_info,
        "tasas_actualizadas": tasas.get('actualizado', ''),
        "datos_recibidos": {
            "cliente_id_length": len(cliente_id),
            "monto_original": float(monto),
            "moneda_original": moneda,
            "hora_transaccion": hora,
            "pais_origen": pais
        }
    }

    if resultado["es_fraude"]:
        _registrar_alerta(resultado)
    
    return resultado

def _registrar_alerta(resultado):
    ruta = LOG_PATH

    if not os.path.exists(ruta) or os.path.getsize(ruta) == 0:
        data = []
    else:
        try:
            with open(ruta, "r", encoding='utf-8') as f:
                data = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            data = []

    data.append(resultado)

    with open(ruta, "w", encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False, default=str)

def obtener_estado_tasas() -> Dict[str, Any]:
    """Obtiene el estado actual de las tasas de cambio"""
    tasas = obtener_tasas_cambio()
    return {
        "tasas_actuales": tasas,
        "cache_actualizado": _TASAS_CACHE['timestamp'].isoformat() if _TASAS_CACHE['timestamp'] else None,
        "estado": "activo" if tasas else "error"
    }

def cerrar_modelo():
    """Función para limpieza de recursos"""
    _TASAS_CACHE['tasas'] = None
    _TASAS_CACHE['timestamp'] = None
# [file content end]