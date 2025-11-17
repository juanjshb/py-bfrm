# [file name]: config.py
# [file content begin]
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """Carga las configuraciones desde variables de entorno"""
    
    # URL de conexión a la base de datos PostgreSQL
    # Formato: postgresql+asyncpg://usuario:clave@host:puerto/basedatos
    DATABASE_URL: str = "postgresql+asyncpg://user:password@localhost:5432/fraude_db"
    
    # URL de Redis para el Rate Limiter
    REDIS_URL: str = "redis://localhost:6379/0"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding='utf-8')

# Instancia global de la configuración
settings = Settings()
# [file content end]