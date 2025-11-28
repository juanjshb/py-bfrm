# app/infra/db/models/ofac_entity.py

from sqlalchemy import Column, Integer, String, Boolean, Text, DateTime
from sqlalchemy.sql import func
from app.infra.db.base import Base


class OfacEntity(Base):
    __tablename__ = "ofac_entity"

    id = Column(Integer, primary_key=True, index=True)
    ent_num = Column(Integer, unique=True, index=True, nullable=False)

    sdn_name = Column(String(255), nullable=False)
    sdn_type = Column(String(50))           # Individual, Entity, Vessel, etc.
    program = Column(Text)
    title = Column(Text)
    remarks = Column(Text)

    is_individual = Column(Boolean, default=False)

    last_updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
