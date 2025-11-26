# app/infra/db/models/card.py
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship

from app.infra.db.base import Base


class Card(Base):
    __tablename__ = "ccardx"

    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey("caccounts.id"), nullable=False)
    pan_token = Column(String(32), unique=True, nullable=False)
    last4 = Column(String(4), nullable=False)
    brand = Column(String(20), nullable=True)
    creado_en = Column(DateTime, server_default=func.now())

    account = relationship("Account", back_populates="cards")
    transactions = relationship("Transaction", back_populates="card")
