# [file name]: db_models.py
# [file content begin]
from sqlalchemy import (
    Column, String, Integer, BigInteger, DateTime, Float, Boolean, 
    ForeignKey, func, DECIMAL, UniqueConstraint
)
from sqlalchemy.orm import relationship
from database import Base
import datetime

# --- NUEVA TABLA: Merchant Category Codes (MCC) ---
class MccCode(Base):
    """
    Tabla para parametrizar el riesgo de los Códigos de Categoría de Comercio (MCC)
    """
    __tablename__ = 'cmcc_codes'
    
    id = Column(Integer, primary_key=True)
    # El código MCC (ej. '5411' para Supermercado, '7995' para Apuestas)
    mcc = Column(String(4), unique=True, nullable=False, index=True)
    description = Column(String(255))
    # 'low', 'medium', 'high', 'blocked'
    risk_level = Column(String(20), nullable=False, default='medium', index=True)

# --- NUEVA TABLA: Comerciantes Monitoreados (MID) ---
class MonitoredMerchant(Base):
    """
    Tabla para listas blancas/negras de Merchant IDs (MID) específicos
    """
    __tablename__ = 'cmonitored_merchants'
    
    id = Column(Integer, primary_key=True)
    # El Merchant ID (ej. 'MERCHANT1234567')
    mid = Column(String(15), unique=True, nullable=False, index=True)
    name = Column(String(100))
    # 'allowed' (lista blanca), 'denied' (lista negra), 'watch' (monitoreo)
    status = Column(String(20), nullable=False, default='watch', index=True)
    reason = Column(String(255))


class Currency(Base):
    """Tabla de códigos de moneda ISO 4217"""
    __tablename__ = 'ccurrencies'
    # ... (sin cambios)
    id = Column(Integer, primary_key=True)
    code_numeric = Column(String(3), unique=True, nullable=False, index=True)
    code_alpha = Column(String(3), unique=True, nullable=False, index=True)
    name = Column(String(100))
    decimals = Column(Integer, default=2)

class Customer(Base):
    """Tabla de Clientes (ccustomers)"""
    __tablename__ = 'ccustomers'
    # ... (sin cambios)
    id = Column(Integer, primary_key=True)
    customer_ref_id = Column(String(50), unique=True, nullable=False, index=True)
    first_name = Column(String(100))
    last_name = Column(String(100))
    email = Column(String(150), unique=True)
    phone = Column(String(20))
    document_id = Column(String(50), unique=True)
    created_at = Column(DateTime, default=func.now())
    accounts = relationship("Account", back_populates="customer")

class Account(Base):
    """Tabla de Cuentas Bancarias (caccounts)"""
    __tablename__ = 'caccounts'
    # ... (sin cambios)
    id = Column(Integer, primary_key=True)
    account_number = Column(String(30), unique=True, nullable=False, index=True)
    account_type = Column(String(50))
    status = Column(String(20), default="active")
    balance = Column(DECIMAL(18, 2), default=0.00)
    currency_code = Column(String(3), nullable=False)
    opened_at = Column(DateTime, default=func.now())
    customer_id = Column(Integer, ForeignKey('ccustomers.id'), nullable=False)
    customer = relationship("Customer", back_populates="accounts")
    cards = relationship("Card", back_populates="account")

class Card(Base):
    """Tabla de Tarjetas (ccardx)"""
    __tablename__ = 'ccardx'
    # ... (sin cambios)
    id = Column(Integer, primary_key=True)
    pan = Column(String(20), unique=True, nullable=False, index=True)
    pan_last_4 = Column(String(4), nullable=False)
    pan_bin = Column(String(8), nullable=False, index=True)
    expiry_date = Column(String(4))
    card_type = Column(String(20))
    brand = Column(String(20))
    status = Column(String(20), default="active")
    account_id = Column(Integer, ForeignKey('caccounts.id'), nullable=False)
    account = relationship("Account", back_populates="cards")
    transactions = relationship("Transaction", back_populates="card")

class Transaction(Base):
    """Tabla de Transacciones (ctransactions) en formato ISO 8583"""
    __tablename__ = 'ctransactions'
    
    id = Column(Integer, primary_key=True)
    tx_timestamp_utc = Column(DateTime, default=func.now(), index=True)
    card_id = Column(Integer, ForeignKey('ccardx.id'), nullable=True, index=True)
    
    # Campos ISO 8583
    mti = Column(String(4), index=True)
    i_0002_pan = Column(String(20), index=True)
    i_0003_processing_code = Column(String(6))
    i_0004_amount_transaction = Column(String(12))
    i_0007_transmission_datetime = Column(String(10))
    i_0011_stan = Column(String(6), index=True)
    i_0012_time_local = Column(String(6))
    i_0013_date_local = Column(String(4))
    i_0022_pos_entry_mode = Column(String(3))
    i_0024_function_code_nii = Column(String(3))
    i_0025_pos_condition_code = Column(String(2))
    
    # --- CAMPO AÑADIDO (MCC) ---
    i_0026_mcc = Column(String(4), index=True) # Merchant Category Code
    
    i_0032_acquiring_inst_id = Column(String(11))
    i_0035_track_2_data = Column(String(37))
    i_0041_card_acceptor_tid = Column(String(8))
    i_0042_card_acceptor_mid = Column(String(15), index=True) # MID
    i_0043_card_acceptor_name_loc = Column(String(40))
    i_0049_currency_code_tx = Column(String(3))
    i_0062_private_use_field = Column(String(255))
    i_0128_mac = Column(String(64))
    
    # ... (Resultados de análisis sin cambios) ...
    es_fraude = Column(Boolean, default=False, index=True)
    probabilidad_fraude = Column(Float, default=0.0)
    nivel_riesgo = Column(String(10), index=True)
    factores_riesgo = Column(String(255))
    mensaje_analisis = Column(String(255))
    recomendacion_analisis = Column(String(255))
    analisis_timestamp = Column(DateTime)
    monto_dop_calculado = Column(DECIMAL(18, 2))
    
    card = relationship("Card", back_populates="transactions")
    
    __table_args__ = (
        UniqueConstraint('i_0011_stan', 'i_0041_card_acceptor_tid', name='uq_stan_tid'),
    )
# [file content end]
