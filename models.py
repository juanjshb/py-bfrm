# [file name]: models.py
# [file content begin]
from pydantic import BaseModel, Field, condecimal, validator
from typing import Literal, Optional
from decimal import Decimal
import re

# --- NUEVO MODELO DE ENTRADA (Basado en ISO 8583) ---
class ISO8583Transaction(BaseModel):
    """
    Modelo Pydantic para recibir datos de transacción en formato ISO 8583
    """
    mti: str = Field(..., max_length=4, example="0100")
    i_0002_pan: str = Field(..., max_length=20, example="4000123456789012")
    i_0003_processing_code: str = Field(..., max_length=6, example="000000")
    i_0004_amount_transaction: str = Field(..., max_length=12, example="000000015050")
    i_0007_transmission_datetime: str = Field(..., max_length=10, example="1114130930")
    i_0011_stan: str = Field(..., max_length=6, example="123456")
    i_0012_time_local: str = Field(..., max_length=6, example="130930")
    i_0013_date_local: str = Field(..., max_length=4, example="1114")
    i_0022_pos_entry_mode: str = Field(..., max_length=3, example="051")
    i_0024_function_code_nii: str = Field(..., max_length=3, example="200")
    i_0025_pos_condition_code: str = Field(..., max_length=2, example="00")
    i_0032_acquiring_inst_id: str = Field(..., max_length=11, example="123456")
    i_0035_track_2_data: Optional[str] = Field(None, max_length=37, example="4000...=...")
    i_0041_card_acceptor_tid: str = Field(..., max_length=8, example="TERM0001")
    i_0042_card_acceptor_mid: str = Field(..., max_length=15, example="MERCHANT1234567")
    i_0043_card_acceptor_name_loc: str = Field(..., max_length=40, example="Mi Tienda, Santo Domingo, DO")
    i_0049_currency_code_tx: str = Field(..., max_length=3, example="840") # ISO 4217 Numérico
    i_0062_private_use_field: Optional[str] = Field(None, max_length=255)
    i_0128_mac: Optional[str] = Field(None, max_length=64)


# --- MODELO DE RESPUESTA (Sin cambios, sigue siendo excelente) ---
class TransaccionResponse(BaseModel):
    fraude_detectado: bool
    probabilidad_fraude: float
    nivel_riesgo: str
    factores_riesgo: list
    mensaje: str
    recomendacion: str
    cliente_hash: str
    score_anomalia: float
    timestamp: str
    datos_analizados: dict
    conversion_moneda: Optional[dict] = None
    # Nuevo campo para vincular el análisis
    transaction_db_id: Optional[int] = None 

class HealthCheck(BaseModel):
    status: str
    timestamp: str
    db_status: str # Agregado
    tasas_cambio: Optional[dict] = None

class TasasCambio(BaseModel):
    USD_compra: float
    USD_venta: float
    EUR_compra: float
    EUR_venta: float
    actualizado: str
# [file content end]