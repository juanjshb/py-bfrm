# app/infra/db/models/customer.py
from sqlalchemy import Column, Integer, String, DateTime, func
from sqlalchemy.orm import relationship

from app.infra.db.base import Base


class Customer(Base):
    __tablename__ = "ccustomers"

    id = Column(Integer, primary_key=True)
    document_id = Column(String(30), unique=True, nullable=False)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    #pais = Column(String(2), default="DO")
    created_at = Column(DateTime, server_default=func.now())

    accounts = relationship("Account", back_populates="customer")
