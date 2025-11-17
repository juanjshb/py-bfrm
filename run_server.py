# [file name]: run_server.py
# [file content begin]
#!/usr/bin/env python3
"""
Script mejorado para ejecutar el servidor de detección de fraude
"""
import uvicorn
import logging
import sys
import os # Importar os para verificar los archivos

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger(__name__)

# --- NUEVAS CONFIGURACIONES SSL/TLS ---
SSL_KEYFILE = "key.pem"
SSL_CERTFILE = "cert.pem"

if __name__ == "__main__":
    
    # Verificar que los certificados existan
    if not os.path.exists(SSL_KEYFILE) or not os.path.exists(SSL_CERTFILE):
        logger.warning("--- ADVERTENCIA SSL/TLS ---")
        logger.warning(f"No se encontraron los archivos '{SSL_KEYFILE}' y '{SSL_CERTFILE}'.")
        logger.warning("El servidor se iniciará en HTTP (no seguro).")
        logger.warning("Para HTTPS, genérelos con: openssl req -x509 -newkey rsa:4096 -nodes -keyout key.pem -out cert.pem -days 365 -subj \"/CN=localhost\"")
        ssl_params = {}
        protocolo = "http"
    else:
        logger.info(f"Cargando certificados SSL/TLS desde '{SSL_KEYFILE}' y '{SSL_CERTFILE}'.")
        ssl_params = {
            "ssl_keyfile": SSL_KEYFILE,
            "ssl_certfile": SSL_CERTFILE
        }
        protocolo = "https"

    try:
        logger.info("🚀 Iniciando servidor de Detección de Fraude...")
        logger.info("📊 Cargando modelos de Machine Learning...")
        
        uvicorn.run(
            "main:app",
            host="0.0.0.0",
            port=8000,
            reload=True,  # Solo en desarrollo
            log_level="info",
            access_log=True,
            # Pasar los parámetros SSL a uvicorn
            **ssl_params 
        )
        
        logger.info(f"Servidor iniciado. Accede en: {protocolo}://localhost:8000")

    except KeyboardInterrupt:
        logger.info("Servidor detenido por el usuario")
    except Exception as e:
        logger.error(f"Error al iniciar el servidor: {e}")
        sys.exit(1)
# [file content end]
