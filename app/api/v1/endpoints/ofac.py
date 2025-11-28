from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.aml.ofac_matcher import screen_person_ofac
from app.infra.db.session import get_db
from app.infra.db.models.ofac_audit import OfacAudit

router = APIRouter(prefix="/ofac", tags=["OFAC"])


class OfacQuery(BaseModel):
    first_name: str
    last_name: str


@router.post("/check")
async def consultar_ofac(
    data: OfacQuery,
    db: AsyncSession = Depends(get_db)
):
    full_name = f"{data.first_name} {data.last_name}".strip()

    resultado = await screen_person_ofac(db, full_name)

    # Guardar auditoría (importante para cumplimiento AML)
    audit = OfacAudit(
        full_name=full_name,
        match_type=resultado["match_type"],
        best_score=resultado["best_score"],
        best_name=resultado["best_name"],
        ent_num=resultado["ent_num"],
    )
    db.add(audit)
    await db.commit()

    return {
        "request": full_name,
        "result": resultado,
    }
