# app/domain/services/analizador_fraude.py
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


from app.infra.cache.risk_factor_cache import risk_config
from app.infra.db.models.card import Card
from app.infra.db.models.account import Account
from app.infra.db.models.customer import Customer
from app.infra.db.models.transaction import Transaction
from app.infra.db.models.country import Country
from app.infra.db.models.risk_factors import RiskFactor, RiskFactorRule, RiskFactorCritical
from app.infra.detectors.fraude_model import analizar as analizar_core
from app.domain.services.historial_service import obtener_historial_cliente
from app.domain.services.merchant_service import obtener_contexto_merchant
from app.domain.services.moneda_service import convertir_monto
from app.schemas.iso_schemas import ISO8583Transaction
from app.infra.detectors.ofac_factor import aplicar_factor_ofac

async def obtener_listas_riesgo(db):
    result = await db.execute(
        select(Country.iso2, Country.risk_level)
    )
    rows = result.all()

    high = {r.iso2 for r in rows if r.risk_level.upper() == "HIGH"}
    medium = {r.iso2 for r in rows if r.risk_level.upper() == "MEDIUM"}

    return high, medium

def normalizar_lista_paises(valor) -> set[str]:
    """
    Acepta:
      - lista python (['VE','HT'])
      - string tipo 'VE,HT'
      - string tipo "['VE','HT']"
      - elementos con espacios
    Devuelve un set limpio: {'VE','HT'}
    """
    if not valor:
        return set()

    if isinstance(valor, list):
        items = valor
    elif isinstance(valor, set):
        items = list(valor)
    else:
        # string → homogenizar
        valor = valor.replace("[", "").replace("]", "").replace("'", "").replace('"', "")
        items = valor.split(",")

    # limpiar
    limpio = {
        item.strip().upper()
        for item in items
        if item and len(item.strip()) == 2
    }

    return limpio

async def cargar_risk_config(db: AsyncSession):
    # Pesos base
    rows = (await db.execute(select(RiskFactor))).scalars().all()
    risk_config.weights = {r.code: r.weight for r in rows if r.enabled}

    # Factores críticos
    rows = (await db.execute(select(RiskFactorCritical))).scalars().all()
    risk_config.critical = {r.factor_code for r in rows}

    # Reglas combinadas
    rows = (await db.execute(select(RiskFactorRule))).scalars().all()
    risk_config.rules = rows

    return risk_config

def extraer_pais_de_locator(de43: str | None) -> str:
    val = (de43 or "").strip()
    return val[-2:]


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

    # 2) Obtener tarjeta/cuenta/cliente por pan
    stmt_card = select(Card).where(Card.pan == tx.i_0002_pan)
    res_card = await db.execute(stmt_card)
    card = res_card.scalars().first()
    
    customer_id = None
    pais = None
    if card:
        stmt_account = select(Account).where(Account.id == card.account_id)
        res_account = await db.execute(stmt_account)
        account = res_account.scalars().first()
        if account:
            card.account = account
            stmt_customer = select(Customer).where(Customer.id == account.customer_id)
            res_customer = await db.execute(stmt_customer)
            customer = res_customer.scalars().first()
            if customer:
                card.account.customer = customer
                customer_id = customer.id
                pais = extraer_pais_de_locator(tx.i_0043_card_acceptor_name_loc)

    # Hora local para el modelo
    hora_local = int(tx.i_0012_time_local[:2]) if tx.i_0012_time_local else 0
    # Monto Origen para el modelo
    monto_src = float(tx.i_0004_amount_transaction) / 100 if tx.i_0004_amount_transaction else 0.0

    # Screening OFAC (si hay cliente)
    ofac_ctx = None
    if customer_id:
        ofac_ctx = {"score": 0.0, "factors": []}
        await aplicar_factor_ofac(db, customer, ofac_ctx)
    else:
        ofac_ctx = {"score": 0.0, "factors": []}

    # Risk countries
    hrc, mrc = await obtener_listas_riesgo(db)
    high_risk_countries = normalizar_lista_paises(hrc)
    medium_risk_countries = normalizar_lista_paises(mrc)

    risk_config = await cargar_risk_config(db)

    # 3) Ejecutar modelo de fraude
    riesgo = analizar_core(
        monto_src= monto_src,
        monto_dop=monto_dop,
        moneda=conversion["moneda_original"],
        hora_local=hora_local,
        pais_cliente=pais,
        customer_id=customer_id,
        hrc=high_risk_countries, 
        mrc=medium_risk_countries,
        risk_config=risk_config,
    )

    # 3.1) Merge OFAC al analisis de riesgo final
    if ofac_ctx["factors"]:
        for f in ofac_ctx["factors"]:
            if not f["code"] == "OFAC_CLEAR":
                riesgo["risk_factor"].append(f["code"])

        # full match = bloqueo completo
        if any(f["code"] == "OFAC_FULL_MATCH" for f in ofac_ctx["factors"]):
            riesgo["is_fraud"] = True
            riesgo["fraud_prob"] = 1.0
            riesgo["risk_level"] = "HIGH"
            riesgo["message"] = "El cliente coincide completamente con OFAC."
            riesgo["advice"] = "BLOCK"


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
        es_fraude=riesgo["is_fraud"],
        probabilidad_fraude=riesgo["fraud_prob"],
        nivel_riesgo=riesgo["risk_level"],
        factores_riesgo=",".join(riesgo["risk_factor"]),
        mensaje_analisis=riesgo["message"],
        recomendacion_analisis=riesgo["advice"],
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
        "risk": riesgo,
        "history": hist_ctx,
        "merchant_ctx": merchant_ctx,
        "exchange": conversion,
        "ofac": ofac_ctx
    }
