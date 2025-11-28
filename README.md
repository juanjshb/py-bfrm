# 🛡️ API de Detección de Fraude Bancario v3.0

Sistema integral para la detección, análisis y auditoría de fraude en transacciones bancarias. Esta versión evoluciona de una simple API de predicción a una plataforma robusta con persistencia de datos, capaz de procesar formatos de transacción estándar de la industria como **ISO 8583**.

Combina Machine Learning (Isolation Forest), reglas de negocio específicas para el contexto dominicano, integración de tasas de cambio en tiempo real (BHD), y ahora, una base de datos **PostgreSQL** para auditoría y un sistema de **Rate Limiting** con **Redis**.

-----

## 🎉 Novedades v3.0 (La Gran Actualización)

Esta versión introduce una arquitectura completamente nueva orientada a la persistencia y el procesamiento de nivel empresarial:

  * **Seguridad Mejorada:** Incluye un comunicacion HTTPS (TLS) y auto-carga del certificado para el proceso de renovacion.
  * **Integración con PostgreSQL:** Todas las transacciones analizadas y sus resultados de fraude se almacenan en una base de datos relacional.
  * **Procesamiento ISO 8583:** Nuevo endpoint (`/analizar-iso`) que acepta transacciones en un formato JSON basado en el estándar ISO 8583.
  * **Persistencia y Auditoría:** La tabla `ctransactions` guarda una copia de la transacción entrante *junto con* el veredicto del modelo (fraude, riesgo, factores, etc.), creando un registro de auditoría completo.
  * **Enriquecimiento de Datos:** La API ahora consulta la base de datos en tiempo real para "traducir" datos (ej. buscar el `PAN` de la tarjeta para encontrar el `cliente_id` asociado).
  * **Rate Limiting:** Implementación de `slowapi` con un backend **Redis** para proteger los endpoints contra abuso y ataques de denegación de servicio.
  * **Esquema de DB Completo:** Incluye tablas para Clientes (`ccustomers`), Cuentas (`caccounts`), Tarjetas (`ccardx`) y Monedas (`ccurrencies`) para un ecosistema de datos completo.
  * **Health Check Mejorado:** El endpoint `/health` ahora verifica el estado de la API, la conexión a la base de datos y el estado de la caché de tasas de cambio.

-----

## 🚀 Características Principales

| Característica | Descripción |
| :--- | :--- |
| **Modelo Híbrido** | Combina **Machine Learning (Isolation Forest)** con reglas de negocio robustas. |
| **Procesamiento ISO 8583** | Acepta y procesa datos de transacción en formato estándar de la industria. |
| **Base de Datos de Auditoría**| Almacena cada transacción y su análisis en **PostgreSQL** para cumplimiento y revisión. |
| **Soporte Multi-Moneda** | Conversión automática de **USD** y **EUR** a **DOP** usando tasas de cambio reales. |
| **Integración de Tasas (BHD)** | Obtiene tasas de cambio del BHD León con un sistema de **caché** de 30 minutos. |
| **Rate Limiting** | Protege la API contra abuso usando un limitador de peticiones basado en IP con **Redis**. |
| **Cumplimiento Legal** | Anonimización de ID de cliente (SHA-256) y trazabilidad para **Ley 172-13**. |
| **API Asíncrona** | Construida con **FastAPI** y `asyncpg` para un alto rendimiento. |

-----

### Factores de Riesgo

| Factor | Descripción | Puntaje | Moneda |
|--------|-------------|---------|---------|
| `MONTO_ELEVADO` | Transacciones > $10,000 DOP | +2 | Todas |
| `MONTO_MUY_BAJO` | Transacciones < $50 DOP | +1 | Todas |
| `TRANSACCION_DIVISA` | Operación en USD/EUR | +1 | USD/EUR |
| `DIVISA_MONTO_ELEVADO` | Divisa + monto > $15,000 DOP | +2 | USD/EUR |
| `HORARIO_NOCTURNO` | Entre 12am-6am | +1 | Todas |
| `PAIS_ALTO_RIESGO` | Venezuela, Haití | +2 | Todas |
| `PAIS_RIESGO_MEDIO` | Países no DO/US | +1 | Todas |
| `MONTO_ALTO_HORARIO_SOSPECHOSO` | Combo monto alto + horario nocturno | +2 | Todas |

-----

## 🔧 Arquitectura del Proyecto (v3)

```
v3/
│
├── main.py                 # API FastAPI: Endpoints (/analizar-iso, /health), DB, Redis
├── detector.py             # Lógica ML (Isolation Forest) y conversión de tasas (BHD)
├── models.py               # Schemas Pydantic (ISO8583Transaction, TransaccionResponse)
│
├── config.py               # (NUEVO) Configuración de entorno (DB_URL, REDIS_URL)
├── database.py             # (NUEVO) Lógica de conexión y sesión de SQLAlchemy async
├── db_models.py            # (NUEVO) Modelos de tablas de PostgreSQL (SQLAlchemy)
│
├── run_server.py           # Script de inicio del servidor uvicorn
├── requirements.txt        # Dependencias (fastapi, sqlalchemy, asyncpg, redis, slowapi)
└── readme.md               # Esta documentación
```

-----

## 🔌 Instalación y Ejecución (v3)

Se requieren tres componentes principales: la **Base de Datos**, **Redis** y la **Aplicación Python**.

### 1\. Servicios de Backend (PostgreSQL y Redis)

Asegúrate de tener PostgreSQL y Redis instalados y ejecutándose.

**PostgreSQL:**

1.  Crea una base de datos: `CREATE DATABASE fraude_db;`
2.  **Ejecuta el Script SQL:** Usa el script SQL (proporcionado en la conversación anterior) para crear todas las tablas (`ccustomers`, `caccounts`, `ccardx`, `ctransactions`, `ccurrencies`) e insertar los datos de prueba.

**Redis:**

1.  Inicia el servidor Redis (usualmente `redis-server`).

### 2\. Configuración de la Aplicación

1.  **Clonar el repositorio** (si aplica).

2.  **Crear un archivo `.env`** en la raíz del proyecto con tus credenciales:

    ```ini
    # .env
    DATABASE_URL="postgresql+asyncpg://usuario:clave@localhost:5432/fraude_db"
    REDIS_URL="redis://localhost:6379/0"
    ```

3.  **Instalar dependencias de Python:**

    ```bash
    pip install -r requirements.txt
    ```

### 3\. Generar los Certificados

Abre tu terminal en la raíz del proyecto y ejecuta el siguiente comando (requiere `openssl`, que usualmente viene instalado en Linux, macOS y Git Bash en Windows):

```bash
openssl req -x509 -newkey rsa:4096 -nodes -keyout key.pem -out cert.pem -days 365 -subj "/CN=localhost"
```

  * Esto creará dos archivos en tu carpeta: `key.pem` (tu llave privada) y `cert.pem` (tu certificado público), válidos por 365 días para `localhost` copialos en la carpeta `ssl` o la que tengas preseterminada.

  **Nota: Estos certificados son self-signed o firmados por el mismo equipo en caso de que tengas un proveedor solo has tu proceso y copia los archivos en tu carperta del servidor**


### 4\. Ejecutar el Servidor

```bash
# Usando el script de inicio (recomendado)
python run_server.py

# O directamente con uvicorn
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**Acceder a la documentación interactiva:** https://localhost:8000/docs

-----

## 📚 Endpoints de la API (v3)

### `POST /analizar-iso` (Endpoint Principal)

Analiza una transacción en formato ISO 8583, la enriquece con datos de la DB, la guarda en `ctransactions` y devuelve el análisis de fraude.

**Ejemplo de Request Body:**

```json
{
  "mti": "0100",
  "i_0002_pan": "4000123456789012",
  "i_0003_processing_code": "000000",
  "i_0004_amount_transaction": "000000100000",
  "i_0007_transmission_datetime": "1114030510",
  "i_0011_stan": "123457",
  "i_0012_time_local": "030510",
  "i_0013_date_local": "1114",
  "i_0022_pos_entry_mode": "051",
  "i_0024_function_code_nii": "200",
  "i_0025_pos_condition_code": "00",
  "i_0032_acquiring_inst_id": "987654",
  "i_0041_card_acceptor_tid": "TERM0002",
  "i_0042_card_acceptor_mid": "MERCHANT9876543",
  "i_0043_card_acceptor_name_loc": "Hotel Caracas, VE",
  "i_0049_currency_code_tx": "840"
}
```

**Ejemplo de Respuesta (Alto Riesgo):**

```json
{
  "fraude_detectado": true,
  "probabilidad_fraude": 0.8743,
  "nivel_riesgo": "ALTO",
  "factores_riesgo": [
    "MONTO_ELEVADO",
    "HORARIO_NOCTURNO",
    "PAIS_ALTO_RIESGO",
    "TRANSACCION_DIVISA",
    "DIVISA_MONTO_ELEVADO",
    "MONTO_ALTO_HORARIO_SOSPECHOSO"
  ],
  "mensaje": "ALERTA: Transacción identificada como fraudulenta por modelo ML y reglas de negocio",
  "recomendacion": "Recomendación: Revisar transacción manualmente y contactar al cliente",
  "cliente_hash": "a1b2c3d4e5f67890", // Hash del cliente_id encontrado en la DB
  "score_anomalia": -0.1245,
  "timestamp": "2025-11-14T17:30:00.123Z",
  "datos_analizados": {
    "cliente_id_length": 10,
    "monto_original": 1000.0,
    "moneda_original": "USD",
    "hora_transaccion": 3,
    "pais_origen": "VE"
  },
  "conversion_moneda": {
    "monto_original": 1000.0,
    "moneda_original": "USD",
    "monto_dop": 59500.0, // Monto convertido
    "tasa_aplicada": 59.5,
    "tipo_tasa": "venta",
    "descripcion": "USD → DOP (tasa venta: 59.5)",
    "conversion_requerida": true
  },
  "transaction_db_id": 1024 // ID de la fila en la tabla 'ctransactions'
}
```

### `GET /tasas-cambio`

Obtiene las tasas de cambio actuales (DOP, USD, EUR) cacheadas desde la API del BHD.

### `GET /health`

Verifica el estado del servicio. Respuesta de ejemplo:

```json
{
  "status": "healthy",
  "timestamp": "2025-11-14T17:31:00.456Z",
  "service": "fraud-detection-api-multi-currency",
  "version": "4.0.0-DB",
  "db_status": "healthy",
  "tasas_cambio": {
    "estado": "activo",
    "actualizado": "2025-11-14T17:15:00.000Z"
  }
}
```

-----

## 🗃️ Esquema de la Base de Datos

  * **`ccurrencies`**: Almacena códigos de moneda (ISO 4217).
  * **`ccustomers`**: Perfil de los clientes.
  * **`caccounts`**: Cuentas bancarias asociadas a los clientes.
  * **`ccardx`**: Tarjetas (PAN) asociadas a las cuentas.
  * **`ctransactions`**: Tabla principal de auditoría. Almacena todos los campos ISO 8583 de la solicitud *y* todos los campos de `TransaccionResponse` (el análisis de fraude).

-----

## 🔒 Recomendaciones para Producción

  * **Variables de Entorno:** No quemar credenciales. Usar `.env` (como está implementado con `pydantic-settings`) o secretos de orquestación (Kubernetes Secrets, etc.).
  * **Seguridad:** Autenticación de API (ej. JWT u OAuth2) y firewalls de red.
  * **Pruebas:** Añadir un set de pruebas unitarias e de integración (`pytest`) para `detector.py` y los endpoints de `main.py`.
  * **Contenerización:** Empaquetar la aplicación usando Docker y Docker Compose para gestionar los servicios (API, Postgres, Redis).
  * **Reglas de negocio:** Mejorar las reglas de negocio, segun tu negocio.
  * **Historial de transacciones del cliente:** Considerar el historial de transacciones de ese cliente para detectar anomalias y alertas; todas sus tarjetas.
  * **Factor de riesgo y reglas:** Hacer que el factor de riesgo este en la base de datos. 
  *  **UI y Reportes** Agregar UI para poder crear reglas y parametrizacion de forma User-friendly; Ademas de generacion de reportes
-----

## ⚖️ Aviso Legal y Cumplimiento

Este sistema está diseñado como una herramienta de soporte a la decisión para el cumplimiento de la **Ley 155-17 contra el Lavado de Activos** y la **Ley 172-13 sobre Protección de Datos**.

  * **Anonimización:** Los IDs de cliente se anonimizan con SHA-256 antes de ser expuestos en la respuesta.
  * **Trazabilidad:** La base de datos `ctransactions` provee la trazabilidad completa requerida por la SIB.

  * **Uso de Tasas:** La integración con el BHD es para fines demostrativos. En un entorno real, se debe usar la API de tasas oficial de la institución o del Banco Central.


**Versión:** 3.0.0  
**Última actualización:** Noviembre 2025






