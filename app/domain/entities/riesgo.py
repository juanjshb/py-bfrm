# app/domain/entities/riesgo.py
from dataclasses import dataclass
from typing import List, Dict, Any


@dataclass
class ResultadoRiesgo:
    fraude_detectado: bool
    probabilidad_fraude: float
    nivel_riesgo: str
    factores_riesgo: List[str]
    mensaje: str
    recomendacion: str
    score_anomalia: float
    cliente_hash: str
    timestamp: str
    extra: Dict[str, Any]
