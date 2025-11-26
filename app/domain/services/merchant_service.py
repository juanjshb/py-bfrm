# app/domain/services/merchant_service.py
from sqlalchemy.ext.asyncio import AsyncSession

# Si más adelante creas tablas Merchant/Mcc, las importas aquí.


async def obtener_contexto_merchant(db: AsyncSession, mid: str | None) -> dict:
    """
    De momento devolvemos contexto neutro porque en la versión que subiste
    aún no existen tablas Merchant/Mcc consolidadas.
    """
    if not mid:
        return {
            "merchant_existe": False,
            "merchant_permitido": None,
            "riesgo_merchant": None,
            "mcc": None,
            "mcc_permitido": None,
            "riesgo_mcc": None,
        }

    # Placeholder: cuando tengas cmerchants / cmccs, consulta aquí.
    return {
        "merchant_existe": False,
        "merchant_permitido": None,
        "riesgo_merchant": None,
        "mcc": None,
        "mcc_permitido": None,
        "riesgo_mcc": None,
    }
