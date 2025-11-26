#!/usr/bin/env python3
import logging
import os
import sys

import uvicorn

from app.core.config import settings


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("run_server")


def get_ssl_params() -> dict:
    key = settings.SSL_KEYFILE
    cert = settings.SSL_CERTFILE
    if not (key and cert and os.path.exists(key) and os.path.exists(cert)):
        logger.warning("Iniciando en HTTP (sin certificados SSL encontrados).")
        return {}
    logger.info("Usando certificados SSL para HTTPS.")
    return {"ssl_keyfile": key, "ssl_certfile": cert}


def main() -> None:
    params = get_ssl_params()
    protocolo = "https" if params else "http"

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
        **params,
    )
    logger.info(f"Servidor levantado en {protocolo}://localhost:8000")


if __name__ == "__main__":
    main()
