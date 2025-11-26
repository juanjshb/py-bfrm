from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship

from app.infra.db.base import Base  # Ajusta si tu proyecto usa otro Base


class Country(Base):
    __tablename__ = "countries"

    country_id = Column(Integer, primary_key=True, index=True)

    iso2 = Column(String(2), unique=True, nullable=False, index=True)
    iso3 = Column(String(3), unique=True, nullable=False)
    numeric_code = Column(String(3), unique=True, nullable=False)
    name = Column(String(120), nullable=False)

    region = Column(String(80))
    subregion = Column(String(80))

    risk_level = Column(String(20), default="LOW")   # HIGH / MEDIUM / LOW
