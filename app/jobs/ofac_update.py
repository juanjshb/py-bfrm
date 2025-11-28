# app/jobs/ofac_update.py
import csv
import io
import logging
from datetime import datetime

import requests
from sqlalchemy import create_engine, text

# Si luego quieres tomar la URL desde settings, asegúrate que sea SIN asyncpg
# from app.core.config import settings

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

SDN_URL = "https://www.treasury.gov/ofac/downloads/sdn.csv"
ADD_URL = "https://www.treasury.gov/ofac/downloads/add.csv"
ALT_URL = "https://www.treasury.gov/ofac/downloads/alt.csv"

# IMPORTANTE: driver síncrono (psycopg2), no asyncpg
DB_URL = "postgresql+psycopg2://postgres:Ju%40n0432@localhost:5432/fraude_db"
# Si quieres dejarlo más genérico y tener psycopg2 como default:
# DB_URL = "postgresql://postgres:Ju%40n0432@localhost:5432/fraude_db"


def download_csv(url: str) -> list[list[str]]:
    """
    Descarga un CSV y lo devuelve como lista de filas.
    OFAC suele usar Windows-1252; latin-1 evita problemas de caracteres raros.
    """
    logger.info(f"Descargando {url}")
    resp = requests.get(url, timeout=60)
    resp.raise_for_status()
    content = resp.content.decode("latin-1")
    reader = csv.reader(io.StringIO(content))
    return list(reader)


def run():
    # create_engine síncrono
    engine = create_engine(DB_URL, future=True)

    sdn_rows = download_csv(SDN_URL)
    add_rows = download_csv(ADD_URL)
    alt_rows = download_csv(ALT_URL)

    with engine.begin() as conn:
        logger.info("Truncando tablas OFAC...")
        conn.execute(
            text("TRUNCATE ofac_address, ofac_alias, ofac_entity RESTART IDENTITY")
        )

        # ============
        #  SDN (entidades)
        # ============
        # SDN.CSV (esquema típico):
        # 0 ENT_NUM
        # 1 SDN_NAME
        # 2 SDN_TYPE
        # 3 PROGRAM
        # 4 TITLE
        # ...
        # 11 REMARKS
        logger.info("Insertando registros SDN (ofac_entity)...")
        for row in sdn_rows:
            if not row:
                continue

            # Saltar header u otras filas no válidas
            try:
                ent_num = int(row[0])
            except (ValueError, IndexError):
                # Ej: "ent_num" (header) u otra cosa no numérica
                continue

            sdn_name = (
                row[1].strip() if len(row) > 1 and row[1] is not None else None
            )
            sdn_type = (
                row[2].strip() if len(row) > 2 and row[2] is not None else None
            )
            program = (
                row[3].strip() if len(row) > 3 and row[3] is not None else None
            )
            title = (
                row[4].strip() if len(row) > 4 and row[4] is not None else None
            )
            remarks = (
                row[11].strip() if len(row) > 11 and row[11] is not None else None
            )

            is_individual = (sdn_type or "").lower() == "individual"

            conn.execute(
                text(
                    """
                    INSERT INTO ofac_entity
                        (ent_num, sdn_name, sdn_type, program, title, remarks, is_individual, last_updated_at)
                    VALUES
                        (:ent_num, :sdn_name, :sdn_type, :program, :title, :remarks, :is_individual, :last_updated_at)
                    """
                ),
                {
                    "ent_num": ent_num,
                    "sdn_name": sdn_name,
                    "sdn_type": sdn_type,
                    "program": program,
                    "title": title,
                    "remarks": remarks,
                    "is_individual": is_individual,
                    "last_updated_at": datetime.utcnow(),
                },
            )

        # ============
        #  ADD (direcciones)
        # ============
        # ADD.CSV típico:
        # 0 ENT_NUM
        # 1 ADDRESS
        # 2 CITY
        # 3 STATE/PROVINCE
        # 4 ZIP
        # 5 COUNTRY
        logger.info("Insertando registros ADD (ofac_address)...")
        for row in add_rows:
            if not row:
                continue

            try:
                ent_num = int(row[0])
            except (ValueError, IndexError):
                continue

            address1 = (
                row[1].strip() if len(row) > 1 and row[1] is not None else None
            )
            city = (
                row[2].strip() if len(row) > 2 and row[2] is not None else None
            )
            state = (
                row[3].strip() if len(row) > 3 and row[3] is not None else None
            )
            postal = (
                row[4].strip() if len(row) > 4 and row[4] is not None else None
            )
            country = (
                row[5].strip() if len(row) > 5 and row[5] is not None else None
            )

            conn.execute(
                text(
                    """
                    INSERT INTO ofac_address
                        (ent_num, address1, city, state, postal_code, country)
                    VALUES
                        (:ent_num, :address1, :city, :state, :postal_code, :country)
                    """
                ),
                {
                    "ent_num": ent_num,
                    "address1": address1,
                    "city": city,
                    "state": state,
                    "postal_code": postal,
                    "country": country,
                },
            )

        # ============
        #  ALT (aliases)
        # ============
        # ALT.CSV típico:
        # 0 ENT_NUM
        # 1 ALT_TYPE
        # 2 ALT_NAME
        # 3 ALT_REMARKS
        logger.info("Insertando registros ALT (ofac_alias)...")
        for row in alt_rows:
            if not row:
                continue

            try:
                ent_num = int(row[0])
            except (ValueError, IndexError):
                continue

            alt_type = (
                row[1].strip() if len(row) > 1 and row[1] is not None else None
            )
            alt_name = (
                row[2].strip() if len(row) > 2 and row[2] is not None else None
            )
            alt_remarks = (
                row[3].strip() if len(row) > 3 and row[3] is not None else None
            )

            conn.execute(
                text(
                    """
                    INSERT INTO ofac_alias
                        (ent_num, alt_name, alt_type, remarks)
                    VALUES
                        (:ent_num, :alt_name, :alt_type, :remarks)
                    """
                ),
                {
                    "ent_num": ent_num,
                    "alt_name": alt_name,
                    "alt_type": alt_type,
                    "remarks": alt_remarks,
                },
            )

        # ============
        #  Metadatos
        # ============
        logger.info("Actualizando metadatos de OFAC...")
        conn.execute(
            text(
                """
                INSERT INTO ofac_metadata (id, last_sync_at)
                VALUES (1, :dt)
                ON CONFLICT (id) DO UPDATE
                SET last_sync_at = EXCLUDED.last_sync_at
                """
            ),
            {"dt": datetime.utcnow()},
        )

    logger.info("Actualización OFAC completada.")


if __name__ == "__main__":
    run()
