# app/infra/db/models/card.py
from sqlalchemy import Column, Integer, String, Float, Boolean, ARRAY
from sqlalchemy.orm import relationship

from app.infra.db.base import Base

class RiskFactor(Base):
    __tablename__ = "risk_factors"

    id = Column(Integer, primary_key=True)
    code = Column(String(80), unique=True, nullable=False)
    description = Column(String(255), nullable=False)
    weight = Column(Float, nullable=False)
    category = Column(String(50), nullable=False)
    severity = Column(String(20), nullable=False)
    enabled = Column(Boolean, default=True)


class RiskFactorRule(Base):
    __tablename__ = "risk_factor_rules"

    id = Column(Integer, primary_key=True)
    trigger_factors = Column(ARRAY(String), nullable=False)
    result_factor = Column(String(80), nullable=False)
    weight_override = Column(Float, nullable=True)
    enabled = Column(Boolean, default=True)


class RiskFactorCritical(Base):
    __tablename__ = "risk_factor_critical"

    factor_code = Column(String(80), primary_key=True)
    auto_fail = Column(Boolean, default=True)
