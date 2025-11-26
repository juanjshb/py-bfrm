**FastAPI + SQLAlchemy Async + Rate-Limit + AML Detector + Tasas BHD Cache**

---

## 📌 **1. Descripción del Proyecto**

La **Fraud / AML API** es un servicio backend desarrollado con **FastAPI** para ejecutar validaciones de fraude, análisis de comportamiento transaccional y cumplimiento AML en tiempo real.
Incluye:

* Detección basada en reglas dinámicas (riesgo por monto, frecuencia, repetición, historial reciente).
* Enriquecimiento con **tasas de cambio del BHD**, con caché de 30 minutos.
* Rate Limiting por IP (SlowAPI).
* Arquitectura asíncrona (SQLAlchemy Async).
* Logging estructurado.
* Modelo de transacción inspirado en ISO8583.
* Evaluación histórico del cliente (24h / 7 días).

Este servicio está diseñado como componente central para ecosistemas antifraude o motores AML dentro de plataformas financieras o sistemas transaccionales.

---

## 🧱 **2. Arquitectura General del Sistema**

### Componentes principales

| Componente              | Función                                             |
| ----------------------- | --------------------------------------------------- |
| **FastAPI**             | Exposición de endpoints y orquestación del flujo.   |
| **Detector AML/Fraude** | Procesa reglas, historial y riesgo por transacción. |
| **Tasas BHD (caché)**   | Extrae tasas y mantiene un TTL de 30 minutos.       |
| **SQLAlchemy Async**    | Persistencia eficiente de transacciones y logs.     |
| **SlowAPI**             | Rate limit por IP/origen.                           |
| **Logging**             | Registro estructurado para auditoría y monitoreo.   |

---

## 🗂 **3. Estructura de Carpetas**

```txt
app/
 ├── infra/
 │    └── detectors/
 │           └── tasas.py
 ├── models/
 ├── database.py
 ├── detector.py
 ├── db_models.py
 ├── main.py
 └── utils/
```

---

## ⚙️ **4. Requisitos Previos**

* Python 3.11+
* PostgreSQL o SQL Server compatible con SQLAlchemy Async
* pipenv o venv recomendado
* Dependencias principales:

  * fastapi
  * uvicorn
  * sqlalchemy[asyncio]
  * slowapi
  * httpx / requests
  * python-dotenv

---

## 🔧 **5. Configuración e Instalación**

### 1. Clonar el repositorio

```bash
git clone https://github.com/tu-org/fraude-api.git
cd fraude-api
```

### 2. Crear entorno

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Variables de entorno

Crear un archivo `.env`:

```env
DATABASE_URL=postgresql+asyncpg://user:pass@host/db
SSL_KEYFILE=
SSL_CERTFILE=
TASAS_TIMEOUT_MINUTES=30
```

---

## 🚀 **6. Ejecución del Servidor**

### Modo desarrollo

```bash
uvicorn run_server:app --reload --host 0.0.0.0 --port 8000
```

Si no se encuentran certificados SSL, el servicio inicia en HTTP y lo registra en consola.

---

## 📡 **7. Endpoints del Sistema**

### 📍 Health Check

```
GET /health
```

### 📍 Obtener tasas BHD (cacheadas)

```
GET /tasas
```

### 📍 Procesar transacción ISO8583 / antifraude

```
POST /transaccion
```

Ejemplo de body:

```json
{
  "customer_id": 1234,
  "monto": 1500.50,
  "currency": "DOP",
  "merchant": "AMZN",
  "timestamp": "2025-11-26T16:40:00"
}
```

Respuesta:

```json
{
  "riesgo": "medio",
  "motivos": ["frecuencia_alta_24h"],
  "aprobada": true
}
```

---

## 🧠 **8. Lógica del Detector AML / Fraude**

### Factores evaluados

| Regla                  | Ejemplo                                    |
| ---------------------- | ------------------------------------------ |
| Frecuencia en 24h      | compras repetidas en tiendas diferentes    |
| Frecuencia en 7 días   | historial anormal vs comportamiento típico |
| Montos fuera de patrón | monto alto comparado con promedio          |
| Merchant pattern       | comercios sospechosos o inconsistentes     |
| Conversión moneda      | uso de tasa BHD precargada                 |

### Comportamiento del caché de tasas

* Timeout configurable (default: 30 min)
* Si la tasa está dentro del TTL → responde desde caché
* Si expira → consulta API BHD

---

## 🔐 **9. Rate Limiting**

Implementado con **SlowAPI**:

```python
limiter = Limiter(key_func=get_remote_address)
```

Políticas configurables:

* X solicitudes por minuto
* Bloqueo temporal
* Respuestas automáticas HTTP 429

---

## 🗄 **10. Base de Datos (SQLAlchemy Async)**

### Ejemplo de modelo:

```python
class Transaccion(Base):
    __tablename__ = "transacciones"

    id = Column(Integer, primary_key=True)
    customer_id = Column(Integer)
    monto = Column(Float)
    fecha = Column(DateTime)
```

### Funciones adicionales:

* Historial 24h
* Historial 7 días
* Agregaciones con `func.count` y `func.sum`

---

## 📊 **11. Logging**

* Nivel INFO por defecto
* Logs de:

  * tasas actualizadas
  * tasas desde caché
  * inicio sin SSL
  * reglas disparadas

---

## 🧭 **12. Roadmap Sugerido**

| Fase                   | Descripción                             |
| ---------------------- | --------------------------------------- |
| **1. MVP**             | Validaciones actuales + BD + tasas      |
| **2. AML avanzado**    | OFAC, listas negras, screening continuo |
| **3. Motor de reglas** | DSL o YAML para reglas dinámicas        |
| **4. Dashboard**       | Power BI / Grafana con KPIs             |
| **5. ML**              | modelos de outliers o anomalías         |

---

## 🏦 **13. Consideraciones AML / Compliance**

Sin agregar inventos, únicamente lo que aplica a tu API actual:

* No almacena datos sensibles más allá de transacciones.
* No ejecuta screening contra listas externas.
* Utiliza reglas determinísticas que pueden ser auditadas.
* Registra entradas/salidas con timestamp para trazabilidad.

---

## 📄 **14. Licencia**

MIT / Privado (dependiendo del repositorio final).

