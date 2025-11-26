# app/infra/db/models/currency.py
from sqlalchemy import Column, Integer, String
from app.infra.db.base import Base


class Currency(Base):
    __tablename__ = "ccurrencies"

    id = Column(Integer, primary_key=True)
    code_num = Column(String(3), unique=True, nullable=False)   # 840
    code_alpha = Column(String(3), unique=True, nullable=False) # USD
    nombre = Column(String(50), nullable=False)
