# [file name]: main.py
# [file content begin]
from fastapi import FastAPI, HTTPException, Depends, Request
from pydantic import BaseModel
from typing import Dict, Any
import logging
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy import func, desc
import datetime

# --- Importaciones ---
from config import settings
from database import get_db, init_db, engine, Base
import db_models # Importar todos los modelos
import detector
from models import (
    ISO8583Transaction, TransaccionSimple, TransaccionResponse, 
    HealthCheck, TasasCambio
)

# --- Configuración de Rate Limiting ---
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import redis.asyncio as aioredis

limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=settings.REDIS_URL,
    storage_options={"socket_timeout": 5},
    strategy="fixed-window"
)

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="API de Detección de Fraude Bancario Multi-Moneda",
    description="Sistema de detección con análisis de historial de cliente y reglas de comercio",
    version="5.0-Contextual" # Nueva versión
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


@app.on_event("startup")
async def startup_event():
    # ... (lógica de startup sin cambios, incluyendo pre_cargar_monedas) ...
    logger.info("🚀 API de Detección de Fraude Multi-Moneda iniciada")
    try:
        app.state.redis = aioredis.from_url(settings.REDIS_URL, encoding="utf-8", decode_responses=True)
        await app.state.redis.ping()
        logger.info("✅ Conectado a Redis para Rate Limiting")
    except Exception as e:
        logger.error(f"❌ Error conectando a Redis: {e}")
        app.state.redis = None
    
    logger.info("🔄 Inicializando conexión a la base de datos...")
    await init_db()
    
    logger.info("📊 Cargando modelo ML y tasas de cambio...")
    await asyncio.to_thread(detector.obtener_tasas_cambio)
    await pre_cargar_monedas() # Definida abajo

async def pre_cargar_monedas():
    # ... (sin cambios) ...
    monedas = [
        {"code_numeric": "214", "code_alpha": "DOP", "name": "Peso Dominicano", "decimals": 2},
        {"code_numeric": "840", "code_alpha": "USD", "name": "Dólar Estadounidense", "decimals": 2},
        {"code_numeric": "978", "code_alpha": "EUR", "name": "Euro", "decimals": 2},
    ]
    async for db in get_db():
        for m in monedas:
            try:
                stmt = select(db_models.Currency).where(db_models.Currency.code_numeric == m["code_numeric"])
                existe = (await db.execute(stmt)).scalars().first()
                if not existe:
                    db.add(db_models.Currency(**m))
            except Exception: pass
        try: await db.commit()
        except Exception: await db.rollback()


async def _enrich_transaction_data(tx: ISO8583Transaction, db: AsyncSession) -> dict:
    """
    Función de orquestación: busca todos los datos contextuales de la DB.
    """
    enrichment_data = {
        "basic_info": {},
        "mcc_info": None,
        "mid_info": None,
        "client_profile": None
    }
    
    # 1. Obtener Moneda
    stmt_currency = select(db_models.Currency).where(db_models.Currency.code_numeric == tx.i_0049_currency_code_tx)
    db_currency = (await db.execute(stmt_currency)).scalars().first()
    moneda_alpha = db_currency.code_alpha if db_currency else "USD"
    
    # 2. Obtener Monto
    monto_str = tx.i_0004_amount_transaction
    monto = float(f"{monto_str[:-2]}.{monto_str[-2:]}")
    
    # 3. Obtener Hora
    hora = int(tx.i_0012_time_local[:2])
    
    # 4. Obtener País (Heurística)
    pais_origen = "DO" # Default
    try:
        partes_loc = tx.i_0043_card_acceptor_name_loc.split(',')
        if len(partes_loc) > 2:
            pais_iso = partes_loc[-1].strip().upper()
            if len(pais_iso) == 2: pais_origen = pais_iso
    except Exception: pass
    
    enrichment_data["basic_info"] = {
        "monto": monto,
        "moneda": moneda_alpha,
        "hora": hora,
        "pais": pais_origen
    }
    
    # 5. Buscar Cliente y Perfil Histórico
    stmt_card = select(db_models.Card).where(db_models.Card.pan == tx.i_0002_pan).options(
        selectinload(db_models.Card.account).selectinload(db_models.Account.customer)
    )
    db_card = (await db.execute(stmt_card)).scalars().first()
    
    cliente_id = "UNKNOWN_CUSTOMER"
    card_db_id = None
    
    if db_card and db_card.account and db_card.account.customer:
        db_customer = db_card.account.customer
        cliente_id = db_customer.customer_ref_id
        card_db_id = db_card.id
        
        # --- Construir Perfil de Cliente ---
        one_hour_ago = datetime.datetime.utcnow() - datetime.timedelta(hours=1)
        
        # Historial (transacciones pasadas de *esta* tarjeta)
        stmt_history = select(db_models.Transaction).where(
            db_models.Transaction.card_id == card_db_id
        ).order_by(desc(db_models.Transaction.tx_timestamp_utc)).limit(20)
        
        # Conteo de tx en la última hora
        stmt_tx_count_hour = select(func.count(db_models.Transaction.id)).where(
            db_models.Transaction.card_id == card_db_id,
            db_models.Transaction.tx_timestamp_utc >= one_hour_ago
        )
        
        history_results = (await db.execute(stmt_history)).scalars().all()
        tx_count_last_hour = (await db.execute(stmt_tx_count_hour)).scalar_one()
        
        countries_used = set([pais_origen])
        total_amount_dop = 0
        
        if history_results:
            for h_tx in history_results:
                countries_used.add("DO") # Asumir DO si no hay país
                total_amount_dop += h_tx.monto_dop_calculado or 0
            
            avg_amount_dop = total_amount_dop / len(history_results)
        else:
            avg_amount_dop = 0
            
        enrichment_data["client_profile"] = {
            "avg_amount_dop": float(avg_amount_dop),
            "countries_used": list(countries_used),
            "tx_count_last_hour": tx_count_last_hour
        }
    
    enrichment_data["basic_info"]["cliente_id"] = cliente_id
    enrichment_data["basic_info"]["card_db_id"] = card_db_id
    
    # 6. Buscar Reglas de MCC
    if tx.i_0026_mcc:
        stmt_mcc = select(db_models.MccCode).where(db_models.MccCode.mcc == tx.i_0026_mcc)
        db_mcc = (await db.execute(stmt_mcc)).scalars().first()
        if db_mcc:
            enrichment_data["mcc_info"] = {
                "mcc": db_mcc.mcc,
                "risk_level": db_mcc.risk_level,
                "description": db_mcc.description
            }

    # 7. Buscar Reglas de MID
    if tx.i_0042_card_acceptor_mid:
        stmt_mid = select(db_models.MonitoredMerchant).where(db_models.MonitoredMerchant.mid == tx.i_0042_card_acceptor_mid)
        db_mid = (await db.execute(stmt_mid)).scalars().first()
        if db_mid:
            enrichment_data["mid_info"] = {
                "mid": db_mid.mid,
                "status": db_mid.status,
                "name": db_mid.name
            }
            
    return enrichment_data


@app.post("/analizar-iso", response_model=TransaccionResponse, summary="Analizar transacción ISO 8583 (Con contexto)")
@limiter.limit("100/minute")
async def analizar_transaccion_iso(
    tx_request: ISO8583Transaction, 
    request: Request, 
    db: AsyncSession = Depends(get_db)
):
    """
    Analiza una transacción ISO 8583 usando contexto de cliente y reglas de comercio.
    """
    try:
        logger.info(f"Analizando TX ISO: STAN {tx_request.i_0011_stan}, MCC {tx_request.i_0026_mcc}")
        
        # 1. Enriquecer datos (Consultar DB para historial, MCC, MID)
        context_data = await _enrich_transaction_data(tx_request, db)
        
        basic_info = context_data["basic_info"]
        
        # 2. Llamar al detector con todo el contexto
        resultado = await asyncio.to_thread(
            detector.detectar_fraude,
            cliente_id=basic_info["cliente_id"],
            monto=basic_info["monto"],
            moneda=basic_info["moneda"],
            hora=basic_info["hora"],
            pais=basic_info["pais"],
            mcc_info=context_data["mcc_info"],
            mid_info=context_data["mid_info"],
            client_profile=context_data["client_profile"]
        )
        
        # 3. Guardar la transacción y el resultado en la BD
        db_transaccion = db_models.Transaction(
            card_id=basic_info["card_db_id"],
            mti=tx_request.mti,
            i_0002_pan=tx_request.i_0002_pan,
            i_0003_processing_code=tx_request.i_0003_processing_code,
            i_0004_amount_transaction=tx_request.i_0004_amount_transaction,
            i_0007_transmission_datetime=tx_request.i_0007_transmission_datetime,
            i_0011_stan=tx_request.i_0011_stan,
            i_0012_time_local=tx_request.i_0012_time_local,
            i_0013_date_local=tx_request.i_0013_date_local,
            i_0022_pos_entry_mode=tx_request.i_0022_pos_entry_mode,
            i_0024_function_code_nii=tx_request.i_0024_function_code_nii,
            i_0025_pos_condition_code=tx_request.i_0025_pos_condition_code,
            i_0026_mcc=tx_request.i_0026_mcc, # <-- Guardar MCC
            i_0032_acquiring_inst_id=tx_request.i_0032_acquiring_inst_id,
            i_0035_track_2_data=tx_request.i_0035_track_2_data,
            i_0041_card_acceptor_tid=tx_request.i_0041_card_acceptor_tid,
            i_0042_card_acceptor_mid=tx_request.i_0042_card_acceptor_mid,
            i_0043_card_acceptor_name_loc=tx_request.i_0043_card_acceptor_name_loc,
            i_0049_currency_code_tx=tx_request.i_0049_currency_code_tx,
            i_0062_private_use_field=tx_request.i_0062_private_use_field,
            i_0128_mac=tx_request.i_0128_mac,
            
            # Resultados del Análisis
            es_fraude=resultado["es_fraude"],
            probabilidad_fraude=resultado["probabilidad_fraude"],
            nivel_riesgo=resultado["analisis_riesgo"]["nivel_riesgo"],
            factores_riesgo=",".join(resultado["analisis_riesgo"]["factores_riesgo"]),
            mensaje_analisis=resultado["mensaje"],
            recomendacion_analisis=resultado["recomendacion"],
            analisis_timestamp=datetime.datetime.fromisoformat(resultado["timestamp"]),
            monto_dop_calculado=resultado["monto_dop"]
        )
        
        db.add(db_transaccion)
        await db.commit()
        await db.refresh(db_transaccion)
        
        # 4. Preparar respuesta
        respuesta = TransaccionResponse(
            fraude_detectado=resultado["es_fraude"],
            probabilidad_fraude=resultado["probabilidad_fraude"],
            nivel_riesgo=resultado["analisis_riesgo"]["nivel_riesgo"],
            factores_riesgo=resultado["analisis_riesgo"]["factores_riesgo"],
            mensaje=resultado["mensaje"],
            recomendacion=resultado["recomendacion"],
            cliente_hash=resultado["cliente_hash"],
            score_anomalia=resultado["score_anomalia"],
            timestamp=resultado["timestamp"],
            datos_analizados=resultado["datos_recibidos"],
            conversion_moneda=resultado["conversion_moneda"],
            transaction_db_id=db_transaccion.id
        )
        
        logger.info(f"✅ Análisis ISO completado (ID: {db_transaccion.id}). Fraude: {resultado['es_fraude']}, Riesgo: {resultado['analisis_riesgo']['nivel_riesgo']}")
        
        return respuesta
        
    except Exception as e:
        logger.error(f"❌ Error analizando transacción ISO: {str(e)}", exc_info=True)
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {str(e)}")

# ... (endpoints /tasas-cambio, /health, / sin cambios) ...
# [file content end]
