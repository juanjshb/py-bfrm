from sqlalchemy import Column, Integer, String, Float, DateTime
from sqlalchemy.sql import func

from app.infra.db.base import Base


class OfacAudit(Base):
    __tablename__ = "ofac_audit"

    id = Column(Integer, primary_key=True, index=True)

    full_name = Column(String(255), nullable=False)
    match_type = Column(String(50), nullable=False)
    best_score = Column(Float, nullable=False)
    best_name = Column(String(255))
    ent_num = Column(Integer)

    created_at = Column(DateTime, server_default=func.now())
