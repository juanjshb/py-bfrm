# app/api/v1/endpoints/auditoria.py
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.infra.db.session import get_db
from app.infra.db.models.transaction import Transaction

router = APIRouter(tags=["auditoria"])


@router.get("/auditoria/transactions")
async def listar_transacciones(limit: int = 50, db: AsyncSession = Depends(get_db)):
    stmt = (
        select(Transaction)
        .order_by(desc(Transaction.tx_timestamp_utc))
        .limit(limit)
    )
    res = await db.execute(stmt)
    txs = res.scalars().all()

    return [
        {
            "id": t.id,
            "timestamp": t.tx_timestamp_utc,
            "pan": t.i_0002_pan,
            "monto_dop": float(t.monto_dop_calculado or 0),
            "nivel_riesgo": t.nivel_riesgo,
            "es_fraude": t.es_fraude,
        }
        for t in txs
    ]
