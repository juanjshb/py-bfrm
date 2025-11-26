# app/infra/db/models/account.py
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship

from app.infra.db.base import Base


class Account(Base):
    __tablename__ = "caccounts"

    id = Column(Integer, primary_key=True)
    customer_id = Column(Integer, ForeignKey("ccustomers.id"), nullable=False)
    numero_cuenta = Column(String(30), unique=True, nullable=False)
    tipo_cuenta = Column(String(20), nullable=False, default="AHORROS")
    creado_en = Column(DateTime, server_default=func.now())

    customer = relationship("Customer", back_populates="accounts")
    cards = relationship("Card", back_populates="account")
