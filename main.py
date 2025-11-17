# [file name]: main.py
# [file content begin]
from fastapi import FastAPI, HTTPException, Depends, Request
from pydantic import BaseModel
from typing import Dict, Any
import logging
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

# --- Nuevas importaciones ---
from config import settings
from database import get_db, init_db, engine, Base
import db_models
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
    strategy="fixed-window" # o "moving-window"
)

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="API de Detección de Fraude Bancario Multi-Moneda",
    description="Sistema de detección de transacciones fraudulentas con soporte para DOP, USD y EUR",
    version="4.0.0-DB" # Nueva versión
)

# Aplicar el manejador de rate limit a la app
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


@app.on_event("startup")
async def startup_event():
    """Evento al iniciar la aplicación"""
    logger.info("🚀 API de Detección de Fraude Multi-Moneda iniciada")
    
    # Conectar a Redis
    try:
        app.state.redis = aioredis.from_url(settings.REDIS_URL, encoding="utf-8", decode_responses=True)
        await app.state.redis.ping()
        logger.info("✅ Conectado a Redis para Rate Limiting")
    except Exception as e:
        logger.error(f"❌ Error conectando a Redis: {e}")
        app.state.redis = None # Continuar sin rate limiting si falla
    
    # Inicializar Base de Datos (solo en dev, usar Alembic en prod)
    logger.info("🔄 Inicializando conexión a la base de datos...")
    await init_db()
    
    # Precargar tasas de cambio
    logger.info("📊 Cargando modelo ML y tasas de cambio...")
    await asyncio.to_thread(detector.obtener_tasas_cambio) # Ejecutar en thread
    
    # Precargar monedas
    await pre_cargar_monedas()

@app.on_event("shutdown")
async def shutdown_event():
    """Evento al cerrar la aplicación"""
    if app.state.redis:
        await app.state.redis.close()
        logger.info("🔌 Desconectado de Redis")
        
    await engine.dispose() # Cerrar pool de conexiones de DB
    logger.info("🛑 Cerrando API de Detección de Fraude")
    detector.cerrar_modelo()

async def pre_cargar_monedas():
    """Carga las monedas básicas en la DB si no existen"""
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
                    db_moneda = db_models.Currency(**m)
                    db.add(db_moneda)
                    logger.info(f"Cargando moneda: {m['code_alpha']}")
            except Exception as e:
                logger.warning(f"No se pudo cargar moneda {m['code_alpha']}: {e}")
                await db.rollback() # Ignorar si ya existe (por si acaso)
        try:
            await db.commit()
        except Exception:
            await db.rollback()

async def obtener_datos_detector_iso(tx: ISO8583Transaction, db: AsyncSession) -> dict:
    """Extrae y transforma datos de ISO8583 para el detector.py"""
    
    # 1. Obtener Moneda (de 840 -> "USD")
    stmt = select(db_models.Currency).where(db_models.Currency.code_numeric == tx.i_0049_currency_code_tx)
    db_currency = (await db.execute(stmt)).scalars().first()
    moneda_alpha = db_currency.code_alpha if db_currency else "USD" # Fallback
    
    # 2. Obtener Monto (de "000000015050" -> 150.50)
    monto_str = tx.i_0004_amount_transaction
    monto = float(f"{monto_str[:-2]}.{monto_str[-2:]}")
    
    # 3. Obtener Hora (de "130930" -> 13)
    hora = int(tx.i_0012_time_local[:2])
    
    # 4. Obtener Cliente ID (Buscando PAN en la DB)
    stmt_card = select(db_models.Card).where(db_models.Card.pan == tx.i_0002_pan).options(
        selectinload(db_models.Card.account).selectinload(db_models.Account.customer)
    )
    db_card = (await db.execute(stmt_card)).scalars().first()
    
    cliente_id = "UNKNOWN_CUSTOMER"
    card_db_id = None
    if db_card and db_card.account and db_card.account.customer:
        cliente_id = db_card.account.customer.customer_ref_id
        card_db_id = db_card.id
    else:
        # Si la tarjeta no existe, la creamos (o podrías rechazar)
        # Por simplicidad, la omitimos pero guardamos el PAN
        logger.warning(f"PAN no encontrado en DB: {tx.i_0002_pan[-4:]}")

    # 5. Obtener País (Extrayendo de nombre de comercio)
    # Esto es una heurística; en un sistema real, tendrías el MCC o país del adquirente
    pais_origen = "DO" # Default
    try:
        partes_loc = tx.i_0043_card_acceptor_name_loc.split(',')
        if len(partes_loc) > 2:
            pais_iso = partes_loc[-1].strip().upper()
            if len(pais_iso) == 2:
                pais_origen = pais_iso
    except Exception:
        pass # Usar default
        
    return {
        "cliente_id": cliente_id,
        "monto": monto,
        "moneda": moneda_alpha,
        "hora": hora,
        "pais": pais_origen,
        "card_db_id": card_db_id # ID de la tarjeta en nuestra DB
    }


@app.post("/analizar-iso", response_model=TransaccionResponse, summary="Analizar transacción ISO 8583 para fraude")
@limiter.limit("100/minute") # Límite por IP
async def analizar_transaccion_iso(
    tx_request: ISO8583Transaction, 
    request: Request, 
    db: AsyncSession = Depends(get_db)
):
    """
    Analiza una transacción bancaria (formato ISO 8583) para detectar fraude.
    Convierte monedas, guarda la transacción en la BD y retorna el análisis.
    """
    try:
        logger.info(f"Analizando TX ISO: STAN {tx_request.i_0011_stan}, TID {tx_request.i_0041_card_acceptor_tid}")
        
        # 1. Convertir datos de ISO 8583 al formato que entiende el detector
        datos_detector = await obtener_datos_detector_iso(tx_request, db)
        
        # 2. Llamar al detector (código síncrono, ejecutar en thread)
        resultado = await asyncio.to_thread(
            detector.detectar_fraude,
            cliente_id=datos_detector["cliente_id"],
            monto=datos_detector["monto"],
            moneda=datos_detector["moneda"],
            hora=datos_detector["hora"],
            pais=datos_detector["pais"]
        )
        
        # 3. Guardar la transacción y el resultado en la base de datos
        db_transaccion = db_models.Transaction(
            card_id=datos_detector["card_db_id"], # Puede ser None si la tarjeta no existe
            
            # --- Datos ISO ---
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
            i_0032_acquiring_inst_id=tx_request.i_0032_acquiring_inst_id,
            i_0035_track_2_data=tx_request.i_0035_track_2_data,
            i_0041_card_acceptor_tid=tx_request.i_0041_card_acceptor_tid,
            i_0042_card_acceptor_mid=tx_request.i_0042_card_acceptor_mid,
            i_0043_card_acceptor_name_loc=tx_request.i_0043_card_acceptor_name_loc,
            i_0049_currency_code_tx=tx_request.i_0049_currency_code_tx,
            i_0062_private_use_field=tx_request.i_0062_private_use_field,
            i_0128_mac=tx_request.i_0128_mac,
            
            # --- Resultados del Análisis ---
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
        
        # 4. Preparar respuesta al cliente
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
            transaction_db_id=db_transaccion.id # Devolver el ID de la transacción en la DB
        )
        
        logger.info(f"✅ Análisis ISO completado (ID: {db_transaccion.id}). Fraude: {resultado['es_fraude']}, Riesgo: {resultado['analisis_riesgo']['nivel_riesgo']}")
        
        return respuesta
        
    except Exception as e:
        logger.error(f"❌ Error analizando transacción ISO: {str(e)}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {str(e)}")


@app.get("/tasas-cambio", summary="Obtener tasas de cambio actuales")
@limiter.limit("30/minute")
async def obtener_tasas(request: Request):
    """Obtiene las tasas de cambio actuales desde el BHD"""
    try:
        tasas_info = await asyncio.to_thread(detector.obtener_estado_tasas)
        return {
            "status": "success",
            "tasas": tasas_info["tasas_actuales"],
            "actualizado": tasas_info["cache_actualizado"],
            "fuente": "BHD Leon API"
        }
    except Exception as e:
        logger.error(f"❌ Error obteniendo tasas: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error obteniendo tasas de cambio: {str(e)}")

@app.get("/health", response_model=HealthCheck)
@limiter.limit("60/minute")
async def health_check(request: Request, db: AsyncSession = Depends(get_db)):
    """Endpoint de salud del servicio con estado de DB y tasas"""
    
    # Verificar DB
    db_ok = False
    try:
        await db.execute(select(1))
        db_ok = True
    except Exception as e:
        logger.error(f"❌ Health check DB fallido: {e}")
        
    tasas_info = await asyncio.to_thread(detector.obtener_estado_tasas)
    
    return {
        "status": "healthy" if db_ok and tasas_info["estado"] == "activo" else "degraded",
        "timestamp": detector.datetime.utcnow().isoformat(),
        "service": "fraud-detection-api-multi-currency",
        "version": "4.0.0-DB",
        "db_status": "healthy" if db_ok else "unhealthy",
        "tasas_cambio": {
            "estado": tasas_info["estado"],
            "actualizado": tasas_info["cache_actualizado"]
        }
    }

@app.get("/")
async def root():
    return {
        "mensaje": "API de Detección de Fraude Bancario Multi-Moneda - República Dominicana",
        "version": "4.0.0-DB",
        "estado": "Operativo",
        "monedas_soportadas": ["DOP", "USD", "EUR"],
        "documentacion": "/docs",
        "endpoints": {
            "analizar_iso": "POST /analizar-iso",
            "tasas_cambio": "GET /tasas-cambio", 
            "health": "GET /health",
            "docs": "GET /docs"
        }
    }

# (Opcional: puedes mantener el endpoint /analizar original si quieres)
# @app.post("/analizar", response_model=TransaccionResponse, summary="Analizar transacción (simple)")
# @limiter.limit("100/minute")
# async def analizar_transaccion_simple(
#     transaccion: TransaccionSimple, 
#     request: Request
# ):
#     ... (lógica original) ...
# [file content end]