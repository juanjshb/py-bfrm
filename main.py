# main.py
from fastapi import FastAPI, HTTPException, Depends, Request
from typing import Dict, Any, List, Optional
import logging
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.middleware import SlowAPIMiddleware
from slowapi.errors import RateLimitExceeded

from config import settings
from database import get_db, init_db, engine, Base
import db_models
import detector
from models import ISO8583Transaction, TransaccionResponse, HealthCheck, TasasCambio

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Rate Limiter
limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="Python - Banking Fraud Risk Monitor (py-bfrm)",
    version="3.0.0",
    description="Detección de fraude con ISO 8583, historial y MCC/Merchants parametrizables",
)

app.state.limiter = limiter
app.add_middleware(
    SlowAPIMiddleware,
)


@app.on_event("startup")
async def on_startup():
    # Crear tablas si no existen
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Base de datos inicializada")


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return HTTPException(
        status_code=429,
        detail="Demasiadas solicitudes desde esta IP. Intenta de nuevo más tarde.",
    )


async def _obtener_historial_cliente(
    db: AsyncSession,
    customer_id: Optional[int],
    monto_dop_actual: float,
) -> Dict[str, Any]:
    """
    Calcula métricas de historial del cliente:
      - tx_24h
      - tx_7d
      - monto_promedio_30d
    Basado en TODAS sus tarjetas/cuentas.
    """
    if not customer_id:
        return {
            "tx_24h": 0,
            "tx_7d": 0,
            "monto_promedio_30d": None,
            "monto_dop_actual": monto_dop_actual,
        }

    ahora = datetime.utcnow()
    hace_24h = ahora - timedelta(hours=24)
    hace_7d = ahora - timedelta(days=7)
    hace_30d = ahora - timedelta(days=30)

    # unir ctransactions -> ccardx -> caccounts -> ccustomers
    tx_query = (
        select(db_models.Transaction)
        .join(db_models.Card, db_models.Transaction.card_id == db_models.Card.id)
        .join(db_models.Account, db_models.Card.account_id == db_models.Account.id)
        .where(db_models.Account.customer_id == customer_id)
        .order_by(db_models.Transaction.tx_timestamp_utc.desc())
    )

    result = await db.execute(tx_query)
    txs: List[db_models.Transaction] = result.scalars().all()

    tx_24h = 0
    tx_7d = 0
    montos_30d: List[float] = []

    for t in txs:
        if not t.tx_timestamp_utc:
            continue
        if t.tx_timestamp_utc >= hace_24h:
            tx_24h += 1
        if t.tx_timestamp_utc >= hace_7d:
            tx_7d += 1
        if t.tx_timestamp_utc >= hace_30d and t.monto_dop_calculado:
            montos_30d.append(float(t.monto_dop_calculado))

    monto_promedio_30d = sum(montos_30d) / len(montos_30d) if montos_30d else None

    return {
        "tx_24h": tx_24h,
        "tx_7d": tx_7d,
        "monto_promedio_30d": monto_promedio_30d,
        "monto_dop_actual": monto_dop_actual,
    }


async def _obtener_contexto_merchant(
    db: AsyncSession, mid: Optional[str]
) -> Dict[str, Any]:
    if not mid:
        return {
            "merchant_permitido": None,
            "mcc_permitido": None,
            "riesgo_merchant": None,
            "riesgo_mcc": None,
        }

    merchant_stmt = select(db_models.Merchant).where(db_models.Merchant.mid == mid)
    merchant = (await db.execute(merchant_stmt)).scalars().first()

    if not merchant:
        # Merchant no registrado
        return {
            "merchant_permitido": False,
            "mcc_permitido": None,
            "riesgo_merchant": None,
            "riesgo_mcc": None,
        }

    # Obtener información de MCC (si existe)
    mcc_stmt = select(db_models.Mcc).where(db_models.Mcc.mcc == merchant.mcc)
    mcc = (await db.execute(mcc_stmt)).scalars().first()

    return {
        "merchant_permitido": bool(merchant.permitido),
        "mcc_permitido": bool(mcc.permitido) if mcc else None,
        "riesgo_merchant": merchant.riesgo_nivel,
        "riesgo_mcc": mcc.riesgo_nivel if mcc else None,
    }


def _parsear_monto_iso(i_0004_amount_transaction: str) -> float:
    """
    Campo 4 ISO 8583: 12 dígitos, normalmente 2 decimales implícitos.
    Ej: '000000015050' => 150.50
    """
    limpio = i_0004_amount_transaction.strip().lstrip("0") or "0"
    valor = int(limpio)
    return valor / 100.0


def _parsear_hora_local(date_local: str, time_local: str) -> int:
    """
    Extrae la hora (0-23) a partir del campo 12/13 local.
    i_0012_time_local: HHMMSS
    """
    if len(time_local) >= 2:
        try:
            return int(time_local[:2])
        except ValueError:
            return 0
    return 0


@app.post(
    "/analizar-iso",
    response_model=TransaccionResponse,
    summary="Analizar transacción ISO 8583 con historial y MCC/Merchant",
)
@limiter.limit("60/minute")
async def analizar_iso(
    tx: ISO8583Transaction, request: Request, db: AsyncSession = Depends(get_db)
):
    # 1. Tasas de cambio y monto
    tasas = detector.obtener_tasas_cambio()
    moneda_tx_alpha = "DOP"
    if tx.i_0049_currency_code_tx == "840":
        moneda_tx_alpha = "USD"
    elif tx.i_0049_currency_code_tx == "978":
        moneda_tx_alpha = "EUR"

    monto_original = _parsear_monto_iso(tx.i_0004_amount_transaction)
    conversion = detector.convertir_a_dop(
        monto_original,
        moneda_tx_alpha,
        tasas,
    )

    # 2. Buscar tarjeta -> cuenta -> cliente
    card_stmt = select(db_models.Card).where(
        db_models.Card.pan == tx.i_0002_pan
    )
    card = (await db.execute(card_stmt)).scalars().first()

    customer_id: Optional[int] = None
    customer_ref: Optional[str] = None

    if card and card.account and card.account.customer:
        customer_id = card.account.customer.id
        customer_ref = card.account.customer.customer_ref_id

    # 3. Historial por cliente
    hist_ctx = await _obtener_historial_cliente(
        db=db,
        customer_id=customer_id,
        monto_dop_actual=conversion["monto_dop"],
    )

    # 4. Merchant / MCC
    merchant_ctx = await _obtener_contexto_merchant(
        db=db, mid=tx.i_0042_card_acceptor_mid
    )

    # 5. Hora local y país
    hora_tx = _parsear_hora_local(tx.i_0013_date_local, tx.i_0012_time_local)
    name_loc = tx.i_0043_card_acceptor_name_loc

    riesgo = detector.analizar_riesgo(
        monto_dop=conversion["monto_dop"],
        moneda_original=conversion["moneda_original"],
        hora_tx=hora_tx,
        name_loc=name_loc,
        hist_ctx=hist_ctx,
        merchant_ctx=merchant_ctx,
    )

    # 6. Guardar en DB (ctransactions)
    ahora = datetime.utcnow()

    db_tx = db_models.Transaction(
        tx_timestamp_utc=ahora,
        card_id=card.id if card else None,
        mti=tx.mti,
        i_0002_pan=tx.i_0002_pan,
        i_0003_processing_code=tx.i_0003_processing_code,
        i_0004_amount_transaction=tx.i_0004_amount_transaction,
        i_0007_transmission_datetime=tx.i_0007_transmission_datetime,
        i_0011_stan=tx.i_0011_stan,
        i_0012_time_local=tx.i_0012_time_local,
        i_0013_date_local=tx.i_0013_date_local,
        i_0022_pos_entry_mode=tx.i_0022_pos_entry_mode,
        i_0024_function_code_nii=tx.i_0024_function_code_nii,
        i_0025_pos_condition_code=tx.i_0025_pos_condition_code,
        i_0032_acquiring_inst_id=tx.i_0032_acquiring_inst_id,
        i_0041_card_acceptor_tid=tx.i_0041_card_acceptor_tid,
        i_0042_card_acceptor_mid=tx.i_0042_card_acceptor_mid,
        i_0043_card_acceptor_name_loc=tx.i_0043_card_acceptor_name_loc,
        i_0049_currency_code_tx=tx.i_0049_currency_code_tx,
        es_fraude=riesgo["fraude_detectado"],
        probabilidad_fraude=riesgo["probabilidad_fraude"],
        nivel_riesgo=riesgo["nivel_riesgo"],
        factores_riesgo=",".join(riesgo["factores_riesgo"]),
        mensaje_analisis=riesgo["mensaje"],
        recomendacion_analisis=riesgo["recomendacion"],
        analisis_timestamp=ahora,
        monto_dop_calculado=conversion["monto_dop"],
        historial_tx_24h=hist_ctx["tx_24h"],
        historial_tx_7d=hist_ctx["tx_7d"],
        monto_promedio_30d=hist_ctx["monto_promedio_30d"],
        merchant_permitido=merchant_ctx.get("merchant_permitido"),
        mcc_permitido=merchant_ctx.get("mcc_permitido"),
    )

    db.add(db_tx)
    try:
        await db.commit()
        await db.refresh(db_tx)
    except Exception as e:
        await db.rollback()
        logger.error(f"Error guardando transacción: {e}")
        raise HTTPException(status_code=500, detail="Error guardando transacción")

    cliente_hash = detector.hash_cliente(customer_ref)

    resp = TransaccionResponse(
        fraude_detectado=riesgo["fraude_detectado"],
        probabilidad_fraude=riesgo["probabilidad_fraude"],
        nivel_riesgo=riesgo["nivel_riesgo"],
        factores_riesgo=riesgo["factores_riesgo"],
        mensaje=riesgo["mensaje"],
        recomendacion=riesgo["recomendacion"],
        cliente_hash=cliente_hash,
        score_anomalia=riesgo["score_anomalia"],
        timestamp=ahora.isoformat() + "Z",
        datos_analizados={
            "cliente_id_length": len(customer_ref) if customer_ref else 0,
            "monto_original": conversion["monto_original"],
            "moneda_original": conversion["moneda_original"],
            "hora_transaccion": hora_tx,
            "pais_origen": name_loc.split(",")[-1].strip()
            if name_loc and "," in name_loc
            else None,
        },
        conversion_moneda=conversion,
        transaction_db_id=db_tx.id,
    )
    return resp


@app.get("/tasas-cambio", response_model=TasasCambio)
@limiter.limit("30/minute")
async def get_tasas_cambio(request: Request):
    tasas = detector.obtener_tasas_cambio()
    ahora = datetime.utcnow().isoformat() + "Z"
    return TasasCambio(
        USD_compra=tasas.get("USD_compra", 0.0),
        USD_venta=tasas.get("USD_venta", 0.0),
        EUR_compra=tasas.get("EUR_compra", 0.0),
        EUR_venta=tasas.get("EUR_venta", 0.0),
        actualizado=ahora,
    )


@app.get("/health", response_model=HealthCheck)
async def health_check():
    ahora = datetime.utcnow().isoformat() + "Z"

    # DB check
    try:
        async with AsyncSession(engine) as session:
            await session.execute(select(func.count(db_models.Transaction.id)))
        db_status = "healthy"
    except Exception as e:
        logger.error(f"DB health check failed: {e}")
        db_status = "error"

    tasas_estado = detector.obtener_estado_tasas()

    return HealthCheck(
        status="healthy" if db_status == "healthy" else "degraded",
        timestamp=ahora,
        db_status=db_status,
        tasas_cambio={
            "estado": tasas_estado["estado"],
            "actualizado": tasas_estado["cache_actualizado"],
        },
    )


@app.get("/")
async def root():
    return {
        "service": "fraud-detection-api-multi-currency",
        "version": "3.0.0",
        "endpoints": {
            "analizar_iso": "POST /analizar-iso",
            "tasas_cambio": "GET /tasas-cambio",
            "health": "GET /health",
            "docs": "GET /docs",
        },
    }
