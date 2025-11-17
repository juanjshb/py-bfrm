# [file name]: run_server.py
# [file content begin]
#!/usr/bin/env python3
"""
Script mejorado para ejecutar el servidor de detección de fraude
"""
import uvicorn
import logging
import sys

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger(__name__)

if __name__ == "__main__":
    try:
        logger.info("🚀 Iniciando servidor de Detección de Fraude...")
        logger.info("📊 Cargando modelos de Machine Learning...")
        
        uvicorn.run(
            "main:app",
            host="0.0.0.0",
            port=8000,
            reload=True,  # Solo en desarrollo
            log_level="info",
            access_log=True
        )
    except KeyboardInterrupt:
        logger.info("🛑 Servidor detenido por el usuario")
    except Exception as e:
        logger.error(f"❌ Error al iniciar el servidor: {e}")
        sys.exit(1)
# [file content end]