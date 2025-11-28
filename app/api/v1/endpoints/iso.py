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


@router.post("/analyze-trnx", response_model=TransaccionResponse)
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
    risk = resultado["risk"]
    ofac = resultado["ofac"]

    return TransaccionResponse(
        is_fraud=risk["is_fraud"],
        fraud_prob=risk["fraud_prob"],
        risk_level=risk["risk_level"],
        risk_factor=risk["risk_factor"],
        message=risk["message"],
        advice=risk["advice"],
        customer_hash=risk["customer_hash"],
        anomaly_score=risk["anomaly_score"],
        timestamp=risk["timestamp"],
        data_analyzed={
            "src_amount": float(db_tx.i_0004_amount_transaction) / 100 if db_tx.i_0004_amount_transaction else 0.0,
            "tar_amount": float(db_tx.monto_dop_calculado or 0),
            "currency_tx": tx.i_0049_currency_code_tx,
            "time_local": tx.i_0012_time_local,
        },
        exchange=resultado["exchange"],
        ofac=resultado["ofac"],
        trnx_db_id=db_tx.id,
    )
