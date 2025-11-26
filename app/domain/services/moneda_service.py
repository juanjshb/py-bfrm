# app/domain/services/moneda_service.py
from typing import Tuple

from app.infra.detectors.tasas import obtener_tasas_cambio, convertir_a_dop


def normalizar_moneda(codigo_iso_numerico: str | None) -> str:
    """Mapea código ISO numérico a texto, simplificado."""
    if codigo_iso_numerico == "840":
        return "USD"
    if codigo_iso_numerico == "978":
        return "EUR"
    return "DOP"


def convertir_monto(
    monto_iso: str,
    codigo_iso_numerico: str | None,
) -> Tuple[float, dict]:
    monto = float(monto_iso) / 100 if monto_iso else 0.0
    moneda = normalizar_moneda(codigo_iso_numerico)
    tasas = obtener_tasas_cambio()
    if tasas:
        conv = convertir_a_dop(monto, moneda, tasas)
        return conv["monto_dop"], conv
    else:
        return monto, {
            "monto_original": monto,
            "moneda_original": moneda,
            "monto_dop": monto,
            "tasa_aplicada": 1.0,
            "tipo_tasa": "sin_tasas",
            "conversion_requerida": False,
        }
