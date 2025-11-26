# app/api/v1/endpoints/iso.py
from fastapi import APIRouter, Depends, HTTPException, Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.infra.db.session import get_db
from app.domain.services.analizador_fraude import procesar_transaccion_iso
from app.schemas.iso_schemas import ISO8583Transaction, TransaccionResponse

limiter = Limiter(key_func=get_remote_address)

router = APIRouter(tags=["iso"])


@router.post("/analizar-iso-trnx", response_model=TransaccionResponse)
@limiter.limit(settings.RATE_LIMIT)
async def analizar_iso(
    request: Request,
    tx: ISO8583Transaction,
    db: AsyncSession = Depends(get_db),
):
    try:
        resultado = await procesar_transaccion_iso(db, tx)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analizando transacción: {e}")

    db_tx = resultado["db_tx"]
    riesgo = resultado["riesgo"]

    return TransaccionResponse(
        fraude_detectado=riesgo["fraude_detectado"],
        probabilidad_fraude=riesgo["probabilidad_fraude"],
        nivel_riesgo=riesgo["nivel_riesgo"],
        factores_riesgo=riesgo["factores_riesgo"],
        mensaje=riesgo["mensaje"],
        recomendacion=riesgo["recomendacion"],
        cliente_hash=riesgo["cliente_hash"],
        score_anomalia=riesgo["score_anomalia"],
        timestamp=riesgo["timestamp"],
        datos_analizados={
            "monto_dop": float(db_tx.monto_dop_calculado or 0),
            "currency_tx": tx.i_0049_currency_code_tx,
            "hora_local": tx.i_0012_time_local,
        },
        conversion_moneda=resultado["conversion"],
        transaction_db_id=db_tx.id,
    )
