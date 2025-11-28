from app.aml.ofac_matcher import screen_person_ofac

OFAC_FULL_WEIGHT = 1.0
OFAC_PARTIAL_WEIGHT = 0.7
OFAC_CLEAR_WEIGHT = 0.0

async def aplicar_factor_ofac(db, cliente, contexto_riesgo):
    full_name = f"{cliente.first_name} {cliente.last_name}".strip()

    try:
        result = await screen_person_ofac(db, full_name)
    except Exception as e:
        # Log y fallback seguro
        contexto_riesgo["factors"].append({
            "code": "OFAC_ERROR",
            "details": {"error": str(e)},
            "weight": 0,
            "recomended_action": "MANUAL_REVIEW"
        })
        return

    # Si no hay resultado, tratamos como CLEAR
    if not result:
        contexto_riesgo["factors"].append({
            "code": "OFAC_CLEAR",
            "details": {},
            "weight": OFAC_CLEAR_WEIGHT,
            "recomended_action": "NONE"
        })
        return

    # Asegurar atributos
    match_type = result["match_type"]
    best_name = result["best_name"]
    best_score = result["best_score"]
    ent_num = result["ent_num"]

    if match_type == "full":
        contexto_riesgo["score"] += OFAC_FULL_WEIGHT
        contexto_riesgo["factors"].append({
            "code": "OFAC_FULL_MATCH",
            "details": {
                "name_match": best_name,
                "score_match": best_score,
                "ent_num": ent_num,
            },
            "weight": OFAC_FULL_WEIGHT,
            "recomended_action": "AUTOMATIC_BLOCK_AND_REPORT"
        })

    elif match_type == "partial":
        contexto_riesgo["score"] += OFAC_PARTIAL_WEIGHT
        contexto_riesgo["factors"].append({
            "code": "OFAC_PARTIAL_MATCH",
            "details": {
                "name_match": best_name,
                "score_match": best_score,
                "ent_num": ent_num,
            },
            "weight": OFAC_PARTIAL_WEIGHT,
            "recomended_action": "MANUAL_REVIEW"
        })

    else:
        contexto_riesgo["factors"].append({
            "code": "OFAC_CLEAR",
            "details": {},
            "weight": OFAC_CLEAR_WEIGHT,
            "recomended_action": "NONE"
        })
