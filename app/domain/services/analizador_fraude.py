# app/domain/services/analizador_fraude.py
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infra.db.models.card import Card
from app.infra.db.models.account import Account
from app.infra.db.models.customer import Customer
from app.infra.db.models.transaction import Transaction
from app.infra.detectors.fraude_model import analizar as analizar_core
from app.domain.services.historial_service import obtener_historial_cliente
from app.domain.services.merchant_service import obtener_contexto_merchant
from app.domain.services.moneda_service import convertir_monto
from app.schemas.iso_schemas import ISO8583Transaction


async def procesar_transaccion_iso(
    db: AsyncSession,
    tx: ISO8583Transaction,
) -> dict:
    ahora = datetime.utcnow()

    # 1) Convertir monto a DOP
    monto_dop, conversion = convertir_monto(
        tx.i_0004_amount_transaction,
        tx.i_0049_currency_code_tx,
    )

    # 2) Obtener tarjeta / cliente por pan_token (asumimos PAN ya tokenizado)
    stmt_card = select(Card).where(Card.pan_token == tx.i_0002_pan)
    res_card = await db.execute(stmt_card)
    card = res_card.scalars().first()

    customer_id = None
    pais = None
    if card and card.account:
        customer = card.account.customer
        if customer:
            customer_id = customer.id
            pais = customer.pais

    # Hora local para el modelo
    hora_local = int(tx.i_0012_time_local[:2]) if tx.i_0012_time_local else 0
    # Monto Origen para el modelo
    monto_src = float(tx.i_0004_amount_transaction) / 100 if tx.i_0004_amount_transaction else 0.0


    # 3) Ejecutar modelo de fraude
    riesgo = analizar_core(
        monto_src= monto_src,
        monto_dop=monto_dop,
        moneda=conversion["moneda_original"],
        hora_local=hora_local,
        pais_cliente=pais,
        customer_id=customer_id,
    )

    # 4) Historial
    hist_ctx = await obtener_historial_cliente(
        db=db,
        customer_id=customer_id,
        monto_actual_dop=monto_dop,
    )

    # 5) Contexto merchant
    merchant_ctx = await obtener_contexto_merchant(db, tx.i_0042_card_acceptor_mid)

    # 6) Guardar Transaction completa
    tx_dict = tx.model_dump()
    columnas_iso = {k: v for k, v in tx_dict.items() if k.startswith("i_") and v is not None}

    db_tx = Transaction(
        tx_timestamp_utc=ahora,
        card_id=card.id if card else None,
        mti=tx.mti,
        bitmap=tx.bitmap,
        **columnas_iso,
        es_fraude=riesgo["fraude_detectado"],
        probabilidad_fraude=riesgo["probabilidad_fraude"],
        nivel_riesgo=riesgo["nivel_riesgo"],
        factores_riesgo=",".join(riesgo["factores_riesgo"]),
        mensaje_analisis=riesgo["mensaje"],
        recomendacion_analisis=riesgo["recomendacion"],
        analisis_timestamp=ahora,
        monto_dop_calculado=monto_dop,
        historial_tx_24h=hist_ctx["tx_24h"],
        historial_tx_7d=hist_ctx["tx_7d"],
        monto_promedio_30d=hist_ctx["promedio_30d"],
        merchant_permitido=merchant_ctx["merchant_permitido"],
        mcc_permitido=merchant_ctx["mcc_permitido"],
    )

    db.add(db_tx)
    await db.commit()
    await db.refresh(db_tx)

    return {
        "db_tx": db_tx,
        "riesgo": riesgo,
        "historial": hist_ctx,
        "merchant_ctx": merchant_ctx,
        "conversion": conversion,
    }
