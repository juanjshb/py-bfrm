# app/core/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Metadatos
    PROJECT_NAME: str = "Fraud Detection API"
    PROJECT_VERSION: str = "3.0.0"
    ENVIRONMENT: str = "development"

    # DB & Redis
    DATABASE_URL: str = "postgresql+asyncpg://postgres:Ju%40n0432@localhost:5432/fraude_db"
    REDIS_URL: str = "redis://localhost:6379/0"

    # Rate limiting (requests/minuto por IP)
    RATE_LIMIT: str = "10/minute"

    # TLS (si usas HTTPS directo)
    SSL_KEYFILE: str | None = "ssl/key.pem"
    SSL_CERTFILE: str | None = "ssl/cert.pem"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
