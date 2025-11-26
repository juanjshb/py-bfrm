from typing import Set
from app.infra.db.models.country import Country


HIGH_RISK_COUNTRIES: Set[str] = set()
MEDIUM_RISK_COUNTRIES: Set[str] = set()


async def load_risk_countries(db, Country):
    # Países de alto riesgo
    result_high = await db.execute(
        Country.__table__.select().where(Country.risk_level == "HIGH")
    )
    rows_high = [row.iso2 for row in result_high.fetchall()]
    HIGH_RISK_COUNTRIES.clear()
    HIGH_RISK_COUNTRIES.update(rows_high)

    # Países de riesgo medio
    result_medium = await db.execute(
        Country.__table__.select().where(Country.risk_level == "MEDIUM")
    )
    rows_medium = [row.iso2 for row in result_medium.fetchall()]
    MEDIUM_RISK_COUNTRIES.clear()
    MEDIUM_RISK_COUNTRIES.update(rows_medium)

    print("🌍 HIGH =", HIGH_RISK_COUNTRIES)
    print("🌍 MEDIUM =", MEDIUM_RISK_COUNTRIES)
