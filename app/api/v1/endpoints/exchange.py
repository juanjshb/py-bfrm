# app/api/v1/endpoints/exchange.py
from fastapi import APIRouter, HTTPException
from app.infra.detectors.tasas import (
    obtener_tasas_cambio,
    obtener_estado_tasas,
    convertir_a_dop
)
from app.infra.db.models.exchange import TasasCambio, ConversionResultado

router = APIRouter(tags=["exchange"])

@router.get("/exchange", response_model=TasasCambio)
def obtener_tasas_endpoint():
    estado = obtener_estado_tasas()

    if not estado["tasas_actuales"]:
        raise HTTPException(
            status_code=503,
            detail="No hay tasas disponibles temporalmente"
        )

    return {
        "rate": estado["tasas_actuales"],
        "timestamp": estado["cache_actualizado"],
        "status": estado["estado"],
    }


@router.get("/exchange/rate", response_model=ConversionResultado)
def convertir(monto: float, moneda: str):
    moneda = moneda.upper().strip()
    tasas = obtener_tasas_cambio()

    if not tasas:
        raise HTTPException(
            status_code=503,
            detail="No hay tasas disponibles para conversión"
        )

    resultado = convertir_a_dop(monto, moneda, tasas)
    return resultado
