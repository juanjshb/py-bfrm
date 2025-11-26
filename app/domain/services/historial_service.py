# app/domain/services/historial_service.py
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.infra.db.models.transaction import Transaction
from app.infra.db.models.card import Card
from app.infra.db.models.account import Account
from app.infra.db.models.customer import Customer


async def obtener_historial_cliente(
    db: AsyncSession,
    customer_id: int | None,
    monto_actual_dop: float,
) -> dict:
    ahora = datetime.utcnow()
    if not customer_id:
        return {
            "tx_24h": 0,
            "tx_7d": 0,
            "promedio_30d": None,
            "monto_actual": monto_actual_dop,
        }

    hace_24h = ahora - timedelta(hours=24)
    hace_7d = ahora - timedelta(days=7)
    hace_30d = ahora - timedelta(days=30)

    stmt = (
        select(Transaction)
        .join(Card, Transaction.card_id == Card.id)
        .join(Account, Card.account_id == Account.id)
        .join(Customer, Account.customer_id == Customer.id)
        .where(Customer.id == customer_id)
    )
    res = await db.execute(stmt)
    txs = res.scalars().all()

    tx_24h = [t for t in txs if t.tx_timestamp_utc and t.tx_timestamp_utc >= hace_24h]
    tx_7d = [t for t in txs if t.tx_timestamp_utc and t.tx_timestamp_utc >= hace_7d]
    tx_30d = [t for t in txs if t.tx_timestamp_utc and t.tx_timestamp_utc >= hace_30d]

    montos_30 = []
    for t in tx_30d:
        try:
            if t.monto_dop_calculado is not None:
                montos_30.append(float(t.monto_dop_calculado))
        except Exception:
            continue

    promedio_30 = sum(montos_30) / len(montos_30) if montos_30 else None

    return {
        "tx_24h": len(tx_24h),
        "tx_7d": len(tx_7d),
        "promedio_30d": promedio_30,
        "monto_actual": monto_actual_dop,
    }
