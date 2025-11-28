# app/aml/ofac_matcher.py
from dataclasses import dataclass
from difflib import SequenceMatcher
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infra.db.models.ofac_entity import OfacEntity
from app.infra.db.models.ofac_alias import OfacAlias

@dataclass
class OfacMatchResult:
    match_type: str           # "none" | "partial" | "full"
    best_score: float
    best_name: str | None
    ent_num: int | None


def _similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


async def screen_person_ofac(
    db: AsyncSession,
    full_name: str,
    min_candidate_score: float = 0.7,
) -> OfacMatchResult:
    """
    Screening muy simplificado:
      - Busca posibles candidatos por nombre aproximado (nombre completo).
      - Calcula similitud y clasifica en none/partial/full.
    """

    # 1) Candidatos: limitamos por LIKE simple para no barrer toda la tabla.
    # En serio productivo, aquí usarías pg_trgm o un índice de texto.
    stmt_entities = (
        select(OfacEntity)
        .where(OfacEntity.is_individual == True)
        .limit(500)
    )
    entities = (await db.execute(stmt_entities)).scalars().all()

    stmt_aliases = (
        select(OfacAlias)
        .join(OfacEntity, OfacAlias.ent_num == OfacEntity.ent_num)
        .where(OfacEntity.is_individual == True)
        .limit(1000)
    )
    aliases = (await db.execute(stmt_aliases)).scalars().all()

    best_score = 0.0
    best_name = None
    best_ent_num = None

    # 2) Comparamos
    for ent in entities:
        score = _similarity(full_name, ent.sdn_name)
        if score > best_score:
            best_score = score
            best_name = ent.sdn_name
            best_ent_num = ent.ent_num

    for alt in aliases:
        score = _similarity(full_name, alt.alt_name)
        if score > best_score:
            best_score = score
            best_name = alt.alt_name
            best_ent_num = alt.ent_num

    # 3) Clasificación de match
    if best_score >= 0.95:
        match_type = "full"
    elif best_score >= 0.80:
        match_type = "partial"
    else:
        match_type = "none"

    return {
        "match_type": match_type,
        "best_score": best_score,
        "best_name": best_name,
        "ent_num": best_ent_num,
    }

