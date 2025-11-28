# app/infra/db/models/ofac_alias.py

from sqlalchemy import Column, Integer, String, Text, ForeignKey
from app.infra.db.base import Base


class OfacAlias(Base):
    __tablename__ = "ofac_alias"

    id = Column(Integer, primary_key=True, index=True)

    ent_num = Column(Integer, ForeignKey("ofac_entity.ent_num", ondelete="CASCADE"), nullable=False)

    alt_name = Column(String(255), nullable=False)
    alt_type = Column(String(100))      # strong, weak, aka, etc.
    remarks = Column(Text)
