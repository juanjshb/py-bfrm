# app/api/v1/endpoints/health.py
from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.infra.db.session import get_db
from app.infra.detectors.tasas import obtener_estado_tasas
from app.schemas.health_schemas import HealthResponse, PageInfo, StatusObject, ComponentStatus

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health_check(db: AsyncSession = Depends(get_db)):
    t = datetime.utcnow().isoformat() + "Z"

    # DB
    try:
        await db.execute(text("SELECT 1"))
        db_status = ComponentStatus(status="operational", detail="Database connection OK")
    except Exception as e:
        db_status = ComponentStatus(status="major_outage", detail=f"Database error: {e}")

    # Tasas
    tasas_estado = obtener_estado_tasas()
    tasas_status = ComponentStatus(
        status="operational" if tasas_estado["estado"] == "activo" else "degraded_performance",
        detail="BHD FX service",
        last_update=tasas_estado["cache_actualizado"],
    )

    # Indicator global
    if db_status.status != "operational":
        indicator = "major_outage"
        desc = "Database unavailable."
    elif tasas_status.status != "operational":
        indicator = "degraded_performance"
        desc = "Exchange rate source degraded."
    else:
        indicator = "operational"
        desc = "All systems functional."

    return HealthResponse(
        page=PageInfo(
            name="Fraud Detection API",
            url="https://api.fraude.local/health",
            time=t,
        ),
        status=StatusObject(
            indicator=indicator,
            description=desc,
        ),
        components={
            "database": db_status,
            "exchange": tasas_status,
        },
    )
