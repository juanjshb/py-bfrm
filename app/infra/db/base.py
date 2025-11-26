# app/infra/db/base.py
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base de todos los modelos ORM."""
    pass
