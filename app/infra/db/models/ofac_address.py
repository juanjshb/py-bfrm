# app/infra/db/models/ofac_address.py

from sqlalchemy import Column, Integer, String, Text, ForeignKey
from app.infra.db.base_class import Base


class OfacAddress(Base):
    __tablename__ = "ofac_address"

    id = Column(Integer, primary_key=True, index=True)

    ent_num = Column(Integer, ForeignKey("ofac_entity.ent_num", ondelete="CASCADE"), nullable=False)

    address1 = Column(Text)
    address2 = Column(Text)

    city = Column(String(255))
    state = Column(String(255))
    postal_code = Column(String(50))
    country = Column(String(100))
