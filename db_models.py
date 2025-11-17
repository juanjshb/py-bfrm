# [file name]: db_models.py
# [file content begin]
from sqlalchemy import (
    Column, String, Integer, BigInteger, DateTime, Float, Boolean, 
    ForeignKey, func, DECIMAL, UniqueConstraint
)
from sqlalchemy.orm import relationship
from database import Base
import datetime

class Currency(Base):
    """Tabla de códigos de moneda ISO 4217"""
    __tablename__ = 'ccurrencies'
    
    id = Column(Integer, primary_key=True)
    # Código numérico ISO 4217 (ej. 840 para USD)
    code_numeric = Column(String(3), unique=True, nullable=False, index=True)
    # Código alpha ISO 4217 (ej. "USD")
    code_alpha = Column(String(3), unique=True, nullable=False, index=True)
    name = Column(String(100))
    decimals = Column(Integer, default=2)

class Customer(Base):
    """Tabla de Clientes (ccustomers)"""
    __tablename__ = 'ccustomers'
    
    id = Column(Integer, primary_key=True)
    # Este es el 'cliente_id' que usaba el detector (ej. "CL-123456789")
    customer_ref_id = Column(String(50), unique=True, nullable=False, index=True)
    first_name = Column(String(100))
    last_name = Column(String(100))
    email = Column(String(150), unique=True)
    phone = Column(String(20))
    document_id = Column(String(50), unique=True) # Cédula/Pasaporte
    created_at = Column(DateTime, default=func.now())
    
    # Relaciones
    accounts = relationship("Account", back_populates="customer")

class Account(Base):
    """Tabla de Cuentas Bancarias (caccounts)"""
    __tablename__ = 'caccounts'
    
    id = Column(Integer, primary_key=True)
    account_number = Column(String(30), unique=True, nullable=False, index=True)
    account_type = Column(String(50)) # Ahorros, Corriente
    status = Column(String(20), default="active")
    balance = Column(DECIMAL(18, 2), default=0.00)
    currency_code = Column(String(3), nullable=False) # ej. "DOP"
    opened_at = Column(DateTime, default=func.now())
    
    # Llave foránea
    customer_id = Column(Integer, ForeignKey('ccustomers.id'), nullable=False)
    
    # Relaciones
    customer = relationship("Customer", back_populates="accounts")
    cards = relationship("Card", back_populates="account")

class Card(Base):
    """Tabla de Tarjetas (ccardx)"""
    __tablename__ = 'ccardx'
    
    id = Column(Integer, primary_key=True)
    # El PAN (Primary Account Number)
    pan = Column(String(20), unique=True, nullable=False, index=True)
    # Guardamos solo los últimos 4 para referencia rápida
    pan_last_4 = Column(String(4), nullable=False)
    # BIN (primeros 6-8 dígitos)
    pan_bin = Column(String(8), nullable=False, index=True)
    expiry_date = Column(String(4)) # MMYY
    card_type = Column(String(20)) # Crédito, Débito
    brand = Column(String(20)) # Visa, Mastercard
    status = Column(String(20), default="active")
    
    # Llave foránea
    account_id = Column(Integer, ForeignKey('caccounts.id'), nullable=False)
    
    # Relaciones
    account = relationship("Account", back_populates="cards")
    transactions = relationship("Transaction", back_populates="card")

class Transaction(Base):
    """Tabla de Transacciones (ctransactions) en formato ISO 8583"""
    __tablename__ = 'ctransactions'
    
    id = Column(Integer, primary_key=True)
    
    # Metadatos de la transacción
    tx_timestamp_utc = Column(DateTime, default=func.now(), index=True)
    
    # Llave foránea a la tarjeta
    card_id = Column(Integer, ForeignKey('ccardx.id'), nullable=False, index=True)
    
    # Campos ISO 8583 (usamos String para mantener el formato original)
    mti = Column(String(4), index=True)
    bitmap = Column(String(128))
    i_0002_pan = Column(String(20), index=True) # PAN (Primary Account Number)
    i_0003_processing_code = Column(String(6))
    i_0004_amount_transaction = Column(String(12)) # Ej: 000000015050
    i_0007_transmission_datetime = Column(String(10)) # MMDDhhmmss
    i_0011_stan = Column(String(6), index=True) # System Trace Audit Number
    i_0012_time_local = Column(String(6)) # hhmmss
    i_0013_date_local = Column(String(4)) # MMDD
    i_0022_pos_entry_mode = Column(String(3))
    i_0024_function_code_nii = Column(String(3))
    i_0025_pos_condition_code = Column(String(2))
    i_0032_acquiring_inst_id = Column(String(11))
    i_0035_track_2_data = Column(String(37))
    i_0041_card_acceptor_tid = Column(String(8)) # Terminal ID
    i_0042_card_acceptor_mid = Column(String(15)) # Merchant ID
    i_0043_card_acceptor_name_loc = Column(String(40))
    i_0049_currency_code_tx = Column(String(3)) # Ej: 840 (USD)
    i_0062_private_use_field = Column(String(255)) # Variable
    i_0128_mac = Column(String(64)) # Message Auth. Code
    
    # --- RESULTADOS DEL ANÁLISIS DE FRAUDE ---
    # Vinculamos el resultado del análisis directamente a la transacción
    
    es_fraude = Column(Boolean, default=False, index=True)
    probabilidad_fraude = Column(Float, default=0.0)
    nivel_riesgo = Column(String(10), index=True) # BAJO, MEDIO, ALTO
    factores_riesgo = Column(String(255)) # Lista como string: "MONTO_ELEVADO,HORARIO_NOCTURNO"
    mensaje_analisis = Column(String(255))
    recomendacion_analisis = Column(String(255))
    
    # Metadatos del análisis
    analisis_timestamp = Column(DateTime)
    monto_dop_calculado = Column(DECIMAL(18, 2))
    
    # Relaciones
    card = relationship("Card", back_populates="transactions")
    
    __table_args__ = (
        # Transacción única por terminal y STAN
        UniqueConstraint('i_0011_stan', 'i_0041_card_acceptor_tid', name='uq_stan_tid'),
    )
# [file content end]