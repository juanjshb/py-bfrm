# [file name]: database.py
# [file content begin]
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from config import settings
from typing import AsyncGenerator

# Crear el motor de SQLAlchemy asíncrono
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=True,  # Imprime las queries SQL (útil en desarrollo)
    future=True
)

# Base para los modelos declarativos
class Base(DeclarativeBase):
    pass

# Fábrica de sesiones asíncronas
AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False
)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependencia de FastAPI para obtener una sesión de base de datos.
    Asegura que la sesión se cierre correctamente.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

async def init_db():
    """Inicializa la base de datos (crea las tablas)"""
    async with engine.begin() as conn:
        # En producción, usarías Alembic para manejar esto
        # await conn.run_sync(Base.metadata.drop_all) 
        await conn.run_sync(Base.metadata.create_all)
# [file content end]